import ctypes
import time
import sys
import os
import json
import threading
import webbrowser
import platform
import random
import struct
from http.server import HTTPServer, BaseHTTPRequestHandler

# Detect OS
IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

# Configuration and State
CONFIG_FILE = "config.json"
state = {
    "running": False,
    "key_code_str": "Space",    # Standard JS KeyboardEvent.code
    "keycode": 49,             # Resolved OS-specific virtual code
    "key_name": "Space",
    "interval_ms": 1000,
    "count": 0,
    "macro_enabled": False,
    "macro_interval_s": 60.0,
    "macro_actions": [
        {"type": "right", "duration_s": 3.0},
        {"type": "left", "duration_s": 3.0}
    ],
    "humanizer_enabled": True,  # Anti-Detection (Humanizer) Mode
    "macos_accessible": True,   # macOS Accessibility privilege status
    
    # Pixel Trigger Macro State
    "pixel_macro_enabled": False,
    "pixel_x": 100,
    "pixel_y": 100,
    "pixel_color": "#FFCC00",
    "pixel_match_type": "equal", # "equal" or "not_equal"
    "pixel_action_code_str": "Space",
    "pixel_action_keycode": 49,
    "pixel_action_name": "Space",
    "pixel_cooldown_s": 1.5,
    
    # Move & Jump Macro State
    "jump_macro_enabled": False,
    "jump_x": 100,
    "jump_y": 100,
    "jump_cooldown_s": 20.0,
    "mouse_macro_enabled": False,
    "mouse_interval_min": 3,
    "mouse_x1": 100, "mouse_y1": 200,
    "mouse_x2": 300, "mouse_y2": 400,
    "jump_action_code_str": "KeyC",
    "jump_action_keycode": 8 if IS_MAC else 0x43,
    "jump_action_name": "C",
    "minimap_offset_x": 0,
    "minimap_offset_y": 0,
    
    # Scheduled Key Macros (list of {id, enabled, interval_s, key_code_str, keycode, key_name, press_count})
    "scheduled_macros": []
}
state_lock = threading.Lock()
sleep_event = threading.Event()

# Tracks last trigger time for each scheduled macro (keyed by macro id, outside state for performance)
_sched_last_triggers = {}

# macOS Virtual Keycode Mapping (standard key code to CGKeyCode)
MAC_KEY_CODES = {
    # Alphabet
    "KeyA": 0, "KeyS": 1, "KeyD": 2, "KeyF": 3, "KeyH": 4, "KeyG": 5, "KeyZ": 6, "KeyX": 7,
    "KeyC": 8, "KeyV": 9, "KeyB": 11, "KeyQ": 12, "KeyW": 13, "KeyE": 14, "KeyR": 15,
    "KeyY": 16, "KeyT": 17, "KeyO": 31, "KeyU": 32, "KeyI": 34, "KeyP": 35, "KeyL": 37,
    "KeyJ": 38, "KeyK": 40, "KeyN": 45, "KeyM": 46,
    # Numbers
    "Digit1": 18, "Digit2": 19, "Digit3": 20, "Digit4": 21, "Digit5": 23, "Digit6": 22,
    "Digit7": 26, "Digit8": 28, "Digit9": 25, "Digit0": 29,
    # Specials
    "Space": 49, "Enter": 36, "NumpadEnter": 76, "Tab": 48, "Escape": 53,
    "Backspace": 51, "Delete": 117,
    "ArrowLeft": 123, "ArrowRight": 124, "ArrowDown": 125, "ArrowUp": 126,
    # Functions
    "F1": 122, "F2": 120, "F3": 99, "F4": 118, "F5": 96, "F6": 97, "F7": 98,
    "F8": 100, "F9": 101, "F10": 109, "F11": 103, "F12": 111,
    # Symbols
    "Minus": 27, "Equal": 24, "BracketLeft": 33, "BracketRight": 30,
    "Semicolon": 41, "Quote": 39, "Backslash": 42, "Comma": 43, "Period": 47,
    "Slash": 44, "Backquote": 50
}

# Windows Virtual-Key (VK) Code Mapping (standard key code to VK Code)
WIN_KEY_CODES = {
    # Alphabet
    "KeyA": 0x41, "KeyS": 0x53, "KeyD": 0x44, "KeyF": 0x46, "KeyH": 0x48, "KeyG": 0x47, "KeyZ": 0x5A, "KeyX": 0x58,
    "KeyC": 0x43, "KeyV": 0x56, "KeyB": 0x42, "KeyQ": 0x51, "KeyW": 0x57, "KeyE": 0x45, "KeyR": 0x52,
    "KeyY": 0x59, "KeyT": 0x54, "KeyO": 0x4F, "KeyU": 0x55, "KeyI": 0x49, "KeyP": 0x50, "KeyL": 0x4C,
    "KeyJ": 0x4A, "KeyK": 0x4B, "KeyN": 0x4E, "KeyM": 0x4D,
    # Numbers
    "Digit1": 0x31, "Digit2": 0x32, "Digit3": 0x33, "Digit4": 0x34, "Digit5": 0x35, "Digit6": 0x36,
    "Digit7": 0x37, "Digit8": 0x38, "Digit9": 0x39, "Digit0": 0x30,
    # Specials
    "Space": 0x20, "Enter": 0x0D, "Tab": 0x09, "Escape": 0x1B,
    "Backspace": 0x08, "Delete": 0x2E,
    "ArrowLeft": 0x25, "ArrowUp": 0x26, "ArrowRight": 0x27, "ArrowDown": 0x28,
    # Functions
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F5": 0x74, "F6": 0x75, "F7": 0x76,
    "F8": 0x77, "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    # Symbols
    "Minus": 0xBD, "Equal": 0xBB, "BracketLeft": 0xDB, "BracketRight": 0xDD,
    "Semicolon": 0xBA, "Quote": 0xDE, "Backslash": 0xDC, "Comma": 0xBC, "Period": 0xBE,
    "Slash": 0xBF, "Backquote": 0xC0
}

# Structs for macOS CoreGraphics coordinate mapping
class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]
class CGSize(ctypes.Structure):
    _fields_ = [("width", ctypes.c_double), ("height", ctypes.c_double)]
class CGRect(ctypes.Structure):
    _fields_ = [("origin", CGPoint), ("size", CGSize)]

def resolve_keycode(key_code_str):
    """Maps the standardized JavaScript key code to the local OS virtual keycode"""
    if IS_MAC:
        return MAC_KEY_CODES.get(key_code_str, 49)  # Fallback to Mac Space
    elif IS_WINDOWS:
        return WIN_KEY_CODES.get(key_code_str, 0x20)  # Fallback to Windows Space (0x20)
    return 0

