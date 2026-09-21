"""Camera capture with a warning light: capture_photo() waits a few
seconds after being called, then turns the LED on and takes the photo -
so there's a clear gap between "capture was triggered" and "the light is
on and the camera is actually looking".

Assumes a Raspberry Pi Camera Module (via picamera2) and an LED wired to
LED_GPIO_PIN through a resistor. If you're using a USB webcam instead,
swap the picamera2 calls below for e.g. `cv2.VideoCapture`."""

import time
from pathlib import Path

from gpiozero import LED
from picamera2 import Picamera2

LED_GPIO_PIN = 17
WARNING_SECONDS = 3
CAPTURE_DIR = Path("/home/pi/R-pi-projekt/captures")

_led = LED(LED_GPIO_PIN)


def capture_photo() -> Path:
    """Waits WARNING_SECONDS, then turns the LED on, takes one photo, and
    turns the LED off again. Returns the saved file's path."""
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    time.sleep(WARNING_SECONDS)
    _led.on()
    try:
        camera = Picamera2()
        camera.start()
        time.sleep(0.5)  # let auto-exposure/focus settle
        path = CAPTURE_DIR / f"capture-{int(time.time())}.jpg"
        camera.capture_file(str(path))
        camera.stop()
        camera.close()
        return path
    finally:
        _led.off()
