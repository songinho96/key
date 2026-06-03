// macOS Virtual Keycodes Map
// Maps JS KeyboardEvent.code strings to native macOS CGKeyCode values
const MACOS_KEY_CODES = {
    // Alphabet
    "KeyA": 0, "KeyS": 1, "KeyD": 2, "KeyF": 3, "KeyH": 4, "KeyG": 5, "KeyZ": 6, "KeyX": 7,
    "KeyC": 8, "KeyV": 9, "KeyB": 11, "KeyQ": 12, "KeyW": 13, "KeyE": 14, "KeyR": 15,
    "KeyY": 16, "KeyT": 17, "KeyO": 31, "KeyU": 32, "KeyI": 34, "KeyP": 35, "KeyL": 37,
    "KeyJ": 38, "KeyK": 40, "KeyN": 45, "KeyM": 46,
    
    // Numbers
    "Digit1": 18, "Digit2": 19, "Digit3": 20, "Digit4": 21, "Digit5": 23, "Digit6": 22,
    "Digit7": 26, "Digit8": 28, "Digit9": 25, "Digit0": 29,
    
    // Standard Specials
    "Space": 49, "Enter": 36, "NumpadEnter": 76, "Tab": 48, "Escape": 53,
    "Backspace": 51, "Delete": 117,
    
    // Navigation
    "ArrowLeft": 123, "ArrowRight": 124, "ArrowDown": 125, "ArrowUp": 126,
    "PageUp": 116, "PageDown": 121, "Home": 115, "End": 119,
    
    // Function keys
    "F1": 122, "F2": 120, "F3": 99, "F4": 118, "F5": 96, "F6": 97, "F7": 98,
    "F8": 100, "F9": 101, "F10": 109, "F11": 103, "F12": 111,
    
    // Punctuation & Symbols
    "Minus": 27, "Equal": 24, "BracketLeft": 33, "BracketRight": 30,
    "Semicolon": 41, "Quote": 39, "Backslash": 42, "Comma": 43, "Period": 47,
    "Slash": 44, "Backquote": 50
};

// UI Elements
const keyCapDisplay = document.getElementById("keyCapDisplay");
const keyCodeDisplay = document.getElementById("keyCodeDisplay");
const btnRecordKey = document.getElementById("btnRecordKey");
const intervalSlider = document.getElementById("intervalSlider");
const intervalInput = document.getElementById("intervalInput");
const intervalSeconds = document.getElementById("intervalSeconds");
const statusBadge = document.getElementById("statusBadge");
const statusText = document.getElementById("statusText");
const btnToggleRun = document.getElementById("btnToggleRun");
const triggerIcon = document.getElementById("triggerIcon");
const triggerBtnText = document.getElementById("triggerBtnText");
const recordingOverlay = document.getElementById("recordingOverlay");
const btnCancelRecord = document.getElementById("btnCancelRecord");
const macroToggle = document.getElementById("macroToggle");
const macroBadge = document.getElementById("macroBadge");
const humanizerToggle = document.getElementById("humanizerToggle");
const humanizerBadge = document.getElementById("humanizerBadge");

// Stat Elements
const statCount = document.getElementById("statCount");
const statStatus = document.getElementById("statStatus");
const statKey = document.getElementById("statKey");
const statInterval = document.getElementById("statInterval");

// Preset Buttons
const presetBtns = document.querySelectorAll(".preset-btn");

// App State
let appState = {
    running: false,
    key_code_str: "Space",
    keycode: 49,
    key_name: "Space",
    interval_ms: 1000,
    count: 0,
    macro_enabled: false,
    humanizer_enabled: true
};
let isRecording = false;
let pollIntervalId = null;
let isUpdatingConfig = false;

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    // Initial fetch of state
    fetchState().then(() => {
        updateUI();
        startPolling();
    });
    
    // Register event listeners
    btnRecordKey.addEventListener("click", startKeyRecording);
    btnCancelRecord.addEventListener("click", stopKeyRecording);
    btnToggleRun.addEventListener("click", toggleExecution);
    
    // Slider & Input binding
    intervalSlider.addEventListener("input", handleSliderInput);
    intervalSlider.addEventListener("change", saveConfigToServer);
    intervalInput.addEventListener("change", handleNumericInput);
    
    // Macro toggle binding
    macroToggle.addEventListener("change", handleMacroToggleChange);
    
    // Humanizer toggle binding
    humanizerToggle.addEventListener("change", handleHumanizerToggleChange);
    
    // Presets
    presetBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const ms = parseInt(btn.getAttribute("data-ms"), 10);
            intervalInput.value = ms;
            intervalSlider.value = Math.min(ms, 5000);
            appState.interval_ms = ms;
            updateIntervalPreview();
            saveConfigToServer();
        });
    });
    
    // Listen for global keypresses during recording
    window.addEventListener("keydown", handleGlobalKeyDown, true);
});