def check_accessibility_privilege():
    """Checks programmatically if the current process is trusted for macOS accessibility"""
    if IS_MAC:
        try:
            ax = ctypes.CDLL("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
            return bool(ax.AXIsProcessTrusted())
        except Exception:
            return False
    return True


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# Try loading macOS CoreGraphics APIs
cg_loaded = False
if IS_MAC:
    try:
        cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        
        cg.CGEventCreate.restype = ctypes.c_void_p
        cg.CGEventCreate.argtypes = [ctypes.c_void_p]
        cg.CGEventGetLocation.restype = CGPoint
        cg.CGEventGetLocation.argtypes = [ctypes.c_void_p]
        
        cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
        cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_ushort, ctypes.c_bool]
        
        cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p
        cg.CGEventCreateMouseEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint32, CGPoint, ctypes.c_uint32]
        
        cg.CGEventPost.restype = None
        cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        cf.CFRelease.restype = None
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        
        # Display/Pixel reading APIs
        cg.CGDisplayCreateImageForRect.restype = ctypes.c_void_p
        cg.CGDisplayCreateImageForRect.argtypes = [ctypes.c_uint32, CGRect]
        cg.CGMainDisplayID.restype = ctypes.c_uint32
        cg.CGImageGetDataProvider.restype = ctypes.c_void_p
        cg.CGImageGetDataProvider.argtypes = [ctypes.c_void_p]
        cg.CGDataProviderCopyData.restype = ctypes.c_void_p
        cg.CGDataProviderCopyData.argtypes = [ctypes.c_void_p]
        cf.CFDataGetBytePtr.restype = ctypes.c_void_p
        cf.CFDataGetBytePtr.argtypes = [ctypes.c_void_p]
        cg.CGImageGetBytesPerRow.restype = ctypes.c_size_t
        cg.CGImageGetBytesPerRow.argtypes = [ctypes.c_void_p]
        cg.CGDisplayPixelsWide.restype = ctypes.c_size_t
        cg.CGDisplayPixelsWide.argtypes = [ctypes.c_uint32]
        cg.CGDisplayBounds.restype = CGRect
        cg.CGDisplayBounds.argtypes = [ctypes.c_uint32]
        
        # Warp Mouse API
        cg.CGWarpMouseCursorPosition.restype = None
        cg.CGWarpMouseCursorPosition.argtypes = [CGPoint]
        
        cg_loaded = True
    except Exception as e:
        print(f"Warning: Could not load macOS CoreGraphics APIs ({e}).")

# Setup Windows SendInput structures and functions
user32 = None
if IS_WINDOWS:
    try:
        user32 = ctypes.windll.user32
        
        # Windows Ctypes Structures
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_void_p)
            ]
            
        class MOUSEINPUT(ctypes.Structure):
            _fields_ = [
                ("dx", ctypes.c_long),
                ("dy", ctypes.c_long),
                ("mouseData", ctypes.c_ulong),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", ctypes.c_void_p)
            ]
            
        class HARDWAREINPUT(ctypes.Structure):
            _fields_ = [
                ("uMsg", ctypes.c_ulong),
                ("wParamL", ctypes.c_ushort),
                ("wParamH", ctypes.c_ushort)
            ]
            
        class INPUT_UNION(ctypes.Union):
            _fields_ = [
                ("ki", KEYBDINPUT),
                ("mi", MOUSEINPUT),
                ("hi", HARDWAREINPUT)
            ]
            
        class INPUT(ctypes.Structure):
            _fields_ = [
                ("type", ctypes.c_ulong),
                ("ii", INPUT_UNION)
            ]
            
    except Exception as e:
        print(f"Warning: Failed to load Windows input driver libraries: {e}")

def send_keypress(keycode):
    """Simulates a physical key down and key up event based on the current OS"""
    with state_lock:
        humanizer_enabled = state["humanizer_enabled"]
        
    # Micro key hold duration (40ms ~ 80ms if humanizer is active, else 50ms)
    hold_time = random.uniform(0.04, 0.08) if humanizer_enabled else 0.05
    
    if IS_MAC:
        if not cg_loaded:
            print(f"[Mac Simulated Keystroke] OS Code: {keycode}")
            return
        try:
            event_down = cg.CGEventCreateKeyboardEvent(None, keycode, True)
            event_up = cg.CGEventCreateKeyboardEvent(None, keycode, False)
            if event_down and event_up:
                cg.CGEventPost(0, event_down)
                time.sleep(hold_time)
                cg.CGEventPost(0, event_up)
                cf.CFRelease(event_down)
                cf.CFRelease(event_up)
        except Exception as e:
            print(f"Error simulating macOS keycode {keycode}: {e}")
            
    elif IS_WINDOWS:
        if user32 is None:
            print(f"[Windows Simulated Keystroke] OS Code: {keycode}")
            return
        try:
            extra = ctypes.c_void_p(0)
            
            # Translate VK Code to Hardware ScanCode for maximum compatibility with DirectInput/DirectX games
            scan_code = user32.MapVirtualKeyW(keycode, 0)
            
            # Check if it is an extended key (such as Left, Up, Right, Down arrows, Delete, etc.)
            is_extended = keycode in [0x25, 0x26, 0x27, 0x28, 0x2E, 0x2D, 0x24, 0x23, 0x21, 0x22]
            
            flags_down = 0x0008  # KEYEVENTF_SCANCODE
            flags_up = 0x0008 | 0x0002  # KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
            
            if is_extended:
                flags_down |= 0x0001
                flags_up |= 0x0001
                
            # Key Down struct using Scancode
            ki_down = KEYBDINPUT(wVk=0, wScan=scan_code, dwFlags=flags_down, time=0, dwExtraInfo=extra)
            ii_down = INPUT_UNION(ki=ki_down)
            input_down = INPUT(type=1, ii=ii_down)  # type 1 is INPUT_KEYBOARD
            
            # Key Up struct using Scancode
            ki_up = KEYBDINPUT(wVk=0, wScan=scan_code, dwFlags=flags_up, time=0, dwExtraInfo=extra)
            ii_up = INPUT_UNION(ki=ki_up)
            input_up = INPUT(type=1, ii=ii_up)
            
            # Post events using native user32 SendInput
            user32.SendInput(1, ctypes.byref(input_down), ctypes.sizeof(input_down))
            time.sleep(hold_time)
            user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(input_up))
        except Exception as e:
            print(f"Error simulating Windows keycode {keycode}: {e}")
            
    else:
        print(f"[Simulated Keystroke] Unsupported OS. Keycode: {keycode}")

def send_key_down(keycode):
    """Simulates a key down event globally"""
    if IS_MAC:
        if not cg_loaded: return
        try:
            event = cg.CGEventCreateKeyboardEvent(None, keycode, True)
            if event:
                cg.CGEventPost(0, event)
                cf.CFRelease(event)
        except Exception as e:
            print(f"Error simulating macOS key down: {e}")
    elif IS_WINDOWS:
        if user32 is None: return
        try:
            scan_code = user32.MapVirtualKeyW(keycode, 0)
            is_extended = keycode in [0x25, 0x26, 0x27, 0x28, 0x2E, 0x2D, 0x24, 0x23, 0x21, 0x22]
            flags = 0x0008  # KEYEVENTF_SCANCODE
            if is_extended: flags |= 0x0001
            ki = KEYBDINPUT(wVk=0, wScan=scan_code, dwFlags=flags, time=0, dwExtraInfo=ctypes.c_void_p(0))
            ii = INPUT_UNION(ki=ki)
            inp = INPUT(type=1, ii=ii)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        except Exception as e:
            print(f"Error simulating Windows key down: {e}")

