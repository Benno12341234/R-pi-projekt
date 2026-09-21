"""Camera capture with two lights: capture_photo() waits a few seconds
after being called, then turns both on and takes the photo - so there's
a clear gap between "capture was triggered" and "the lights are on and
the camera is actually looking".

- WARNING_LED_GPIO_PIN - signals that a capture is happening (the same
  small warning LED as before).
- READING_LIGHT_GPIO_PIN - a brighter light that illuminates the subject,
  so the camera (and the AI reading the photo) can still make things out
  in a dark room. Always turned on during capture - it's the room being
  dark that makes it necessary, not something worth detecting up front.

Assumes a Raspberry Pi Camera Module (via picamera2) and two LEDs wired
through resistors. If you're using a USB webcam instead, swap the
picamera2 calls below for e.g. `cv2.VideoCapture`."""

import time
from pathlib import Path

from gpiozero import LED
from picamera2 import Picamera2

WARNING_LED_GPIO_PIN = 17
READING_LIGHT_GPIO_PIN = 27
WARNING_SECONDS = 3
CAPTURE_DIR = Path("/home/pi/R-pi-projekt/captures")

_warning_led = LED(WARNING_LED_GPIO_PIN)
_reading_light = LED(READING_LIGHT_GPIO_PIN)


def capture_photo() -> Path:
    """Waits WARNING_SECONDS, then turns both lights on, takes one photo,
    and turns them off again. Returns the saved file's path."""
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    time.sleep(WARNING_SECONDS)
    _warning_led.on()
    _reading_light.on()
    try:
        camera = Picamera2()
        camera.start()
        time.sleep(0.5)  # let auto-exposure/focus settle under the new light
        path = CAPTURE_DIR / f"capture-{int(time.time())}.jpg"
        camera.capture_file(str(path))
        camera.stop()
        camera.close()
        return path
    finally:
        _warning_led.off()
        _reading_light.off()
