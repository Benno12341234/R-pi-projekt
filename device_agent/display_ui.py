"""Fullscreen touchscreen UI for the Pi. Hold the button to give a spoken
command, review what the AI proposes, and explicitly tap Confirm or Deny
before anything is queued as approved. Confirmation is touch-only, never by
voice - a TV in the background or a misheard word must not be able to
approve anything.

Runs continuously (see desktop/pi-ai-console.desktop), independent of
whether the USB-C link to a host is currently up. Approving an action here
only marks it "approved" in the shared queue (pending_actions.py) -
__main__.py (which only runs while the USB-C link is up) is what actually
acts on it, once that part is built.
"""

import threading
import tkinter as tk

from model_router import ModelRouter, RateLimitExceeded

from . import pending_actions
from .speech import PushToTalkRecorder, speak

ACTION_SYSTEM_PROMPT = (
    "You turn a spoken command into a short, one-sentence description of "
    "exactly one concrete action to take on the user's computer. Do not "
    "execute anything yourself - only describe the action. If the command "
    "is unclear or does not map to a single concrete action, say that "
    "instead of guessing. Reply in German."
)


class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.router = ModelRouter()
        self.recorder = PushToTalkRecorder()
        self._pending_action = None

        root.attributes("-fullscreen", True)
        root.configure(bg="black")

        self.status = tk.Label(root, text="Bereit", font=("DejaVu Sans", 28), fg="white", bg="black")
        self.status.pack(pady=20)

        self.transcript = tk.Label(root, text="", font=("DejaVu Sans", 20), fg="white", bg="black", wraplength=700)
        self.transcript.pack(pady=10)

        self.talk_button = tk.Button(
            root, text="Gedrückt halten zum Sprechen", font=("DejaVu Sans", 24), bg="#2563eb", fg="white",
        )
        self.talk_button.pack(pady=30, ipadx=20, ipady=20)
        self.talk_button.bind("<ButtonPress-1>", self.on_talk_press)
        self.talk_button.bind("<ButtonRelease-1>", self.on_talk_release)

        self.confirm_frame = tk.Frame(root, bg="black")
        self.proposal_label = tk.Label(
            self.confirm_frame, text="", font=("DejaVu Sans", 20), fg="yellow", bg="black", wraplength=700,
        )
        self.proposal_label.pack(pady=10)
        tk.Button(
            self.confirm_frame, text="Bestätigen", font=("DejaVu Sans", 22), bg="#16a34a", fg="white",
            command=self.on_confirm,
        ).pack(side="left", padx=20)
        tk.Button(
            self.confirm_frame, text="Ablehnen", font=("DejaVu Sans", 22), bg="#dc2626", fg="white",
            command=self.on_deny,
        ).pack(side="right", padx=20)

    def on_talk_press(self, _event):
        self.status.configure(text="Höre zu ...")
        self.recorder.start()

    def on_talk_release(self, _event):
        self.status.configure(text="Verarbeite ...")
        threading.Thread(target=self._handle_command, daemon=True).start()

    def _handle_command(self):
        text = self.recorder.stop()
        self.transcript.configure(text=text or "(nichts verstanden)")
        if not text:
            self.status.configure(text="Bereit")
            return

        try:
            result = self.router.route(text, system=ACTION_SYSTEM_PROMPT)
        except RateLimitExceeded:
            self.status.configure(text="Zu viele Anfragen - kurz warten")
            speak("Zu viele Anfragen, bitte kurz warten.")
            return
        except Exception:
            self.status.configure(text="Fehler bei der KI-Anfrage")
            speak("Da ist etwas schiefgelaufen.")
            return

        self._pending_action = pending_actions.propose(result.text)
        self.proposal_label.configure(text=result.text)
        self.status.configure(text="Bestätigung erforderlich")
        self.confirm_frame.pack(pady=20)
        speak(result.text + " Bestätigen oder ablehnen?")

    def on_confirm(self):
        if self._pending_action:
            pending_actions.resolve(self._pending_action.id, approved=True)
            speak("Bestätigt.")
        self._reset()

    def on_deny(self):
        if self._pending_action:
            pending_actions.resolve(self._pending_action.id, approved=False)
            speak("Abgelehnt.")
        self._reset()

    def _reset(self):
        self._pending_action = None
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