def send_key_up(keycode):
    """Simulates a key up event globally"""
    if IS_MAC:
        if not cg_loaded: return
        try:
            event = cg.CGEventCreateKeyboardEvent(None, keycode, False)
            if event:
                cg.CGEventPost(0, event)
                cf.CFRelease(event)
        except Exception as e:
            print(f"Error simulating macOS key up: {e}")
    elif IS_WINDOWS:
        if user32 is None: return
        try:
            scan_code = user32.MapVirtualKeyW(keycode, 0)
            is_extended = keycode in [0x25, 0x26, 0x27, 0x28, 0x2E, 0x2D, 0x24, 0x23, 0x21, 0x22]
            flags = 0x0008 | 0x0002  # KEYEVENTF_SCANCODE | KEYEVENTF_KEYUP
            if is_extended: flags |= 0x0001
            ki = KEYBDINPUT(wVk=0, wScan=scan_code, dwFlags=flags, time=0, dwExtraInfo=ctypes.c_void_p(0))
            ii = INPUT_UNION(ki=ki)
            inp = INPUT(type=1, ii=ii)
            user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))
        except Exception as e:
            print(f"Error simulating Windows key up: {e}")

def get_pixel_color(x, y):
    """Reads screen pixel RGB color at coordinate (x, y) dynamically without external dependencies"""
    r, g, b = 0, 0, 0
    if IS_MAC and cg_loaded:
        try:
            display_id = cg.CGMainDisplayID()
            rect = CGRect(CGPoint(x, y), CGSize(1, 1))
            image = cg.CGDisplayCreateImageForRect(display_id, rect)
            if image:
                provider = cg.CGImageGetDataProvider(image)
                data = cg.CGDataProviderCopyData(provider)
                if data:
                    ptr = cf.CFDataGetBytePtr(data)
                    char_ptr = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ubyte))
                    # BGRA format is standard on macOS CoreGraphics
                    b = char_ptr[0]
                    g = char_ptr[1]
                    r = char_ptr[2]
                    cf.CFRelease(data)
                cf.CFRelease(image)
        except Exception as e:
            pass
    elif IS_WINDOWS and user32 is not None:
        try:
            hdc = user32.GetDC(0)
            color = ctypes.windll.gdi32.GetPixel(hdc, x, y)
            r = color & 0xff
            g = (color >> 8) & 0xff
            b = (color >> 16) & 0xff
            user32.ReleaseDC(0, hdc)
        except Exception as e:
            pass
    return f"#{r:02X}{g:02X}{b:02X}"

def set_mouse_pos(x, y):
    """Warp mouse to (x, y)."""
    if IS_MAC and cg_loaded:
        try:
            cg.CGWarpMouseCursorPosition(CGPoint(x, y))
        except Exception as e:
            print(f"[Mouse Move] Error: {e}")
    elif IS_WINDOWS and user32 is not None:
        try:
            user32.SetCursorPos(x, y)
        except Exception as e:
            print(f"[Mouse Move] Error: {e}")
    else:
        print("[Mouse Move] Unsupported OS.")

# Alias for readability
warp_mouse = set_mouse_pos
    
def click_mouse(button=0, double=False, x=None, y=None):
    """Simulates mouse click.
    button: 0 = left, 1 = right.
    double: whether to perform a double click.
    x, y: optional screen coordinates; if provided, the click event will be at that location.
    """
    # Determine click location
    pos_x = x if x is not None else 0
    pos_y = y if y is not None else 0
    if IS_MAC and cg_loaded:
        try:
            btn_down = 1 if button == 0 else 2  # kCGEventLeftMouseDown / RightMouseDown
            btn_up = 3 if button == 0 else 4   # kCGEventLeftMouseUp / RightMouseUp
            # First click at given position
            ev_down = cg.CGEventCreateMouseEvent(None, btn_down, CGPoint(pos_x, pos_y), button)
            ev_up = cg.CGEventCreateMouseEvent(None, btn_up, CGPoint(pos_x, pos_y), button)
            if ev_down and ev_up:
                cg.CGEventPost(0, ev_down)
                cg.CGEventPost(0, ev_up)
                cf.CFRelease(ev_down)
                cf.CFRelease(ev_up)
            if double:
                time.sleep(0.05)
                ev_down2 = cg.CGEventCreateMouseEvent(None, btn_down, CGPoint(pos_x, pos_y), button)
                ev_up2 = cg.CGEventCreateMouseEvent(None, btn_up, CGPoint(pos_x, pos_y), button)
                if ev_down2 and ev_up2:
                    cg.CGEventPost(0, ev_down2)
                    cg.CGEventPost(0, ev_up2)
                    cf.CFRelease(ev_down2)
                    cf.CFRelease(ev_up2)
        except Exception as e:
            print(f"[Mouse Click] Error: {e}")
    elif IS_WINDOWS and user32 is not None:
        # Windows mouse click implementation omitted for brevity
        pass

    """Warps the mouse pointer to screen coordinate (x, y)"""
    if IS_MAC and cg_loaded:
        try:
            cg.CGWarpMouseCursorPosition(CGPoint(x, y))
        except Exception as e:
            print(f"Error warp mouse macOS: {e}")
    elif IS_WINDOWS and user32 is not None:
        try:
            user32.SetCursorPos(x, y)
        except Exception as e:
            print(f"Error warp mouse Windows: {e}")

def get_screen_scale():
    """Calculates the host screen scale factor (Retina/DPI Scaling)"""
    if IS_MAC and cg_loaded:
        try:
            display_id = cg.CGMainDisplayID()
            bounds = cg.CGDisplayBounds(display_id)
            points_wide = bounds.size.width
            pixels_wide = cg.CGDisplayPixelsWide(display_id)
            if points_wide > 0:
                return float(pixels_wide) / float(points_wide)
        except Exception as e:
            print(f"Error calculating macOS screen scale: {e}")
    elif IS_WINDOWS and user32 is not None:
        try:
            hdc = user32.GetDC(0)
            logpixelsy = ctypes.windll.gdi32.GetDeviceCaps(hdc, 90) # LOGPIXELSY
            user32.ReleaseDC(0, hdc)
            return float(logpixelsy) / 96.0
        except Exception as e:
            pass
    return 1.0

def pack_rgb_to_bmp(width, height, raw_bgra):
    """Packs raw BGRA pixel data into a standard 32-bit BMP bytearray directly (no external dependencies)"""
    pixel_data_size = width * height * 4
    file_size = 54 + pixel_data_size
    
    # BMP File Header (14 bytes): Magic, FileSize, Reserved1, Reserved2, Offset
    file_header = struct.pack("<2sIHHI", b"BM", file_size, 0, 0, 54)
    
    # BMP Info Header (40 bytes - BITMAPINFOHEADER): HeaderSize, Width, Height, Planes, BPP, Compression, ImageSize, Xppm, Yppm, Colors, ImportantColors
    # Use negative height for a top-down DIB layout
    info_header = struct.pack("<IiiHHIIiiII", 40, width, -height, 1, 32, 0, pixel_data_size, 2835, 2835, 0, 0)
    
    return file_header + info_header + raw_bgra

