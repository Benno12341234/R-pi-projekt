"""Fullscreen touchscreen UI for the Pi. Two hold-to-talk buttons:

- "Regel festlegen" - say what the AI is allowed to do (e.g. "Du darfst
  Dateien im Ordner Dokumente sichern"). Stored only after you confirm the
  transcript by tapping - a misheard word must not silently become a
  permission.
- "Befehl geben" - say what it should do right now. The AI checks the
  request against the stored rules and proposes exactly one action, or
  says the request isn't covered by any rule. Either way, nothing is
  queued as approved until you tap Confirm - never by voice, so background
  noise or a misheard word can't approve anything.

Runs continuously (see desktop/pi-ai-console.desktop), independent of
whether the USB-C link to a host is currently up. Confirming an action
here only marks it "approved" in the shared queue (pending_actions.py) -
__main__.py (which only runs while the USB-C link is up) is what actually
acts on it, once that part is built.
"""

import threading
import tkinter as tk

from model_router import ModelRouter, RateLimitExceeded

from . import pending_actions, policy
from .speech import PushToTalkRecorder, speak

NO_RULES_REPLY = "NICHT ERLAUBT: Es sind noch keine Regeln festgelegt."


def build_action_prompt() -> str:
    rules = policy.list_rules()
    if not rules:
        return (
            "The user has not set any rules yet for what you may do on "
            "their computer. Since nothing is explicitly allowed, do not "
            f"propose any action - respond with exactly '{NO_RULES_REPLY}' "
            "and nothing else."
        )
    rules_text = "\n".join(f"- {r}" for r in rules)
    return (
        "The user has set these rules for what you may do on their "
        f"computer:\n{rules_text}\n\n"
        "Turn the user's spoken command into a short, one-sentence "
        "description of exactly one concrete action to take on their "
        "computer - but only if it is clearly covered by the rules above. "
        "If the command is unclear, or is not covered by / conflicts with "
        "the rules, respond with exactly 'NICHT ERLAUBT: <kurzer Grund>' "
        "and nothing else. Reply in German."
    )


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.router = ModelRouter()
        self.recorder = PushToTalkRecorder()
        self._pending_kind = None   # "action" | "rule"
        self._pending_value = None  # PendingAction | rule text

        root.attributes("-fullscreen", True)
        root.configure(bg="black")

        self.status = tk.Label(root, text="Bereit", font=("DejaVu Sans", 26), fg="white", bg="black")
        self.status.pack(pady=15)

        self.transcript = tk.Label(root, text="", font=("DejaVu Sans", 18), fg="white", bg="black", wraplength=700)
        self.transcript.pack(pady=10)

        buttons = tk.Frame(root, bg="black")
        buttons.pack(pady=20)

        self.rule_button = tk.Button(
            buttons, text="Regel festlegen\n(gedrückt halten)", font=("DejaVu Sans", 18), bg="#7c3aed", fg="white",
        )
        self.rule_button.pack(side="left", padx=15, ipadx=15, ipady=15)
        self.rule_button.bind("<ButtonPress-1>", lambda e: self.on_talk_press("rule"))
        self.rule_button.bind("<ButtonRelease-1>", lambda e: self.on_talk_release("rule"))

        self.command_button = tk.Button(
            buttons, text="Befehl geben\n(gedrückt halten)", font=("DejaVu Sans", 18), bg="#2563eb", fg="white",
        )
        self.command_button.pack(side="left", padx=15, ipadx=15, ipady=15)
        self.command_button.bind("<ButtonPress-1>", lambda e: self.on_talk_press("action"))
        self.command_button.bind("<ButtonRelease-1>", lambda e: self.on_talk_release("action"))

        self.confirm_frame = tk.Frame(root, bg="black")
        self.proposal_label = tk.Label(
            self.confirm_frame, text="", font=("DejaVu Sans", 18), fg="yellow", bg="black", wraplength=700,
        )
        self.proposal_label.pack(pady=10)
        tk.Button(
            self.confirm_frame, text="Bestätigen", font=("DejaVu Sans", 20), bg="#16a34a", fg="white",
            command=self.on_confirm,
        ).pack(side="left", padx=20)
        tk.Button(
            self.confirm_frame, text="Ablehnen", font=("DejaVu Sans", 20), bg="#dc2626", fg="white",
            command=self.on_deny,
        ).pack(side="right", padx=20)

        self.rules_label = tk.Label(root, text="", font=("DejaVu Sans", 12), fg="#888888", bg="black", wraplength=700)
        self.rules_label.pack(pady=15, side="bottom")
        self._refresh_rules_label()

    def _refresh_rules_label(self):
        rules = policy.list_rules()
        text = "Aktuelle Regeln:\n" + "\n".join(f"- {r}" for r in rules) if rules else "Aktuelle Regeln: keine"
        self.rules_label.configure(text=text)

    def on_talk_press(self, kind: str):
        self.status.configure(text="Höre zu ...")
        self._active_kind = kind
        self.recorder.start()

    def on_talk_release(self, kind: str):
        self.status.configure(text="Verarbeite ...")
        threading.Thread(target=self._handle_recording, args=(kind,), daemon=True).start()

    def _handle_recording(self, kind: str):
        text = self.recorder.stop()
        self.transcript.configure(text=text or "(nichts verstanden)")
        if not text:
            self.status.configure(text="Bereit")
            return

        if kind == "rule":
            self._propose_rule(text)
        else:
            self._propose_action(text)

    def _propose_rule(self, text: str):
        self._pending_kind = "rule"
        self._pending_value = text
        self.proposal_label.configure(text=f"Neue Regel: {text}")
        self.status.configure(text="Regel bestätigen?")
        self.confirm_frame.pack(pady=15)
        speak(f"Neue Regel: {text}. Bestätigen oder ablehnen?")

    def _propose_action(self, text: str):
        try:
            result = self.router.route(text, system=build_action_prompt())
        except RateLimitExceeded:
            self.status.configure(text="Zu viele Anfragen - kurz warten")
            speak("Zu viele Anfragen, bitte kurz warten.")
            return
        except Exception:
            self.status.configure(text="Fehler bei der KI-Anfrage")
            speak("Da ist etwas schiefgelaufen.")
            return

        if result.text.strip().upper().startswith("NICHT ERLAUBT"):
            self.status.configure(text="Nicht erlaubt")
            self.transcript.configure(text=result.text)
            speak(result.text)
            return

        action = pending_actions.propose(result.text)
        self._pending_kind = "action"
        self._pending_value = action
        self.proposal_label.configure(text=result.text)
        self.status.configure(text="Bestätigung erforderlich")
        self.confirm_frame.pack(pady=15)
        speak(result.text + " Bestätigen oder ablehnen?")

    def on_confirm(self):
        if self._pending_kind == "rule":
            policy.add_rule(self._pending_value)
            self._refresh_rules_label()
            speak("Regel gespeichert.")
        elif self._pending_kind == "action":
            pending_actions.resolve(self._pending_value.id, approved=True)
            speak("Bestätigt.")
        self._reset()

    def on_deny(self):
        if self._pending_kind == "action":
            pending_actions.resolve(self._pending_value.id, approved=False)
        speak("Abgelehnt.")
        self._reset()

    def _reset(self):
        self._pending_kind = None
        self._pending_value = None
        self.confirm_frame.pack_forget()
        self.transcript.configure(text="")
        self.status.configure(text="Bereit")


def main() -> None:
    root = tk.Tk()
    root.title("Pi AI Console")
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
