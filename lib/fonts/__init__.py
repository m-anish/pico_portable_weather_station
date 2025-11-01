# fonts package: Font mapping and loader for ezFBfont integration
# Provides convenient font name mapping to actual font modules

# Try importing available fonts and cache module objects
# Using direct imports and caching the module objects
_FONT_MODULES = {}

def _import_font(module_name, font_key):
    """Helper to import a font module and cache it."""
    try:
        # Try using __import__ with positional args only (MicroPython compatible)
        parts = module_name.split('.')
        if len(parts) == 2:
            # Format: fonts.module_name
            mod = __import__(module_name)
            # Navigate to the actual submodule
            for part in parts[1:]:
                mod = getattr(mod, part)
            _FONT_MODULES[font_key] = mod
            return True
    except:
        pass
    return False

# Import all available fonts
_import_font('fonts.ezFBfont_micro_full_05', 'micro')
_import_font('fonts.ezFBfont_PTSans_06_latin_09', 'PTSans_06')
_import_font('fonts.ezFBfont_PTSans_08_latin_14', 'PTSans_08')
_import_font('fonts.ezFBfont_helvB12_latin_20', 'helvB12')
_import_font('fonts.ezFBfont_PTSans_20_latin_30', 'PTSans_20')
_import_font('fonts.ezFBfont_open_iconic_all_1x_0x0_0xFFF_08', 'icons')
_import_font('fonts.ezFBfont_amstrad_cpc_extended_latin_08', 'amstrad')


# Font name aliases for backward compatibility and convenience
_FONT_ALIASES = {
    '6x10': 'PTSans_06',      # Approximate match for small font
    '8x13': 'PTSans_08',      # Approximate match for medium font
    '12x24': 'helvB12',       # Approximate match for large font
    'micro': 'micro',         # Tiny font
    'small': 'PTSans_06',
    'medium': 'PTSans_08',
    'large': 'helvB12',
    'xlarge': 'PTSans_20',
    'symbols': 'icons',       # Icon/symbol font
    'icon': 'icons',
    'amstrad': 'amstrad',     # Extended character set font
}


def get_font_module(font_name):
    """Get the actual font module object by name or alias.
    
    Args:
        font_name: Font name or alias (e.g., 'PTSans_08', '8x13', 'medium')
        
    Returns:
        Font module object if found, None otherwise
    """
    # Resolve alias
    resolved_name = _FONT_ALIASES.get(font_name, font_name)
    
    # Return cached module if available
    if resolved_name in _FONT_MODULES:
        return _FONT_MODULES[resolved_name]
    
    return None


def get_available_fonts():
    """Return list of available font names."""
    return list(_FONT_MODULES.keys())


def get_font_aliases():
    """Return dict of font aliases."""
    return _FONT_ALIASES.copy()