def capture_minimap_as_bmp():
    """Captures the minimap region based on configured offsets (400x400 logical points) and encodes it as BMP bytes"""
    scale = get_screen_scale()
    
    with state_lock:
        offset_x = state.get("minimap_offset_x", 0)
        offset_y = state.get("minimap_offset_y", 0)
        
    search_width = int(400 * scale)
    search_height = int(400 * scale)
    
    phys_offset_x = int(offset_x * scale)
    phys_offset_y = int(offset_y * scale)
    
    if IS_MAC and cg_loaded:
        try:
            display_id = cg.CGMainDisplayID()
            rect = CGRect(CGPoint(phys_offset_x, phys_offset_y), CGSize(search_width, search_height))
            image = cg.CGDisplayCreateImageForRect(display_id, rect)
            if image:
                provider = cg.CGImageGetDataProvider(image)
                data = cg.CGDataProviderCopyData(provider)
                if data:
                    ptr = cf.CFDataGetBytePtr(data)
                    bytes_per_row = cg.CGImageGetBytesPerRow(image)
                    char_ptr = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ubyte))
                    
                    clean_bgra = bytearray(search_width * search_height * 4)
                    
                    # Copy row by row safely using python bytearray slices
                    for y in range(search_height):
                        src_offset = y * bytes_per_row
                        dest_offset = y * search_width * 4
                        clean_bgra[dest_offset : dest_offset + search_width * 4] = char_ptr[src_offset : src_offset + search_width * 4]
                        
                    cf.CFRelease(data)
                    cf.CFRelease(image)
                    return pack_rgb_to_bmp(search_width, search_height, clean_bgra)
        except Exception as e:
            print(f"Error capturing minimap macOS: {e}")
            
    elif IS_WINDOWS and user32 is not None:
        try:
            hdc_screen = user32.GetDC(0)
            hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
            h_bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_screen, search_width, search_height)
            h_old = ctypes.windll.gdi32.SelectObject(hdc_mem, h_bitmap)
            
            # SRCCOPY BitBlt
            ctypes.windll.gdi32.BitBlt(hdc_mem, 0, 0, search_width, search_height, hdc_screen, phys_offset_x, phys_offset_y, 0x00CC0020)
            
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", ctypes.c_ulong), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                    ("biPlanes", ctypes.c_ushort), ("biBitCount", ctypes.c_ushort), ("biCompression", ctypes.c_ulong),
                    ("biSizeImage", ctypes.c_ulong), ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
                    ("biClrUsed", ctypes.c_ulong), ("biClrImportant", ctypes.c_ulong)
                ]
            class BITMAPINFO(ctypes.Structure):
                _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_ulong * 3)]
                
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = search_width
            bmi.bmiHeader.biHeight = -search_height # Top-down DIB
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = 0
            
            buffer_size = search_width * search_height * 4
            buffer = (ctypes.c_ubyte * buffer_size)()
            
            ctypes.windll.gdi32.GetDIBits(hdc_screen, h_bitmap, 0, search_height, ctypes.byref(buffer), ctypes.byref(bmi), 0)
            
            # GDI cleanup
            ctypes.windll.gdi32.SelectObject(hdc_mem, h_old)
            ctypes.windll.gdi32.DeleteObject(h_bitmap)
            ctypes.windll.gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)
            
            return pack_rgb_to_bmp(search_width, search_height, bytearray(buffer))
        except Exception as e:
            print(f"Error capturing minimap Windows: {e}")
            
    return None

def find_character_yellow_dot():
    """Scans the configured minimap area for the character's yellow dot pixel and returns its logical coordinates (relative to the minimap area)"""
    scale = get_screen_scale()
    
    with state_lock:
        offset_x = state.get("minimap_offset_x", 0)
        offset_y = state.get("minimap_offset_y", 0)
        
    search_width = int(400 * scale)
    search_height = int(400 * scale)
    
    phys_offset_x = int(offset_x * scale)
    phys_offset_y = int(offset_y * scale)
    
    if IS_MAC and cg_loaded:
        try:
            display_id = cg.CGMainDisplayID()
            rect = CGRect(CGPoint(phys_offset_x, phys_offset_y), CGSize(search_width, search_height))
            image = cg.CGDisplayCreateImageForRect(display_id, rect)
            if image:
                provider = cg.CGImageGetDataProvider(image)
                data = cg.CGDataProviderCopyData(provider)
                if data:
                    ptr = cf.CFDataGetBytePtr(data)
                    bytes_per_row = cg.CGImageGetBytesPerRow(image)
                    char_ptr = ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ubyte))
                    
                    yellow_pixels = []
                    # Scan every 1 pixel for exact centroid calculation
                    for y in range(0, search_height):
                        for x in range(0, search_width):
                            offset = y * bytes_per_row + x * 4
                            b = char_ptr[offset]
                            g = char_ptr[offset+1]
                            r = char_ptr[offset+2]
                            
                            # Yellow character dot threshold (R>=240, G>=200, B<=40)
                            if r >= 240 and g >= 200 and b <= 40:
                                yellow_pixels.append((x, y))
                                
                    cf.CFRelease(data)
                    cf.CFRelease(image)
                    
                    if yellow_pixels:
                        avg_x = sum(p[0] for p in yellow_pixels) / len(yellow_pixels)
                        avg_y = sum(p[1] for p in yellow_pixels) / len(yellow_pixels)
                        # Convert to logical coordinate
                        return int(avg_x / scale), int(avg_y / scale)
        except Exception as e:
            print(f"Error scanning yellow dot macOS: {e}")
            
    elif IS_WINDOWS and user32 is not None:
        try:
            hdc_screen = user32.GetDC(0)
            hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc_screen)
            h_bitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc_screen, search_width, search_height)
            h_old = ctypes.windll.gdi32.SelectObject(hdc_mem, h_bitmap)
            
            # SRCCOPY BitBlt
            ctypes.windll.gdi32.BitBlt(hdc_mem, 0, 0, search_width, search_height, hdc_screen, phys_offset_x, phys_offset_y, 0x00CC0020)
            
            class BITMAPINFOHEADER(ctypes.Structure):
                _fields_ = [
                    ("biSize", ctypes.c_ulong), ("biWidth", ctypes.c_long), ("biHeight", ctypes.c_long),
                    ("biPlanes", ctypes.c_ushort), ("biBitCount", ctypes.c_ushort), ("biCompression", ctypes.c_ulong),
                    ("biSizeImage", ctypes.c_ulong), ("biXPelsPerMeter", ctypes.c_long), ("biYPelsPerMeter", ctypes.c_long),
                    ("biClrUsed", ctypes.c_ulong), ("biClrImportant", ctypes.c_ulong)
                ]
            class BITMAPINFO(ctypes.Structure):
                _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", ctypes.c_ulong * 3)]
                
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = search_width
            bmi.bmiHeader.biHeight = -search_height # Top-down DIB
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = 0
            
            buffer_size = search_width * search_height * 4
            buffer = (ctypes.c_ubyte * buffer_size)()
            
            ctypes.windll.gdi32.GetDIBits(hdc_screen, h_bitmap, 0, search_height, ctypes.byref(buffer), ctypes.byref(bmi), 0)
            
            # GDI cleanup
            ctypes.windll.gdi32.SelectObject(hdc_mem, h_old)
            ctypes.windll.gdi32.DeleteObject(h_bitmap)
            ctypes.windll.gdi32.DeleteDC(hdc_mem)
            user32.ReleaseDC(0, hdc_screen)
            
            yellow_pixels = []
            for y in range(0, search_height):
                for x in range(0, search_width):
                    offset = (y * search_width + x) * 4
                    b = buffer[offset]
                    g = buffer[offset+1]
                    r = buffer[offset+2]
                    
                    if r >= 240 and g >= 200 and b <= 40:
                        yellow_pixels.append((x, y))
                        
            if yellow_pixels:
                avg_x = sum(p[0] for p in yellow_pixels) / len(yellow_pixels)
                avg_y = sum(p[1] for p in yellow_pixels) / len(yellow_pixels)
                # Convert to logical coordinate
                return int(avg_x / scale), int(avg_y / scale)
        except Exception as e:
            print(f"Error scanning yellow dot Windows: {e}")
            
    return None

