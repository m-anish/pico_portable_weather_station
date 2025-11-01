# display_utils.py
# Helpers for drawing scaled text on SSD1306 OLED using MicroPython framebuf

import framebuf


def text_scaled(oled, text, x, y, scale=1):
    """Draw text at (x, y) scaled by integer 'scale' onto the provided oled.

    Falls back to oled.text for scale == 1 to save work.
    """
    if scale == 1:
        oled.text(text, x, y)
        return
    w = len(text) * 8
    h = 8
    buf = bytearray(w * h // 8)
    fb = framebuf.FrameBuffer(buf, w, h, framebuf.MONO_HLSB)
    fb.fill(0)
    fb.text(text, 0, 0, 1)
    for yy in range(h):
        for xx in range(w):
            if fb.pixel(xx, yy):
                for dy in range(int(scale)):
                    for dx in range(int(scale)):
                        oled.pixel(int(x + xx * scale + dx), int(y + yy * scale + dy), 1)


def show_big(oled, lines, scales):
    """Clear the display and render a list of lines with corresponding scales.

    - lines: list[str]
    - scales: list[int|float] matching or shorter than lines; defaults to 1 when missing
    """
    oled.fill(0)
    y = 0
    for i, l in enumerate(lines):
        s = scales[i] if i < len(scales) else 1
        text_scaled(oled, l, 0, int(y), s)
        y += 9 * s + 2
    oled.show()
