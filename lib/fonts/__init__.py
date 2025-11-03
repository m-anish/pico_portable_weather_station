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

# Import only essential fonts (memory optimization - Phase 2)
# Removed: micro, PTSans_06, PTSans_08, icons (saves ~20-30KB RAM)
_import_font('fonts.ezFBfont_amstrad_cpc_extended_latin_08', 'amstrad')
_import_font('fonts.ezFBfont_helvB12_latin_20', 'helvB12')
_import_font('fonts.ezFBfont_PTSans_20_latin_30', 'PTSans_20')


# Font name aliases for backward compatibility and convenience
# Aliases now map to the 3 available fonts
_FONT_ALIASES = {
    '6x10': 'amstrad',        # Small font -> amstrad
    '8x13': 'amstrad',        # Medium font -> amstrad
    '12x24': 'helvB12',       # Large font -> helvB12
    'small': 'amstrad',       # Small -> amstrad
    'medium': 'helvB12',      # Medium -> helvB12
    'large': 'helvB12',       # Large -> helvB12
    'xlarge': 'PTSans_20',    # Extra large -> PTSans_20
    'amstrad': 'amstrad',     # Direct mapping
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