def get_mouse_pos_and_color():
    """Reads current mouse cursor position and color underneath it"""
    x, y = 0, 0
    color_hex = "#000000"
    if IS_MAC and cg_loaded:
        try:
            evt = cg.CGEventCreate(None)
            pos = cg.CGEventGetLocation(evt)
            x, y = int(pos.x), int(pos.y)
            cf.CFRelease(evt)
            color_hex = get_pixel_color(x, y)
        except Exception as e:
            print(f"Error getting mouse pos/color macOS: {e}")
    elif IS_WINDOWS and user32 is not None:
        try:
            pt = POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            x, y = pt.x, pt.y
            color_hex = get_pixel_color(x, y)
        except Exception as e:
            print(f"Error getting mouse pos/color Windows: {e}")
    return x, y, color_hex

def presser_thread_func():
    """Background worker thread executing keypress loop at specified intervals"""
    global state
    
    last_macro_time = time.time()
    next_macro_delay = 60.0  # Dynamic macro delay target (randomized if humanizer is active)
    
    while True:
        with state_lock:
            running = state["running"]
            keycode = state["keycode"]
            interval_ms = state["interval_ms"]
            macro_enabled = state["macro_enabled"]
            humanizer_enabled = state["humanizer_enabled"]
            
        if running:
            # Jittering key press interval (±8% of interval, max ±100ms) to remove uniform rhythm
            if humanizer_enabled and interval_ms > 50:
                jitter_range = min(100, int(interval_ms * 0.08))
                actual_interval = (interval_ms + random.randint(-jitter_range, jitter_range)) / 1000.0
            else:
                actual_interval = interval_ms / 1000.0
                
            # Check macro timer
            current_time = time.time()
            if macro_enabled and (current_time - last_macro_time >= next_macro_delay):
                # Idle pause (randomized between 1.7s and 2.5s if humanizer active, else 2s)
                idle_delay = random.uniform(1.7, 2.5) if humanizer_enabled else 2.0
                print(f"[Macro] Idle delay: pausing {idle_delay:.2f} seconds before movement...")
                time.sleep(idle_delay)
                
                left_kc = 123 if IS_MAC else 0x25
                right_kc = 124 if IS_MAC else 0x27
                up_kc = 126 if IS_MAC else 0x26
                down_kc = 125 if IS_MAC else 0x28
                
                with state_lock:
                    actions = list(state.get("macro_actions", []))
                    base_interval = state.get("macro_interval_s", 60.0)
                
                # Execute actions in sequence
                for idx, act in enumerate(actions):
                    act_type = act.get("type", "right")
                    duration = max(0.05, float(act.get("duration_s", 1.0)))
                    
                    # Apply humanizer jitter to duration if enabled (±8%)
                    if humanizer_enabled and duration > 0.5:
                        duration_jitter = duration * 0.08
                        actual_duration = duration + random.uniform(-duration_jitter, duration_jitter)
                    else:
                        actual_duration = duration
                    
                    # Determine target keycode
                    kc = None
                    act_name = act_type
                    if act_type == "left":
                        kc = left_kc
                    elif act_type == "right":
                        kc = right_kc
                    elif act_type == "up":
                        kc = up_kc
                    elif act_type == "down":
                        kc = down_kc
                    elif act_type == "key":
                        kc = act.get("keycode")
                        act_name = f"Key ({act.get('key_name', '?')})"
                    
                    if kc is not None:
                        print(f"[Macro] Action {idx+1}/{len(actions)}: Holding {act_name} for {actual_duration:.2f} seconds...")
                        send_key_down(kc)
                        time.sleep(actual_duration)
                        send_key_up(kc)
                    
                    # Brief pause between sequential actions (randomized if humanizer active)
                    pause_dur = random.uniform(0.15, 0.35) if humanizer_enabled else 0.2
                    time.sleep(pause_dur)
                
                # Apply humanizer jitter to next macro delay if enabled (±8%)
                if humanizer_enabled and base_interval > 5.0:
                    interval_jitter = base_interval * 0.08
                    next_macro_delay = base_interval + random.uniform(-interval_jitter, interval_jitter)
                else:
                    next_macro_delay = base_interval
                
                last_macro_time = time.time()
            
            # Send continuous key
            send_keypress(keycode)
            with state_lock:
                state["count"] += 1
                
            # Smart interruptible sleep
            sleep_event.clear()
            sleep_event.wait(timeout=actual_interval)
        else:
            # Reset timer when stopped
            last_macro_time = time.time()
            with state_lock:
                base_interval = state.get("macro_interval_s", 60.0)
            next_macro_delay = base_interval
            time.sleep(0.1)

def pixel_trigger_thread_func():
    """Background thread polling target pixel color 10 times a second and firing actions on color match"""
    global state
    last_trigger_time = 0
    
    while True:
        with state_lock:
            running = state["running"]
            pixel_macro_enabled = state["pixel_macro_enabled"]
            pixel_x = state["pixel_x"]
            pixel_y = state["pixel_y"]
            pixel_color = state["pixel_color"]
            pixel_match_type = state["pixel_match_type"]
            pixel_action_keycode = state["pixel_action_keycode"]
            pixel_action_name = state["pixel_action_name"]
            pixel_cooldown_s = state["pixel_cooldown_s"]
            
        if running and pixel_macro_enabled:
            current_time = time.time()
            if current_time - last_trigger_time >= pixel_cooldown_s:
                current_color = get_pixel_color(pixel_x, pixel_y)
                
                # Check for color equivalence match
                match = False
                if pixel_match_type == "equal" and current_color.upper() == pixel_color.upper():
                    match = True
                elif pixel_match_type == "not_equal" and current_color.upper() != pixel_color.upper():
                    match = True
                    
                if match:
                    print(f"[Pixel Trigger] Detected matching color {current_color} at ({pixel_x}, {pixel_y}). Firing {pixel_action_name}...")
                    send_keypress(pixel_action_keycode)
                    last_trigger_time = current_time
                    
        # Sleep for 100ms
        time.sleep(0.1)

