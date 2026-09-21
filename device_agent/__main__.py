"""Runs only while the Pi's USB-C gadget link (usb0) is up - started and
stopped by udev, see udev/99-usb-gadget-link.rules.

Placeholder: this does NOT change anything on the connected computer yet.
Still open before it safely can:
  - which actions the AI may propose (fixed scripts vs. free-form)
  - who has to approve a proposed action before it runs (see cli_approve.py
    for today's default: you, on the Pi, over SSH)
"""

import logging
import signal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("device-agent")


def main() -> None:
    log.info("USB-C link up - device agent started (no actions wired up yet)")
    signal.sigwait([signal.SIGTERM, signal.SIGINT])
    log.info("device agent stopping")


if __name__ == "__main__":
    main()