// Fetch current state from the local server
async function fetchState() {
    try {
        const response = await fetch("/api/status");
        if (response.ok) {
            appState = await response.json();
        }
    } catch (error) {
        console.error("Error connecting to AutoKey server:", error);
        statStatus.textContent = "OFFLINE";
        statStatus.style.color = "var(--color-red)";
    }
}

// Start polling backend for live stats/status updates
function startPolling() {
    if (pollIntervalId) clearInterval(pollIntervalId);
    pollIntervalId = setInterval(async () => {
        // Only update stats during polling (so we don't disrupt user inputs)
        try {
            const response = await fetch("/api/status");
            if (response.ok) {
                const newState = await response.json();
                
                // Live count update (animate count if changed)
                if (newState.count !== appState.count) {
                    animateCount(appState.count, newState.count);
                }
                
                appState.count = newState.count;
                appState.running = newState.running;
                
                // If we aren't recording or changing configurations, keep settings in sync
                if (!isRecording && !isUpdatingConfig) {
                    appState.key_code_str = newState.key_code_str;
                    appState.keycode = newState.keycode;
                    appState.key_name = newState.key_name;
                    appState.interval_ms = newState.interval_ms;
                    appState.macro_enabled = newState.macro_enabled;
                    appState.humanizer_enabled = newState.humanizer_enabled;
                    updateMacroBadge();
                    updateHumanizerBadge();
                }
                
                updateUIStateOnly();
            }
        } catch (e) {
            console.warn("Polling failed. Server offline?");
        }
    }, 500);
}

// Update the full UI controls (run on init or configuration change)
function updateUI() {
    // Update key details
    keyCapDisplay.textContent = appState.key_name;
    keyCodeDisplay.textContent = `KeyCode ${appState.keycode}`;
    statKey.textContent = appState.key_name;
    
    // Update interval
    intervalInput.value = appState.interval_ms;
    intervalSlider.value = Math.min(appState.interval_ms, 5000);
    statInterval.textContent = `${(appState.interval_ms / 1000).toFixed(2)}s`;
    updateIntervalPreview();
    
    // Update macro toggle state
    updateMacroBadge();
    updateHumanizerBadge();
    
    updateUIStateOnly();
}

function handleMacroToggleChange(e) {
    appState.macro_enabled = e.target.checked;
    updateMacroBadge();
    saveConfigToServer();
}

function handleHumanizerToggleChange(e) {
    appState.humanizer_enabled = e.target.checked;
    updateHumanizerBadge();
    saveConfigToServer();
}

function updateHumanizerBadge() {
    if (appState.humanizer_enabled) {
        humanizerBadge.textContent = "활성";
        humanizerBadge.className = "humanizer-badge active";
        humanizerToggle.checked = true;
    } else {
        humanizerBadge.textContent = "비활성";
        humanizerBadge.className = "humanizer-badge";
        humanizerToggle.checked = false;
    }
}

function updateMacroBadge() {
    if (appState.macro_enabled) {
        macroBadge.textContent = "활성";
        macroBadge.className = "macro-badge active";
        macroToggle.checked = true;
    } else {
        macroBadge.textContent = "비활성";
        macroBadge.className = "macro-badge";
        macroToggle.checked = false;
    }
}