def jump_trigger_thread_func():
    """Background thread executing the Move & Jump & Climb macro with Minimap yellow dot navigation"""
    global state
    last_trigger_time = 0
    
    # Arrow key codes
    left_kc = 123 if IS_MAC else 0x25
    right_kc = 124 if IS_MAC else 0x27
    up_kc = 126 if IS_MAC else 0x26
    down_kc = 125 if IS_MAC else 0x28
    
    while True:
        with state_lock:
            running = state["running"]
            jump_macro_enabled = state["jump_macro_enabled"]
            jump_x = state["jump_x"] # Target X on Minimap (logical coordinates)
            jump_y = state["jump_y"] # Target Y on Minimap (logical coordinates)
            jump_cooldown_s = state["jump_cooldown_s"]
            jump_action_keycode = state["jump_action_keycode"]
            jump_action_name = state["jump_action_name"]
            humanizer_enabled = state["humanizer_enabled"]
            
        if running and jump_macro_enabled:
            current_time = time.time()
            
            # Apply humanizer jitter to cooldown if enabled (±8%)
            actual_cooldown = jump_cooldown_s
            if humanizer_enabled and jump_cooldown_s > 1.0:
                jitter = jump_cooldown_s * 0.08
                actual_cooldown += random.uniform(-jitter, jitter)
                
            if current_time - last_trigger_time >= actual_cooldown:
                print(f"[Navigate Macro] Commencing movement towards target X: {jump_x} on minimap...")
                
                # 1. Navigation loop
                start_nav_time = time.time()
                nav_timeout = 12.0  # 12 seconds max to reach target
                reached = False
                last_dir = None
                
                while running and (time.time() - start_nav_time < nav_timeout):
                    # Live check of running state
                    with state_lock:
                        running = state["running"]
                        if not running:
                            break
                            
                    pos = find_character_yellow_dot()
                    if pos is None:
                        # If character is not found, abort immediately to prevent key freeze / conflict
                        print("[Navigate Macro] Character yellow dot not found on minimap. Aborting navigation to prevent key conflicts.")
                        if last_dir:
                            send_key_up(last_dir)
                            last_dir = None
                        break
                        
                    curr_x, curr_y = pos
                    diff_x = curr_x - jump_x # + means character is to the right of target -> must move left
                                             # - means character is to the left of target -> must move right
                                             
                    tolerance = 1 # X-axis tolerance tightened to 1 pixel for exact rope alignment
                    
                    if abs(diff_x) <= tolerance:
                        reached = True
                        break
                        
                    if abs(diff_x) > 5:
                        # High distance: hold arrow keys down for normal running speed
                        if diff_x < 0:
                            # Move Right
                            if last_dir == left_kc:
                                send_key_up(left_kc)
                            if last_dir != right_kc:
                                send_key_down(right_kc)
                                last_dir = right_kc
                        else:
                            # Move Left
                            if last_dir == right_kc:
                                send_key_up(right_kc)
                            if last_dir != left_kc:
                                send_key_down(left_kc)
                                last_dir = left_kc
                        time.sleep(0.05) # Scan minimap at 20Hz
                    else:
                        # Close distance (<= 5px): micro-stepping adjustments
                        if last_dir:
                            send_key_up(last_dir)
                            last_dir = None
                            time.sleep(0.15) # Wait brief moment to absorb slide inertia
                            
                        # Perform micro-tap
                        tap_key = right_kc if diff_x < 0 else left_kc
                        send_key_down(tap_key)
                        
                        # Dynamically scale tap duration based on distance
                        tap_duration = 0.035 if abs(diff_x) <= 2 else 0.06
                        time.sleep(tap_duration)
                        send_key_up(tap_key)
                        
                        # Wait for position updates to settle on minimap
                        time.sleep(0.2)
                    
                # Stop walking
                if last_dir:
                    send_key_up(last_dir)
                    
                # Proceed with jump climb ONLY if we successfully reached the target X coordinate
                if reached and running:
                    print("[Navigate Macro] Arrived at target X coordinate. Launching jump grab...")
                    
                    # Brief stop (100ms ~ 250ms)
                    time.sleep(random.uniform(0.1, 0.25) if humanizer_enabled else 0.15)
                    
                    # Press Jump Key
                    send_keypress(jump_action_keycode)
                    
                    # Brief delay before climbing (80ms ~ 150ms)
                    time.sleep(random.uniform(0.08, 0.15) if humanizer_enabled else 0.1)
                    
                    # Climb Up (Hold ArrowUp for 2 seconds)
                    hold_up_duration = random.uniform(1.8, 2.2) if humanizer_enabled else 2.0
                    print(f"[Navigate Macro] Holding ArrowUp for {hold_up_duration:.2f} seconds...")
                    send_key_down(up_kc)
                    time.sleep(hold_up_duration)
                    send_key_up(up_kc)
                    
                    # Brief stop (100ms ~ 250ms)
                    time.sleep(random.uniform(0.1, 0.25) if humanizer_enabled else 0.15)
                    
                    # Climb Down (Hold ArrowDown for 2 seconds)
                    hold_down_duration = random.uniform(1.8, 2.2) if humanizer_enabled else 2.0
                    print(f"[Navigate Macro] Holding ArrowDown for {hold_down_duration:.2f} seconds...")
                    send_key_down(down_kc)
                    time.sleep(hold_down_duration)
                    send_key_up(down_kc)
                else:
                    if not reached:
                        print("[Navigate Macro] Skipping jump grab sequence because target coordinate was not reached or character was not found.")
                    
                last_trigger_time = time.time()
                
        time.sleep(0.1)

def scheduled_macro_thread_func():
    """Background thread executing each user-defined scheduled key press macro independently"""
    global state, _sched_last_triggers
    
    while True:
        with state_lock:
            running = state["running"]
            macros = list(state.get("scheduled_macros", []))
        
        if running:
            current_time = time.time()
            for macro in macros:
                if not macro.get("enabled", False):
                    continue
                macro_id = macro.get("id", "")
                interval = max(0.5, float(macro.get("interval_s", 30.0)))
                press_count = max(1, int(macro.get("press_count", 1)))
                keycode = macro.get("keycode", 49)
                
                last_time = _sched_last_triggers.get(macro_id, 0)
                if current_time - last_time >= interval:
                    _sched_last_triggers[macro_id] = current_time
                    print(f"[Scheduled Macro] Triggering '{macro.get('key_name','?')}' x{press_count} (id={macro_id})")
                    for i in range(press_count):
                        send_keypress(keycode)
                        if i < press_count - 1:
                            time.sleep(0.12)  # Small delay between multiple presses
        
        time.sleep(0.1)

def mouse_macro_thread_func():
    """Background thread executing mouse macro at configured intervals."""
    global _mouse_last_trigger
    _mouse_last_trigger = 0
    while True:
        with state_lock:
            running = state.get("running", False)
            enabled = state.get("mouse_macro_enabled", False)
            interval_min = state.get("mouse_interval_min", 3)
        if running and enabled:
            now = time.time()
            if now - _mouse_last_trigger >= interval_min * 60:
                warp_mouse(state.get("mouse_x1", 100), state.get("mouse_y1", 200))
                click_mouse(x=state.get("mouse_x1", 100), y=state.get("mouse_y1", 200), double=True)
                warp_mouse(state.get("mouse_x2", 300), state.get("mouse_y2", 400))
                click_mouse(x=state.get("mouse_x2", 300), y=state.get("mouse_y2", 400))
                _mouse_last_trigger = now
        time.sleep(0.5)

