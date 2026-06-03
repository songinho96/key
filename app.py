import ctypes
import time
import sys
import os
import json
import threading
import webbrowser
import platform
import random
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
    "humanizer_enabled": True,  # Anti-Detection (Humanizer) Mode
    
    # Pixel Trigger Macro State
    "pixel_macro_enabled": False,
    "pixel_x": 100,
    "pixel_y": 100,
    "pixel_color": "#FFCC00",
    "pixel_match_type": "equal", # "equal" or "not_equal"
    "pixel_action_code_str": "Space",
    "pixel_action_keycode": 49,
    "pixel_action_name": "Space",
    "pixel_cooldown_s": 1.5
}
state_lock = threading.Lock()
sleep_event = threading.Event()

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
                
                if humanizer_enabled:
                    # Randomized direction order (Right->Left or Left->Right)
                    directions = [(right_kc, "Right"), (left_kc, "Left")]
                    if random.choice([True, False]):
                        directions = [(left_kc, "Left"), (right_kc, "Right")]
                        
                    # Randomized steps (3 to 6 steps per direction, slightly uneven to look natural)
                    steps_first = random.randint(3, 6)
                    steps_second = random.randint(3, 6)
                    
                    print(f"[Macro] Executing humanized movement: {directions[0][1]} x{steps_first}, {directions[1][1]} x{steps_second}...")
                    
                    # 1st Direction movement
                    for _ in range(steps_first):
                        send_keypress(directions[0][0])
                        time.sleep(random.uniform(0.14, 0.22))
                        
                    # Brief stop between switching directions (200ms ~ 500ms)
                    time.sleep(random.uniform(0.2, 0.5))
                    
                    # 2nd Direction movement
                    for _ in range(steps_second):
                        send_keypress(directions[1][0])
                        time.sleep(random.uniform(0.14, 0.22))
                    
                    # Next macro delay gets randomized (between 50 and 70 seconds)
                    next_macro_delay = random.uniform(50.0, 70.0)
                else:
                    # Uniform mode: Right x4, Left x4
                    print("[Macro] Executing uniform movement: Right x4, Left x4...")
                    for _ in range(4):
                        send_keypress(right_kc)
                        time.sleep(0.18)
                    for _ in range(4):
                        send_keypress(left_kc)
                        time.sleep(0.18)
                    next_macro_delay = 60.0
                    
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
            next_macro_delay = random.uniform(50.0, 70.0) if humanizer_enabled else 60.0
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
                    
                    # Resolve keycodes
                    state["keycode"] = resolve_keycode(state["key_code_str"])
                    state["pixel_action_keycode"] = resolve_keycode(state["pixel_action_code_str"])
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
            "humanizer_enabled": state["humanizer_enabled"],
            
            # Pixel Trigger Config
            "pixel_macro_enabled": state["pixel_macro_enabled"],
            "pixel_x": state["pixel_x"],
            "pixel_y": state["pixel_y"],
            "pixel_color": state["pixel_color"],
            "pixel_match_type": state["pixel_match_type"],
            "pixel_action_code_str": state["pixel_action_code_str"],
            "pixel_action_name": state["pixel_action_name"],
            "pixel_cooldown_s": state["pixel_cooldown_s"]
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
    
    # Open dashboard in browser
    threading.Thread(target=open_dashboard, daemon=True).start()
    
    # Start Web API Server
    server_address = ("", 5001)
    httpd = HTTPServer(server_address, AutoKeyAPIHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping AutoKey Web Server. Goodbye!")
        sys.exit(0)