// Update running/stopping UI representations (run during polling)
function updateUIStateOnly() {
    statCount.textContent = appState.count.toLocaleString();
    
    if (appState.running) {
        // Status indicator
        statusBadge.className = "status-indicator-badge running";
        statusText.textContent = "작동 중";
        statStatus.textContent = "RUNNING";
        statStatus.style.color = "var(--color-green)";
        
        // Large action button
        btnToggleRun.className = "btn-trigger running";
        triggerBtnText.textContent = "작동 중지";
        
        // Change icon to Pause
        triggerIcon.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/></svg>`;
    } else {
        // Status indicator
        statusBadge.className = "status-indicator-badge";
        statusText.textContent = "정지됨";
        statStatus.textContent = "STOPPED";
        statStatus.style.color = "var(--text-secondary)";
        
        // Large action button
        btnToggleRun.className = "btn-trigger";
        triggerBtnText.textContent = "작동 시작";
        
        // Change icon to Play
        triggerIcon.innerHTML = `<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="6 3 20 12 6 21 6 3"/></svg>`;
    }
}

// Helper to format/preview interval speeds
function updateIntervalPreview() {
    const ms = appState.interval_ms;
    if (ms <= 10) {
        intervalSeconds.textContent = "최대 속도 (무제한)";
    } else {
        const rate = (1000 / ms).toFixed(1);
        intervalSeconds.textContent = `초당 ~${rate}회 입력`;
    }
}

// Smoothly animate the count value changes
function animateCount(start, end) {
    if (start === end) return;
    const duration = 400; // ms
    const startTime = performance.now();
    
    function update(now) {
        const elapsed = now - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Ease out quadratic
        const ease = progress * (2 - progress);
        const current = Math.floor(start + (end - start) * ease);
        statCount.textContent = current.toLocaleString();
        
        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            statCount.textContent = end.toLocaleString();
        }
    }
    requestAnimationFrame(update);
}

// Handle slider inputs
function handleSliderInput(e) {
    const ms = parseInt(e.target.value, 10);
    intervalInput.value = ms;
    appState.interval_ms = ms;
    updateIntervalPreview();
}

// Handle text input changes
function handleNumericInput(e) {
    let ms = parseInt(e.target.value, 10);
    if (isNaN(ms) || ms < 10) ms = 10;
    if (ms > 60000) ms = 60000;
    
    e.target.value = ms;
    intervalSlider.value = Math.min(ms, 5000);
    appState.interval_ms = ms;
    updateIntervalPreview();
    saveConfigToServer();
}

// Send current configuration to backend API
async function saveConfigToServer() {
    isUpdatingConfig = true;
    try {
        const response = await fetch("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                key_code_str: appState.key_code_str,
                key_name: appState.key_name,
                interval_ms: appState.interval_ms,
                macro_enabled: appState.macro_enabled,
                humanizer_enabled: appState.humanizer_enabled
            })
        });
        if (response.ok) {
            statInterval.textContent = `${(appState.interval_ms / 1000).toFixed(2)}s`;
        }
    } catch (e) {
        console.error("Failed to save config:", e);
    } finally {
        isUpdatingConfig = false;
    }
}

// Start recording keyboard input
function startKeyRecording() {
    isRecording = true;
    recordingOverlay.classList.add("active");
}

// Cancel or stop recording keyboard input
function stopKeyRecording() {
    isRecording = false;
    recordingOverlay.classList.remove("active");
}

// Intercept global keydown when keybinder modal is active
async function handleGlobalKeyDown(event) {
    if (!isRecording) return;
    
    // Stop recording overlay if ESC is pressed
    if (event.key === "Escape" || event.code === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        stopKeyRecording();
        return;
    }
    
    event.preventDefault();
    event.stopPropagation();
    
    const keyDetails = mapJsEventToOsKey(event);
    if (keyDetails) {
        appState.key_code_str = keyDetails.code_str;
        appState.key_name = keyDetails.name;
        
        // Update display immediately
        updateUI();
        
        // Sync configuration changes with backend
        await saveConfigToServer();
        stopKeyRecording();
    } else {
        // Flash a notification/warning that key is not supported on macOS event taps
        console.warn(`Unmappable key code: ${event.code} (${event.key})`);
    }
}

// Maps JavaScript KeyboardEvent codes to matching macOS Virtual Keycodes
function mapJsEventToOsKey(event) {
    const code = event.code;
    const key = event.key;
    
    let isSupported = MACOS_KEY_CODES[code] !== undefined;
    
    // Dynamic backups if direct key codes fail
    if (!isSupported) {
        if (key === " " || key === "Enter" || key === "Escape" || key === "Tab") {
            isSupported = true;
        } else {
            return null; 
        }
    }
    
    // Generate readable names
    let displayName = key;
    if (code.startsWith("Key")) {
        displayName = code.substring(3); // "KeyA" -> "A"
    } else if (code.startsWith("Digit")) {
        displayName = code.substring(5); // "Digit1" -> "1"
    } else if (code === "Space" || key === " ") {
        displayName = "Space";
    } else if (code === "Enter") {
        displayName = "Enter";
    } else if (code === "ArrowLeft") {
        displayName = "Left Arrow";
    } else if (code === "ArrowRight") {
        displayName = "Right Arrow";
    } else if (code === "ArrowUp") {
        displayName = "Up Arrow";
    } else if (code === "ArrowDown") {
        displayName = "Down Arrow";
    } else if (code.startsWith("F") && code.length <= 4) {
        displayName = code; // F1, F2... F12
    }
    
    return {
        code_str: code,
        name: displayName
    };
}

// Toggle execution (Start / Stop) on button click
async function toggleExecution() {
    const endpoint = appState.running ? "/api/stop" : "/api/start";
    try {
        const response = await fetch(endpoint, { method: "POST" });
        if (response.ok) {
            appState.running = !appState.running;
            updateUIStateOnly();
        }
    } catch (e) {
        console.error("API request failed:", e);
    }
}