def load_config():
    """Load configuration settings from config.json if it exists"""
    global state
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                with state_lock:
                    state["key_code_str"] = data.get("key_code_str", "Space")
                    state["key_name"] = data.get("key_name", "Space")
                    state["interval_ms"] = data.get("interval_ms", 1000)
                    state["macro_enabled"] = data.get("macro_enabled", False)
                    state["macro_interval_s"] = data.get("macro_interval_s", 60.0)
                    state["macro_actions"] = data.get("macro_actions", [
                        {"type": "right", "duration_s": 3.0},
                        {"type": "left", "duration_s": 3.0}
                    ])
                    for act in state["macro_actions"]:
                        if act.get("type") == "key" and "key_code_str" in act:
                            act["keycode"] = resolve_keycode(act["key_code_str"])
                    state["humanizer_enabled"] = data.get("humanizer_enabled", True)
                    
                    # Pixel Trigger Config
                    state["pixel_macro_enabled"] = data.get("pixel_macro_enabled", False)
                    state["pixel_x"] = data.get("pixel_x", 100)
                    state["pixel_y"] = data.get("pixel_y", 100)
                    state["pixel_color"] = data.get("pixel_color", "#FFCC00")
                    state["pixel_match_type"] = data.get("pixel_match_type", "equal")
                    state["pixel_action_code_str"] = data.get("pixel_action_code_str", "Space")
                    state["pixel_action_name"] = data.get("pixel_action_name", "Space")
                    state["pixel_cooldown_s"] = data.get("pixel_cooldown_s", 1.5)
                    
                    # Jump Macro Config
                    state["jump_macro_enabled"] = data.get("jump_macro_enabled", False)
                    state["jump_x"] = data.get("jump_x", 100)
                    state["jump_y"] = data.get("jump_y", 100)
                    state["jump_cooldown_s"] = data.get("jump_cooldown_s", 20.0)
                    state["jump_action_code_str"] = data.get("jump_action_code_str", "KeyC")
                    state["jump_action_name"] = data.get("jump_action_name", "C")
                    state["minimap_offset_x"] = data.get("minimap_offset_x", 0)
                    state["minimap_offset_y"] = data.get("minimap_offset_y", 0)
                    state["mouse_macro_enabled"] = data.get("mouse_macro_enabled", False)
                    state["mouse_interval_min"] = data.get("mouse_interval_min", 3)
                    state["mouse_x1"] = data.get("mouse_x1", 100)
                    state["mouse_y1"] = data.get("mouse_y1", 200)
                    state["mouse_x2"] = data.get("mouse_x2", 300)
                    state["mouse_y2"] = data.get("mouse_y2", 400)
                    
                    # Scheduled Macros Config
                    raw_scheds = data.get("scheduled_macros", [])
                    resolved_scheds = []
                    for m in raw_scheds:
                        m["keycode"] = resolve_keycode(m.get("key_code_str", "Space"))
                        resolved_scheds.append(m)
                    state["scheduled_macros"] = resolved_scheds
                    
                    # Resolve keycodes
                    state["keycode"] = resolve_keycode(state["key_code_str"])
                    state["pixel_action_keycode"] = resolve_keycode(state["pixel_action_code_str"])
                    state["jump_action_keycode"] = resolve_keycode(state["jump_action_code_str"])
            print(f"[Config] Loaded successfully.")
        except Exception as e:
            print(f"[Config] Error loading configuration: {e}")

def save_config():
    """Save current configuration to config.json"""
    with state_lock:
        data = {
            "key_code_str": state["key_code_str"],
            "key_name": state["key_name"],
            "interval_ms": state["interval_ms"],
            "macro_enabled": state["macro_enabled"],
            "macro_interval_s": state["macro_interval_s"],
            "macro_actions": [
                {k: v for k, v in act.items() if not k.startswith("_")}
                for act in state.get("macro_actions", [])
            ],
            "humanizer_enabled": state["humanizer_enabled"],
            
            # Pixel Trigger Config
            "pixel_macro_enabled": state["pixel_macro_enabled"],
            "pixel_x": state["pixel_x"],
            "pixel_y": state["pixel_y"],
            "pixel_color": state["pixel_color"],
            "pixel_match_type": state["pixel_match_type"],
            "pixel_action_code_str": state["pixel_action_code_str"],
            "pixel_action_name": state["pixel_action_name"],
            "pixel_cooldown_s": state["pixel_cooldown_s"],
            
            # Jump Macro Config
            "jump_macro_enabled": state["jump_macro_enabled"],
            "jump_x": state["jump_x"],
            "jump_y": state["jump_y"],
            "jump_cooldown_s": state["jump_cooldown_s"],
            "jump_action_code_str": state["jump_action_code_str"],
            "jump_action_name": state["jump_action_name"],
            "minimap_offset_x": state["minimap_offset_x"],
            "minimap_offset_y": state["minimap_offset_y"],
            "mouse_macro_enabled": state["mouse_macro_enabled"],
            "mouse_interval_min": state["mouse_interval_min"],
            "mouse_x1": state["mouse_x1"],
            "mouse_y1": state["mouse_y1"],
            "mouse_x2": state["mouse_x2"],
            "mouse_y2": state["mouse_y2"],
            
            # Scheduled Macros (stored without internal-only fields)
            "scheduled_macros": [
                {k: v for k, v in m.items() if not k.startswith("_")}
                for m in state.get("scheduled_macros", [])
            ]
        }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"[Config] Error saving configuration: {e}")

