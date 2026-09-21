"""Runs only while the Pi's USB-C gadget link (usb0) is up - started and
stopped by udev, see udev/99-usb-gadget-link.rules.

Watches the approval queue (pending_actions.py) for actions confirmed on
the touchscreen (display_ui.py) and picks them up. Still a placeholder for
the last step: it only logs what it *would* run - actually reaching over
the USB-C link and changing something on the host computer isn't
implemented yet.
"""

import logging
import signal
import time

from . import pending_actions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("device-agent")

_stop = False


def _request_stop(*_args):
    global _stop
    _stop = True


def main() -> None:
    signal.signal(signal.SIGTERM, _request_stop)
    signal.signal(signal.SIGINT, _request_stop)
    log.info("USB-C link up - watching for approved actions")

    while not _stop:
        for action in pending_actions.list_approved():
            log.info("would execute (id=%s): %s - not implemented yet", action.id, action.description)
            pending_actions.mark_executed(action.id)
        time.sleep(2)

    log.info("device agent stopping")


if __name__ == "__main__":
    main()
