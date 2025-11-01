# font_renderer.py
# Unified font rendering wrapper with proper ezFBfont integration
# Falls back gracefully to built-in 8x8 font if ezFBfont not available

_HAS_EZ = False
ezFBfont = None
try:
    # Prefer vendored path: lib/ezFBfont.py
    from ezFBfont import ezFBfont
    _HAS_EZ = True
except ImportError:
    try:
        # Fallback to fonts subdirectory if present
        from fonts.ezFBfont import ezFBfont
        _HAS_EZ = True
    except ImportError:
        ezFBfont = None
        _HAS_EZ = False

import framebuf
from fonts import get_font_module


class FontRenderer:
    """Render text using microPyEZfonts when available; fallback to built-in 8x8 font with software scaling.

    Usage:
      fr = FontRenderer(oled)
      fr.text("Hello", 0, 0, font="PTSans_08", scale=1)
      fr.text("Hello", 0, 0, font="8x13")  # Uses alias
    """
    
    def __init__(self, device):
        self.device = device
        self._ez_instances = {}  # Cache ezFBfont instances per font
        
    def _get_ez_instance(self, font_name):
        """Get or create an ezFBfont instance for the given font name."""
        if not _HAS_EZ or font_name is None:
            return None
            
        # Check cache
        if font_name in self._ez_instances:
            return self._ez_instances[font_name]
        
        # Try to load font module
        font_module = get_font_module(font_name)
        if font_module is None:
            return None
        
        # Create ezFBfont instance (using positional args for MicroPython compatibility)
        try:
            instance = ezFBfont(self.device, font_module, 1, 0)  # device, font, fg, bg
            self._ez_instances[font_name] = instance
            return instance
        except Exception:
            return None

    def text(self, text: str, x: int, y: int, font: str = "PTSans_08", scale: int = 1, color: int = 1):
        """Draw text at position (x, y).
        
        Args:
            text: Text string to render
            x, y: Position coordinates
            font: Font name or alias (default: "PTSans_08")
            scale: Scale factor (only used for fallback, ezFBfont uses font size)
            color: Foreground color (1 for on, 0 for off)
        """
        # Try ezFBfont first
        ez_instance = self._get_ez_instance(font)
        if ez_instance:
            try:
                # ezFBfont uses write() method, set colors using positional args for MicroPython compatibility
                ez_instance.set_default(color, 0)  # fg, bg as positional
                ez_instance.write(text, x, y)
                return
            except Exception:
                # Fall through to fallback
                pass
        
        # Fallback: software-scale default 8x8 font
        _text_scaled(self.device, text, x, y, scale, color)

    def text_block(self, lines, x: int, y: int, font: str = "PTSans_08", scale: int = 1, 
                   line_spacing: int = 2, align: str = "left", color: int = 1):
        """Draw multiple lines of text.
        
        Args:
            lines: List of text strings
            x, y: Starting position coordinates
            font: Font name or alias
            scale: Scale factor (only for fallback)
            line_spacing: Additional pixels between lines
            align: Text alignment ('left', 'center', 'right')
            color: Foreground color
        """
        # Try ezFBfont first
        ez_instance = self._get_ez_instance(font)
        if ez_instance:
            try:
                # Get font height for spacing
                font_module = get_font_module(font)
                if font_module:
                    font_height = font_module.height()
                    
                    # Calculate text width for alignment
                    max_width = 0
                    if align != "left":
                        for line in lines:
                            w, _ = ez_instance.size(line)
                            max_width = max(max_width, w)
                    
                    yy = y
                    for line in lines:
                        xx = x
                        if align == "center":
                            w, _ = ez_instance.size(line)
                            xx = x - (w // 2)
                        elif align == "right":
                            w, _ = ez_instance.size(line)
                            xx = x - w
                        
                        # Use positional args for MicroPython compatibility
                        ez_instance.set_default(color, 0)  # fg, bg
                        ez_instance.write(line, xx, yy)
                        yy += font_height + line_spacing
                    return
            except Exception:
                # Fall through to fallback
                pass
        
        # Fallback: software-scale default font
        yy = y
        for line in lines:
            xx = x
            if align != "left":
                w = 8 * len(line) * max(1, scale)
                if align == "center":
                    xx = x - w // 2
                elif align == "right":
                    xx = x - w
            _text_scaled(self.device, line, xx, yy, scale, color)
            yy += (8 * max(1, scale)) + line_spacing


def _text_scaled(oled, text, x, y, scale=1, color=1):
    """Fallback text rendering with software scaling."""
    if scale == 1:
        # SSD1306 text() method only takes 3 args: text, x, y (no color parameter)
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
                        oled.pixel(int(x + xx * scale + dx), int(y + yy * scale + dy), color)