class AutoKeyAPIHandler(BaseHTTPRequestHandler):
    """Local HTTP Server that serves frontend pages and handles REST API requests"""
    
    def log_message(self, format, *args):
        # Suppress logging of every API poll to keep terminal output readable
        try:
            log_str = format % args
            if "GET /api/status" in log_str:
                return
        except Exception:
            pass
        super().log_message(format, *args)
        
    def do_GET(self):
        if self.path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with state_lock:
                state["macos_accessible"] = check_accessibility_privilege()
                res = json.dumps(state)
            self.wfile.write(res.encode("utf-8"))
            
        elif self.path == "/api/pick":
            # Read current mouse position and pixel color under it
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            x, y, color = get_mouse_pos_and_color()
            res = json.dumps({"x": x, "y": y, "color": color})
            self.wfile.write(res.encode("utf-8"))
            
        elif self.path.startswith("/api/capture_minimap"):
            # Capture minimap area as standard 32-bit BMP
            bmp_data = capture_minimap_as_bmp()
            if bmp_data:
                self.send_response(200)
                self.send_header("Content-Type", "image/bmp")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(bmp_data)))
                self.end_headers()
                self.wfile.write(bmp_data)
            else:
                self.send_response(500)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b"Failed to capture screen")
                
        else:
            # Server static files
            clean_path = self.path.split("?")[0].lstrip("/")
            if not clean_path or clean_path == "index.html":
                filepath = resource_path(os.path.join("web", "index.html"))
            else:
                filepath = resource_path(os.path.join("web", clean_path))
                
            # Prevent directory traversal
            abs_filepath = os.path.abspath(filepath)
            abs_web_dir = os.path.abspath(resource_path("web"))
            if not abs_filepath.startswith(abs_web_dir):
                self.send_error(403, "Access Denied")
                return
                
            if os.path.exists(filepath) and os.path.isfile(filepath):
                ext = os.path.splitext(filepath)[1].lower()
                mime = {
                    ".html": "text/html",
                    ".css": "text/css",
                    ".js": "application/javascript",
                    ".json": "application/json",
                    ".png": "image/png",
                    ".jpg": "image/jpeg",
                    ".jpeg": "image/jpeg",
                    ".ico": "image/x-icon"
                }.get(ext, "text/plain")
                
                try:
                    with open(filepath, "rb") as f:
                        content = f.read()
                    self.send_response(200)
                    self.send_header("Content-Type", mime)
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                except Exception as e:
                    self.send_error(500, f"Internal Server Error: {e}")
            else:
                self.send_error(404, "File Not Found")
                
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""
        
        response_data = {"success": True}
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        if self.path == "/api/start":
            with state_lock:
                state["running"] = True
            sleep_event.set()
            print("[Control] Auto-keypresser started.")
        elif self.path == "/api/stop":
            with state_lock:
                state["running"] = False
            sleep_event.set()
            print("[Control] Auto-keypresser stopped.")
        elif self.path == "/api/config":
            try:
                data = json.loads(body)
                with state_lock:
                    if "key_code_str" in data:
                        state["key_code_str"] = str(data["key_code_str"])
                        state["keycode"] = resolve_keycode(state["key_code_str"])
                    if "key_name" in data:
                        state["key_name"] = str(data["key_name"])
                    if "interval_ms" in data:
                        state["interval_ms"] = max(10, int(data["interval_ms"]))
                    if "macro_enabled" in data:
                        state["macro_enabled"] = bool(data["macro_enabled"])
                    if "macro_interval_s" in data:
                        state["macro_interval_s"] = max(1.0, float(data["macro_interval_s"]))
                    if "macro_actions" in data:
                        raw_actions = data["macro_actions"]
                        if isinstance(raw_actions, list):
                            for act in raw_actions:
                                if act.get("type") == "key" and "key_code_str" in act:
                                    act["keycode"] = resolve_keycode(act["key_code_str"])
                            state["macro_actions"] = raw_actions
                    if "humanizer_enabled" in data:
                        state["humanizer_enabled"] = bool(data["humanizer_enabled"])
                        
                    # Parse Pixel trigger configurations
                    if "pixel_macro_enabled" in data:
                        state["pixel_macro_enabled"] = bool(data["pixel_macro_enabled"])
                    if "pixel_x" in data:
                        state["pixel_x"] = int(data["pixel_x"])
                    if "pixel_y" in data:
                        state["pixel_y"] = int(data["pixel_y"])
                    if "pixel_color" in data:
                        state["pixel_color"] = str(data["pixel_color"])
                    if "pixel_match_type" in data:
                        state["pixel_match_type"] = str(data["pixel_match_type"])
                    if "pixel_action_code_str" in data:
                        state["pixel_action_code_str"] = str(data["pixel_action_code_str"])
                        state["pixel_action_keycode"] = resolve_keycode(state["pixel_action_code_str"])
                    if "pixel_action_name" in data:
                        state["pixel_action_name"] = str(data["pixel_action_name"])
                    if "pixel_cooldown_s" in data:
                        state["pixel_cooldown_s"] = max(0.1, float(data["pixel_cooldown_s"]))
                        
                    # Parse Jump macro configurations
                    if "jump_macro_enabled" in data:
                        state["jump_macro_enabled"] = bool(data["jump_macro_enabled"])
                    if "jump_x" in data:
                        state["jump_x"] = int(data["jump_x"])
                    if "jump_y" in data:
                        state["jump_y"] = int(data["jump_y"])
                    if "jump_cooldown_s" in data:
                        state["jump_cooldown_s"] = max(0.5, float(data["jump_cooldown_s"]))
                    if "jump_action_code_str" in data:
                        state["jump_action_code_str"] = str(data["jump_action_code_str"])
                        state["jump_action_keycode"] = resolve_keycode(state["jump_action_code_str"])
                    if "jump_action_name" in data:
                        state["jump_action_name"] = str(data["jump_action_name"])
                    if "minimap_offset_x" in data:
                        state["minimap_offset_x"] = int(data["minimap_offset_x"])
                    if "minimap_offset_y" in data:
                        state["minimap_offset_y"] = int(data["minimap_offset_y"])
                    if "mouse_macro_enabled" in data:
                        state["mouse_macro_enabled"] = bool(data["mouse_macro_enabled"])
                    if "mouse_interval_min" in data:
                        state["mouse_interval_min"] = max(1, int(data["mouse_interval_min"]))
                    if "mouse_x1" in data:
                        state["mouse_x1"] = int(data["mouse_x1"])
                    if "mouse_y1" in data:
                        state["mouse_y1"] = int(data["mouse_y1"])
                    if "mouse_x2" in data:
                        state["mouse_x2"] = int(data["mouse_x2"])
                    if "mouse_y2" in data:
                        state["mouse_y2"] = int(data["mouse_y2"])
                    if "scheduled_macros" in data:
                        # Resolve keycodes for each scheduled macro
                        raw_list = data["scheduled_macros"]
                        if isinstance(raw_list, list):
                            for m in raw_list:
                                m["keycode"] = resolve_keycode(m.get("key_code_str", "Space"))
                            state["scheduled_macros"] = raw_list
                        
                save_config()
                sleep_event.set()  # Apply changes immediately
                print(f"[Control] Config updated.")
            except Exception as e:
                response_data = {"success": False, "error": str(e)}
        else:
            self.send_error(404, "API Endpoint Not Found")
            return
            
        self.wfile.write(json.dumps(response_data).encode("utf-8"))
        
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def open_dashboard():
    """Wait for server to start, then launch default web browser to the controller URL"""
    time.sleep(1.2)
    print("\n=============================================")
    print("AutoKey Web Dashboard is running at:")
    print("👉 http://localhost:5001")
    print("=============================================\n")
    webbrowser.open("http://localhost:5001")

if __name__ == "__main__":
    # Ensure current working directory is correct
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Load config file settings
    load_config()
    
    # Initialize background keypress loop
    threading.Thread(target=presser_thread_func, daemon=True).start()
    
    # Initialize background pixel checking loop
    threading.Thread(target=pixel_trigger_thread_func, daemon=True).start()
    
    # Initialize background move & jump macro loop
    threading.Thread(target=jump_trigger_thread_func, daemon=True).start()
    
    # Initialize background scheduled key macro loop
    threading.Thread(target=scheduled_macro_thread_func, daemon=True).start()
    
    # Open dashboard in browser
    threading.Thread(target=open_dashboard, daemon=True).start()
    threading.Thread(target=mouse_macro_thread_func, daemon=True).start()
    
    # Start Web API Server
    server_address = ("", 5001)
    httpd = HTTPServer(server_address, AutoKeyAPIHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping AutoKey Web Server. Goodbye!")
        sys.exit(0)
