"""
Filename: main.py
Description: WS2812 / NeoPixel full strip test
- Solid RGB test
- Chase test
- Fast rainbow (≈ 9–10 seconds total)
"""

from time import sleep_ms
from led_strip import LedStrip

# ---------------- NeoPixel config ----------------
LED_PIN = 25
LED_COUNT = 111
LED_BRIGHTNESS = 80

# Timing
SOLID_HOLD_MS = 600
CHASE_DELAY_MS = 6

# Rainbow tuning (≈ 9 seconds total)
RAINBOW_FRAMES = 256
RAINBOW_FRAME_DELAY_MS = 35   # 256 * 35ms ≈ 8.9s


def wheel(pos: int) -> tuple:
    """
    Color wheel: pos in [0..255] -> (r,g,b)
    """
    pos = pos % 256
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)


def solid_test(leds: LedStrip):
    print("[TEST] Solid RGB + White")
    leds.fill(255, 0, 0, show=True)
    sleep_ms(SOLID_HOLD_MS)
    leds.fill(0, 255, 0, show=True)
    sleep_ms(SOLID_HOLD_MS)
    leds.fill(0, 0, 255, show=True)
    sleep_ms(SOLID_HOLD_MS)
    leds.fill(255, 255, 255, show=True)
    sleep_ms(SOLID_HOLD_MS)
    leds.clear(show=True)
    sleep_ms(300)


def chase_test(leds: LedStrip):
    print("[TEST] Chase (1 pixel)")
    leds.clear(show=True)
    for i in range(LED_COUNT):
        leds.clear(show=False)
        leds.set_pixel(i, 255, 255, 255, show=False)
        leds.show()
        sleep_ms(CHASE_DELAY_MS)
    leds.clear(show=True)
    sleep_ms(300)


def rainbow_fast(leds: LedStrip):
    print("[TEST] Fast rainbow (~9s)")
    for j in range(RAINBOW_FRAMES):
        for i in range(LED_COUNT):
            leds.set_pixel_rgb(
                i,
                wheel((i * 256 // LED_COUNT) + j),
                show=False
            )
        leds.show()
        sleep_ms(RAINBOW_FRAME_DELAY_MS)

    leds.clear(show=True)
    sleep_ms(300)


def main():
    leds = LedStrip(
        data_pin=LED_PIN,
        led_count=LED_COUNT,
        brightness=LED_BRIGHTNESS,
    )
    leds.clear(show=True)

    print("=== NEOPIXEL STRIP TEST (FAST RAINBOW) ===")
    print("GPIO:", LED_PIN, "| LEDs:", LED_COUNT, "| Brightness:", LED_BRIGHTNESS)

    while True:
        solid_test(leds)
        chase_test(leds)
        rainbow_fast(leds)


if __name__ == "__main__":
    main()

