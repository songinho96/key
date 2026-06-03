import ctypes
import time
import sys
import os
import json
import threading
import webbrowser
import platform
from http.server import HTTPServer, BaseHTTPRequestHandler

# Detect OS
IS_MAC = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"

# Configuration and State
CONFIG_FILE = "config.json"
state = {
    "running": False,
    "key_code_str": "Space", # Standard JS KeyboardEvent.code
    "keycode": 49,          # Resolved OS-specific virtual code
    "key_name": "Space",
    "interval_ms": 1000,
    "count": 0,
    "macro_enabled": False
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

def resolve_keycode(key_code_str):
    """Maps the standardized JavaScript key code to the local OS virtual keycode"""
    if IS_MAC:
        return MAC_KEY_CODES.get(key_code_str, 49)  # Fallback to Mac Space
    elif IS_WINDOWS:
        return WIN_KEY_CODES.get(key_code_str, 0x20)  # Fallback to Windows Space (0x20)
    return 0

# Try loading macOS CoreGraphics APIs
cg_loaded = False
if IS_MAC:
    try:
        cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        
        cg.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p
        cg.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_ushort, ctypes.c_bool]
        cg.CGEventPost.restype = None
        cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
        cf.CFRelease.restype = None
        cf.CFRelease.argtypes = [ctypes.c_void_p]
        
        cg_loaded = True
    except Exception as e:
        print(f"Warning: Could not load macOS CoreGraphics APIs ({e}).")

# Setup Windows SendInput structures and functions
user32 = None
if IS_WINDOWS:
    try:
        user32 = ctypes.windll.user32
        
        # Windows Ctypes Structures
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
    if IS_MAC:
        if not cg_loaded:
            print(f"[Mac Simulated Keystroke] OS Code: {keycode}")
            return
        try:
            event_down = cg.CGEventCreateKeyboardEvent(None, keycode, True)
            event_up = cg.CGEventCreateKeyboardEvent(None, keycode, False)
            if event_down and event_up:
                cg.CGEventPost(0, event_down)
                time.sleep(0.01)
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
            
            # Key Down struct
            ki_down = KEYBDINPUT(wVk=keycode, wScan=0, dwFlags=0, time=0, dwExtraInfo=extra)
            ii_down = INPUT_UNION(ki=ki_down)
            input_down = INPUT(type=1, ii=ii_down)  # type 1 is INPUT_KEYBOARD
            
            # Key Up struct (dwFlags = 0x0002 is KEYEVENTF_KEYUP)
            ki_up = KEYBDINPUT(wVk=keycode, wScan=0, dwFlags=0x0002, time=0, dwExtraInfo=extra)
            ii_up = INPUT_UNION(ki=ki_up)
            input_up = INPUT(type=1, ii=ii_up)
            
            # Post events using native user32 SendInput
            user32.SendInput(1, ctypes.byref(input_down), ctypes.sizeof(input_down))
            time.sleep(0.01)
            user32.SendInput(1, ctypes.byref(input_up), ctypes.sizeof(input_up))
        except Exception as e:
            print(f"Error simulating Windows keycode {keycode}: {e}")
            
    else:
        print(f"[Simulated Keystroke] Unsupported OS. Keycode: {keycode}")

def presser_thread_func():
    """Background worker thread executing keypress loop at specified intervals"""
    global state
    last_macro_time = time.time()
    
    while True:
        with state_lock:
            running = state["running"]
            keycode = state["keycode"]
            interval = state["interval_ms"] / 1000.0
            macro_enabled = state["macro_enabled"]
            
        if running:
            # Check if 30 seconds have passed since last macro run
            current_time = time.time()
            if macro_enabled and (current_time - last_macro_time >= 30.0):
                print("[Macro] Idle delay: waiting 2 seconds before movement...")
                time.sleep(2.0)  # Pause all keypresses for 2 seconds
                
                print("[Macro] Executing 30s movement routine: Right x2, Left x2...")
                # Resolve keycodes depending on OS (mac vs win)
                left_kc = 123 if IS_MAC else 0x25
                right_kc = 124 if IS_MAC else 0x27
                
                # Right Arrow twice
                send_keypress(right_kc)
                time.sleep(0.18)
                send_keypress(right_kc)
                time.sleep(0.18)
                
                # Left Arrow twice
                send_keypress(left_kc)
                time.sleep(0.18)
                send_keypress(left_kc)
                time.sleep(0.18)
                
                last_macro_time = time.time()
            
            send_keypress(keycode)
            with state_lock:
                state["count"] += 1
            
            # Smart interruptible sleep
            sleep_event.clear()
            sleep_event.wait(timeout=interval)
        else:
            # Reset timer when stopped to delay the first macro trigger by 30 seconds after start
            last_macro_time = time.time()
            # Short sleep when idle to prevent high CPU utilization
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
                    # Resolve OS specific keycode on load
                    state["keycode"] = resolve_keycode(state["key_code_str"])
            print(f"[Config] Loaded: Key={state['key_name']} (OS Code {state['keycode']}), Interval={state['interval_ms']}ms, Macro={state['macro_enabled']}")
        except Exception as e:
            print(f"[Config] Error loading configuration: {e}")

def save_config():
    """Save current configuration to config.json"""
    with state_lock:
        data = {
            "key_code_str": state["key_code_str"],
            "key_name": state["key_name"],
            "interval_ms": state["interval_ms"],
            "macro_enabled": state["macro_enabled"]
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
        else:
            # Server static files
            clean_path = self.path.split("?")[0].lstrip("/")
            if not clean_path or clean_path == "index.html":
                filepath = os.path.join("web", "index.html")
            else:
                filepath = os.path.join("web", clean_path)
                
            # Prevent directory traversal
            abs_filepath = os.path.abspath(filepath)
            abs_web_dir = os.path.abspath("web")
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
                        # Dynamically resolve OS keycode on update
                        state["keycode"] = resolve_keycode(state["key_code_str"])
                    if "key_name" in data:
                        state["key_name"] = str(data["key_name"])
                    if "interval_ms" in data:
                        state["interval_ms"] = max(10, int(data["interval_ms"]))
                    if "macro_enabled" in data:
                        state["macro_enabled"] = bool(data["macro_enabled"])
                save_config()
                sleep_event.set()  # Apply changes immediately
                print(f"[Control] Config updated: Key={state['key_name']} (OS Code {state['keycode']}), Interval={state['interval_ms']}ms, Macro={state['macro_enabled']}")
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
    # Ensure current working directory is the script's folder so 'web/' paths resolve correctly
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Load config file settings
    load_config()
    
    # Initialize background keypress loop
    threading.Thread(target=presser_thread_func, daemon=True).start()
    
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
