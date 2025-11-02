"""display_utils.py
Helpers for drawing text on SSD1306 OLED.

Provides two backends:
- FontRenderer (preferred): uses microPyEZfonts if present, else falls back.
- Software scaling fallback for built-in 8x8 font.
- ezFBmarquee integration for scrolling text.
"""

import framebuf
from font_renderer import FontRenderer

# Try to import ezFBmarquee
_HAS_MARQUEE = False
ezFBmarquee = None
try:
    from ezFBmarquee import ezFBmarquee
    _HAS_MARQUEE = True
except ImportError:
    try:
        from fonts.ezFBmarquee import ezFBmarquee
        _HAS_MARQUEE = True
    except ImportError:
        ezFBmarquee = None
        _HAS_MARQUEE = False

from fonts import get_font_module


def text_scaled(oled, text, x, y, scale=1):
    """Draw text at (x, y) scaled by integer 'scale' onto the provided oled.

    Falls back to oled.text for scale == 1 to save work.
    Note: Prefer using draw_text() with FontRenderer for better font support.
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
    Note: Prefer using draw_block() with FontRenderer for better font support.
    """
    oled.fill(0)
    y = 0
    for i, l in enumerate(lines):
        s = scales[i] if i < len(scales) else 1
        text_scaled(oled, l, 0, int(y), s)
        y += 9 * s + 2
    oled.show()


# -------- FontRenderer-backed helpers --------
def draw_text(oled, text, x, y, font="PTSans_08", scale=1, align="left", color=1):
    """Draw text using FontRenderer with ezFBfont support.
    
    Args:
        oled: SSD1306 display object
        text: Text string to render
        x, y: Position coordinates
        font: Font name or alias (e.g., "PTSans_08", "8x13", "medium")
        scale: Scale factor (only used for fallback)
        align: Horizontal alignment ('left', 'center', 'right')
        color: Foreground color (1 for on, 0 for off)
    """
    fr = FontRenderer(oled)
    
    # Adjust x position for alignment if not left
    if align != "left":
        # For proper alignment, we need to measure text width
        # Simple approximation for non-ezFBfont case
        if align == "center":
            # Approximate width (will be corrected by FontRenderer if using ezFBfont)
            w = len(text) * 8 * max(1, scale)
            x = x - w // 2
        elif align == "right":
            w = len(text) * 8 * max(1, scale)
            x = x - w
    
    fr.text(text, x, y, font=font, scale=scale, color=color)


def draw_block(oled, lines, x, y, font="PTSans_08", scale=1, line_spacing=2, align="left", color=1):
    """Draw multiple lines of text using FontRenderer.
    
    Args:
        oled: SSD1306 display object
        lines: List of text strings
        x, y: Starting position coordinates
        font: Font name or alias
        scale: Scale factor (only used for fallback)
        line_spacing: Additional pixels between lines
        align: Text alignment ('left', 'center', 'right')
        color: Foreground color
    """
    fr = FontRenderer(oled)
    fr.text_block(lines, x, y, font=font, scale=scale, line_spacing=line_spacing, align=align, color=color)


# -------- Marquee utilities --------
class Marquee:
    """Horizontal text marquee with ezFBmarquee integration.
    
    Falls back to basic software scrolling if ezFBmarquee not available.
    
    Usage:
      mq = Marquee(oled, x, y, width, font="PTSans_08")
      mq.start("Long text...")
      ... in loop: mq.step(); oled.show()
    """

    def __init__(self, device, x, y, width, font="PTSans_08", speed_px=1, mode='marquee'):
        self.device = device
        self.x = x
        self.y = y
        self.width = width
        self.font_name = font
        self.speed_px = max(1, int(speed_px))
        self.mode = mode
        self._offset = 0
        self._text = ""
        self._ez_marquee = None
        
        # Try to use ezFBmarquee if available
        if _HAS_MARQUEE:
            font_module = get_font_module(font)
            if font_module:
                try:
                    # Use positional args for MicroPython compatibility: display, font, x, y, width, mode
                    self._ez_marquee = ezFBmarquee(device, font_module, x, y, width, mode)
                    self._fr = None  # Not needed if using ezFBmarquee
                    return
                except Exception:
                    # Fall through to software fallback
                    pass
        
        # Software fallback
        self._fr = FontRenderer(device)

    def start(self, text: str):
        """Start the marquee with the given text."""
        self._text = text or ""
        self._offset = 0
        
        if self._ez_marquee:
            try:
                # Use positional args: string, mode (MicroPython compatibility)
                self._ez_marquee.start(text, self.mode)
                return
            except Exception:
                # Fall through to software fallback
                pass

    def step(self):
        """Advance the marquee one step. Returns True if rollover occurred."""
        if self._ez_marquee:
            try:
                return self._ez_marquee.step(self.speed_px)
            except Exception:
                # Fall through to software fallback
                pass
        
        # Software fallback
        if not self._text:
            return False
        
        # Clear the marquee area (approximate height)
        font_module = get_font_module(self.font_name)
        if font_module:
            h = font_module.height()
        else:
            h = 10  # Default fallback height
        # Use faster fill_rect instead of per-pixel loops
        try:
            self.device.fill_rect(self.x, self.y, self.width, h, 0)
        except Exception:
            # Fallback if device lacks fill_rect
            for yy in range(h):
                for xx in range(self.width):
                    self.device.pixel(self.x + xx, self.y + yy, 0)
        
        # Draw text starting at -offset (for left-to-right scrolling)
        # Text scrolls from right to left, so start_x decreases as offset increases
        start_x = self.x - self._offset
        self._fr.text(self._text, start_x, self.y, font=self.font_name, scale=1)
        
        # Calculate text width - try to get accurate width from FontRenderer
        text_w = 0
        font_module = get_font_module(self.font_name)
        if font_module and hasattr(self._fr, '_get_ez_instance'):
            ez_inst = self._fr._get_ez_instance(self.font_name)
            if ez_inst:
                try:
                    text_w, _ = ez_inst.size(self._text)
                except Exception:
                    pass
        
        # Fallback: estimate width based on font
        if text_w == 0:
            if font_module:
                avg_width = (font_module.max_width()
                             if hasattr(font_module, 'max_width') else 16)
                text_w = len(self._text) * avg_width
            else:
                text_w = len(self._text) * 16  # Larger default for bigger fonts
        
        # Advance offset for scrolling (text scrolls right to left)
        self._offset += self.speed_px
        # When text has scrolled completely past left edge, cycle to next
        # Add some padding (width of screen) before repeating
        if self._offset >= text_w + self.width + 20:
            self._offset = 0
            return True
        return False
    
    def stop(self):
        """Stop the marquee."""
        if self._ez_marquee:
            try:
                self._ez_marquee.stop()
                return
            except Exception:
                pass
        
        # Software fallback: clear area
        font_module = get_font_module(self.font_name)
        h = font_module.height() if font_module else 10
        try:
            self.device.fill_rect(self.x, self.y, self.width, h, 0)
        except Exception:
            for yy in range(h):
                for xx in range(self.width):
                    self.device.pixel(self.x + xx, self.y + yy, 0)
        self._text = ""
        self._offset = 0
    
    def active(self):
        """Return True if marquee is active."""
        if self._ez_marquee:
            try:
                return self._ez_marquee.active()
            except Exception:
                pass
        return bool(self._text)
