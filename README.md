# R-Pi-Projekt

Raspberry Pi Projekt.

## AI Model Routing

`model_router/` routes a prompt to the cheapest model tier that can plausibly
handle it (`simple` / `standard` / `complex`, picked by a lightweight
heuristic in `complexity.py`), and falls back to the next configured
provider if one fails or has no API key set.

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # and/or
export OPENAI_API_KEY=...
python examples/model_routing_demo.py
```

```python
from model_router import ModelRouter

router = ModelRouter()
result = router.route("Explain what a Kalman filter does.")
print(result.provider, result.model, result.tier)
print(result.text)
```

Which models back each tier is defined in `model_router/config.py`
(`DEFAULT_TIERS`) - update it when a provider ships a new model.

### Cost guard

`ModelRouter` refuses to make more than `MODEL_ROUTER_RATE_LIMIT_MAX_REQUESTS`
API calls per `MODEL_ROUTER_RATE_LIMIT_WINDOW_SECONDS` (default: 60 per hour)
and raises `RateLimitExceeded` instead. This caps what a stuck loop, or a
crash-restart on the Pi, can cost you - even before the provider is asked.
Tune it via those two env vars, or pass `max_requests=`/`window_seconds=`
to `ModelRouter()` directly.

### Running as a systemd service (autostart on the Pi)

```bash
cp .env.example .env        # then fill in your API key(s)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

sudo cp systemd/model-router.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now model-router.service

# check it's running / see logs
systemctl status model-router.service
journalctl -u model-router.service -f
```

`systemd/model-router.service` assumes user `pi` and the project checked
out at `/home/pi/R-pi-projekt` - adjust `User=`, `WorkingDirectory=`, and
`ExecStart=` if yours differs. It restarts the service on crash
(`Restart=on-failure`), but gives up after 5 restarts within 10 minutes
(`StartLimitBurst`/`StartLimitIntervalSec`) so a broken deploy can't turn
into an endless, paid, restart loop. `ExecStart` currently points at the
demo script - swap it for your real entrypoint once you have one.

## USB-C Device Agent

The idea: plug the Pi into one of your own computers via USB-C. On the
Pi's touchscreen you say, out loud, what the AI is allowed to do (rules)
and separately what it should do right now (commands); it proposes one
concrete action and it only happens once you tap Confirm on the same
screen. This is for your own computers only - not for plugging into
devices you don't own or control.

Two safeguards apply to every proposal:
- Transcribed speech is shown on screen and must be **confirmed by tap**,
  never by voice.
- **Read-only requests are always allowed** (looking something up,
  listing files, checking status). **Anything that changes something
  needs a stored rule that covers it** - with no matching rule, the AI
  refuses instead of guessing (deny-by-default for changes, not for
  reads).

**Still open / not implemented yet:** actually reaching over the USB-C
link and changing something on the connected host. Everything up to and
including "confirmed on the touchscreen, queued as approved" works;
`device_agent/__main__.py` currently only logs what it *would* run.

### Hardware

- **Display:** a touchscreen, so commands and confirmation happen on the
  Pi itself. The official Raspberry Pi Touch Display (DSI, no separate
  power/HDMI cable needed) is the easiest match; any HDMI touchscreen
  works too.
- **Audio:** a USB microphone and a speaker (USB, or the Pi's 3.5mm jack /
  HDMI audio). USB mics avoid the ALSA config hassle that I2S mic HATs
  need.
- **Camera:** a Raspberry Pi Camera Module (CSI, via `picamera2`) + an LED
  on GPIO 17 (through a resistor) as the warning light. Have a USB webcam
  instead? Swap the capture code in `device_agent/camera.py`.
- A Pi model with a USB-C/OTG-capable data port for the host link: Pi
  Zero 2 W, Pi 4, or Pi 5.

### Setup

```bash
sudo apt install python3-tk espeak-ng portaudio19-dev python3-picamera2 python3-gpiozero
.venv/bin/pip install -r requirements.txt

# Vosk speech-to-text model (German example - pick your language):
# https://alphacephei.com/vosk/models
wget https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip
unzip vosk-model-small-de-0.15.zip -d /home/pi/

# USB-C gadget link to the host computer
sudo ./scripts/setup-usb-gadget.sh
sudo cp udev/99-usb-gadget-link.rules /etc/udev/rules.d/
sudo udevadm control --reload
sudo cp systemd/device-agent.service /etc/systemd/system/
sudo systemctl daemon-reload

# Touchscreen UI, always running (independent of the USB-C link)
mkdir -p ~/.config/autostart
cp desktop/pi-ai-console.desktop ~/.config/autostart/
```

Reboot. The touchscreen UI starts automatically on the desktop, with
three buttons:

- **"Regel festlegen"** (hold-to-talk) - say what the AI may do, e.g.
  "Du darfst Dateien im Ordner Dokumente sichern". Shown on screen; saved
  only if you tap Confirm.
- **"Foto aufnehmen"** (tap once) - waits 3 seconds, then the warning LED
  and the camera turn on and it takes one photo. Shown as a preview on
  screen; it's attached to the next command only, then discarded.
- **"Befehl geben"** (hold-to-talk) - say what it should do now, with the
  just-taken photo attached if there is one (e.g. "Was siehst du auf dem
  Bild?" or "Sichere den Ordner, den du auf dem Foto siehst"). A
  read-only request ("zeig mir ...", "was ist das ...") is always
  proposed; a request that changes something (e.g. "Sichere meine
  Dokumente") only gets proposed if a stored rule covers it, otherwise
  the AI says so instead of guessing. Either way: tap Confirm/Deny, never
  spoken.

### What's built

- **`scripts/setup-usb-gadget.sh`** + **`udev/99-usb-gadget-link.rules`** -
  turn the USB-C port into a USB gadget (Ethernet-over-USB) and start
  `device-agent.service` only while that link to a host is actually up.
- **`device_agent/speech.py`** - push-to-talk recording + offline Vosk
  speech-to-text, and espeak-ng for spoken replies. Fully local, no cost,
  no internet needed for either.
- **`device_agent/camera.py`** - waits, turns the warning LED on, and
  takes one photo. `model_router` sends it to the AI as an image (Claude
  and the configured GPT models both support vision), alongside the
  spoken command.
- **`device_agent/policy.py`** - the rules, as plain text, set via the
  "Regel festlegen" button. Handed to the AI as context before it
  proposes any action.
- **`device_agent/display_ui.py`** - the touchscreen app: the three
  buttons above, transcript, photo preview, the current rule list, and
  Confirm/Deny. Runs continuously via `desktop/pi-ai-console.desktop`.
- **`device_agent/pending_actions.py`** - the approval queue shared
  between the touchscreen and `device-agent.service`
  (propose -> pending -> approved/denied -> executed). `cli_approve.py`
  is a secondary, SSH-based way to approve/deny for when the screen isn't
  handy.
- **`device_agent/__main__.py`** - picks up approved actions while the
  USB-C link is up and logs what it would do - the actual host-side
  execution is the one piece still to design and build.
