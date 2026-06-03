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

// Pixel Trigger UI Elements
const pixelToggle = document.getElementById("pixelToggle");
const pixelBadge = document.getElementById("pixelBadge");
const pixelConfigContainer = document.getElementById("pixelConfigContainer");
const pixelXInput = document.getElementById("pixelXInput");
const pixelYInput = document.getElementById("pixelYInput");
const btnPickPixel = document.getElementById("btnPickPixel");
const pixelColorInput = document.getElementById("pixelColorInput");
const pixelColorPreview = document.getElementById("pixelColorPreview");
const pixelMatchType = document.getElementById("pixelMatchType");
const pixelKeyCapDisplay = document.getElementById("pixelKeyCapDisplay");
const btnRecordPixelKey = document.getElementById("btnRecordPixelKey");
const pixelCooldownInput = document.getElementById("pixelCooldownInput");
const pickerOverlay = document.getElementById("pickerOverlay");
const pickerCountdown = document.getElementById("pickerCountdown");

// Move & Jump UI Elements
const jumpToggle = document.getElementById("jumpToggle");
const jumpBadge = document.getElementById("jumpBadge");
const jumpConfigContainer = document.getElementById("jumpConfigContainer");
const jumpXInput = document.getElementById("jumpXInput");
const jumpYInput = document.getElementById("jumpYInput");
const btnCaptureMinimap = document.getElementById("btnCaptureMinimap");
const minimapViewer = document.getElementById("minimapViewer");
const minimapImage = document.getElementById("minimapImage");
const minimapPlaceholder = document.getElementById("minimapPlaceholder");
const minimapMarker = document.getElementById("minimapMarker");
const minimapOffsetX = document.getElementById("minimapOffsetX");
const minimapOffsetY = document.getElementById("minimapOffsetY");
const btnPickMinimapOffset = document.getElementById("btnPickMinimapOffset");
const btnPickJumpPosAbsolute = document.getElementById("btnPickJumpPosAbsolute");
const jumpKeyCapDisplay = document.getElementById("jumpKeyCapDisplay");
const btnRecordJumpKey = document.getElementById("btnRecordJumpKey");
const jumpCooldownInput = document.getElementById("jumpCooldownInput");

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
    humanizer_enabled: true,
    
    // Pixel Trigger config fields
    pixel_macro_enabled: false,
    pixel_x: 100,
    pixel_y: 100,
    pixel_color: "#FFCC00",
    pixel_match_type: "equal",
    pixel_action_code_str: "Space",
    pixel_action_keycode: 49,
    pixel_action_name: "Space",
    pixel_cooldown_s: 1.5,
    
    // Move & Jump config fields
    jump_macro_enabled: false,
    jump_x: 100,
    jump_y: 100,
    jump_cooldown_s: 20.0,
    jump_action_code_str: "KeyC",
    jump_action_keycode: 8,
    jump_action_name: "C",
    minimap_offset_x: 0,
    minimap_offset_y: 0
};
let isRecording = false;
let recordingTarget = "main"; // "main", "pixel", or "jump"
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
    btnRecordKey.addEventListener("click", () => startKeyRecording("main"));
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

    // Pixel Trigger bindings
    pixelToggle.addEventListener("change", handlePixelToggleChange);
    pixelXInput.addEventListener("change", handlePixelCoordsChange);
    pixelYInput.addEventListener("change", handlePixelCoordsChange);
    btnPickPixel.addEventListener("click", startPixelPicking);
    pixelColorInput.addEventListener("input", handlePixelColorChange);
    pixelColorInput.addEventListener("change", handlePixelColorChange);
    pixelMatchType.addEventListener("change", handlePixelMatchTypeChange);
    btnRecordPixelKey.addEventListener("click", () => startKeyRecording("pixel"));
    pixelCooldownInput.addEventListener("change", handlePixelCooldownChange);

    // Move & Jump bindings
    jumpToggle.addEventListener("change", handleJumpToggleChange);
    jumpXInput.addEventListener("change", handleJumpXChange);
    jumpYInput.addEventListener("change", handleJumpYChange);
    btnCaptureMinimap.addEventListener("click", captureMinimap);
    minimapViewer.addEventListener("click", handleMinimapClick);
    btnRecordJumpKey.addEventListener("click", () => startKeyRecording("jump"));
    jumpCooldownInput.addEventListener("change", handleJumpCooldownChange);
    minimapOffsetX.addEventListener("change", handleMinimapOffsetChange);
    minimapOffsetY.addEventListener("change", handleMinimapOffsetChange);
    btnPickMinimapOffset.addEventListener("click", startMinimapOffsetPicking);
    btnPickJumpPosAbsolute.addEventListener("click", startAbsoluteJumpPicking);
    
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
                    
                    appState.pixel_macro_enabled = newState.pixel_macro_enabled;
                    appState.pixel_x = newState.pixel_x;
                    appState.pixel_y = newState.pixel_y;
                    appState.pixel_color = newState.pixel_color;
                    appState.pixel_match_type = newState.pixel_match_type;
                    appState.pixel_action_code_str = newState.pixel_action_code_str;
                    appState.pixel_action_keycode = newState.pixel_action_keycode;
                    appState.pixel_action_name = newState.pixel_action_name;
                    appState.pixel_cooldown_s = newState.pixel_cooldown_s;
                    
                    appState.jump_macro_enabled = newState.jump_macro_enabled;
                    appState.jump_x = newState.jump_x;
                    appState.jump_y = newState.jump_y;
                    appState.jump_cooldown_s = newState.jump_cooldown_s;
                    appState.jump_action_code_str = newState.jump_action_code_str;
                    appState.jump_action_keycode = newState.jump_action_keycode;
                    appState.jump_action_name = newState.jump_action_name;
                    appState.minimap_offset_x = newState.minimap_offset_x;
                    appState.minimap_offset_y = newState.minimap_offset_y;
                    
                    updateMacroBadge();
                    updateHumanizerBadge();
                    updatePixelBadge();
                    updateJumpBadge();
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
    
    // Update pixel macro inputs & elements
    pixelToggle.checked = appState.pixel_macro_enabled;
    updatePixelBadge();
    pixelXInput.value = appState.pixel_x;
    pixelYInput.value = appState.pixel_y;
    pixelColorInput.value = appState.pixel_color;
    pixelColorPreview.style.backgroundColor = appState.pixel_color;
    pixelMatchType.value = appState.pixel_match_type;
    pixelKeyCapDisplay.textContent = appState.pixel_action_name;
    pixelCooldownInput.value = appState.pixel_cooldown_s;
    
    // Update Move & Jump inputs & elements
    jumpToggle.checked = appState.jump_macro_enabled;
    updateJumpBadge();
    jumpXInput.value = appState.jump_x;
    jumpYInput.value = appState.jump_y;
    jumpKeyCapDisplay.textContent = appState.jump_action_name;
    jumpCooldownInput.value = appState.jump_cooldown_s;
    minimapOffsetX.value = appState.minimap_offset_x;
    minimapOffsetY.value = appState.minimap_offset_y;
    updateMinimapMarkerPosition();
    
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

function updatePixelBadge() {
    if (appState.pixel_macro_enabled) {
        pixelBadge.textContent = "활성";
        pixelBadge.className = "pixel-badge active";
        pixelConfigContainer.style.display = "flex";
    } else {
        pixelBadge.textContent = "비활성";
        pixelBadge.className = "pixel-badge";
        pixelConfigContainer.style.display = "none";
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
                humanizer_enabled: appState.humanizer_enabled,
                
                // Pixel fields
                pixel_macro_enabled: appState.pixel_macro_enabled,
                pixel_x: appState.pixel_x,
                pixel_y: appState.pixel_y,
                pixel_color: appState.pixel_color,
                pixel_match_type: appState.pixel_match_type,
                pixel_action_code_str: appState.pixel_action_code_str,
                pixel_action_name: appState.pixel_action_name,
                pixel_cooldown_s: appState.pixel_cooldown_s,
                
                // Jump fields
                jump_macro_enabled: appState.jump_macro_enabled,
                jump_x: appState.jump_x,
                jump_y: appState.jump_y,
                jump_cooldown_s: appState.jump_cooldown_s,
                jump_action_code_str: appState.jump_action_code_str,
                jump_action_name: appState.jump_action_name,
                minimap_offset_x: appState.minimap_offset_x,
                minimap_offset_y: appState.minimap_offset_y
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
function startKeyRecording(target = "main") {
    recordingTarget = target;
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
        if (recordingTarget === "pixel") {
            appState.pixel_action_code_str = keyDetails.code_str;
            appState.pixel_action_name = keyDetails.name;
        } else if (recordingTarget === "jump") {
            appState.jump_action_code_str = keyDetails.code_str;
            appState.jump_action_name = keyDetails.name;
        } else {
            appState.key_code_str = keyDetails.code_str;
            appState.key_name = keyDetails.name;
        }
        
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

// Pixel Trigger Event Handlers
function handlePixelToggleChange(e) {
    appState.pixel_macro_enabled = e.target.checked;
    updatePixelBadge();
    saveConfigToServer();
}

function handlePixelCoordsChange() {
    let x = parseInt(pixelXInput.value, 10);
    let y = parseInt(pixelYInput.value, 10);
    if (isNaN(x) || x < 0) x = 0;
    if (isNaN(y) || y < 0) y = 0;
    pixelXInput.value = x;
    pixelYInput.value = y;
    appState.pixel_x = x;
    appState.pixel_y = y;
    saveConfigToServer();
}

function handlePixelColorChange(e) {
    let color = e.target.value.trim();
    if (/^#[0-9A-F]{6}$/i.test(color)) {
        pixelColorPreview.style.backgroundColor = color;
        appState.pixel_color = color;
        saveConfigToServer();
    }
}

function handlePixelMatchTypeChange(e) {
    appState.pixel_match_type = e.target.value;
    saveConfigToServer();
}

function handlePixelCooldownChange(e) {
    let val = parseFloat(e.target.value);
    if (isNaN(val) || val < 0.1) val = 0.1;
    e.target.value = val;
    appState.pixel_cooldown_s = val;
    saveConfigToServer();
}

// Pixel picking countdown logic
function startPixelPicking() {
    pickerOverlay.classList.add("active");
    let timeLeft = 3;
    pickerCountdown.textContent = timeLeft;
    
    const interval = setInterval(() => {
        timeLeft--;
        if (timeLeft > 0) {
            pickerCountdown.textContent = timeLeft;
        } else {
            clearInterval(interval);
            // Trigger pick API
            fetch("/api/pick")
                .then(res => {
                    if (!res.ok) throw new Error("Pick request failed");
                    return res.json();
                })
                .then(data => {
                    pixelXInput.value = data.x;
                    pixelYInput.value = data.y;
                    pixelColorInput.value = data.color;
                    pixelColorPreview.style.backgroundColor = data.color;
                    
                    appState.pixel_x = data.x;
                    appState.pixel_y = data.y;
                    appState.pixel_color = data.color;
                    
                    saveConfigToServer();
                })
                .catch(err => {
                    console.error("Error picking pixel color:", err);
                })
                .finally(() => {
                    pickerOverlay.classList.remove("active");
                });
        }
    }, 1000);
}

// Move & Jump Event Handlers
function handleJumpToggleChange(e) {
    appState.jump_macro_enabled = e.target.checked;
    updateJumpBadge();
    saveConfigToServer();
}

function handleJumpXChange(e) {
    let val = parseInt(e.target.value);
    if (isNaN(val) || val < 0) val = 0;
    if (val > 400) val = 400;
    e.target.value = val;
    appState.jump_x = val;
    updateMinimapMarkerPosition();
    saveConfigToServer();
}

function handleJumpYChange(e) {
    let val = parseInt(e.target.value);
    if (isNaN(val) || val < 0) val = 0;
    if (val > 400) val = 400;
    e.target.value = val;
    appState.jump_y = val;
    updateMinimapMarkerPosition();
    saveConfigToServer();
}

function handleJumpCooldownChange(e) {
    let val = parseFloat(e.target.value);
    if (isNaN(val) || val < 0.5) val = 0.5;
    e.target.value = val;
    appState.jump_cooldown_s = val;
    saveConfigToServer();
}

function captureMinimap() {
    btnCaptureMinimap.textContent = "📸 로딩 중...";
    btnCaptureMinimap.disabled = true;
    
    // Append timestamp to bust browser image cache
    minimapImage.src = "/api/capture_minimap?t=" + Date.now();
    
    minimapImage.onload = function() {
        minimapImage.style.display = "block";
        minimapPlaceholder.style.display = "none";
        minimapMarker.style.display = "block";
        btnCaptureMinimap.textContent = "📸 현재 게임 미니맵 화면 가져오기";
        btnCaptureMinimap.disabled = false;
        updateMinimapMarkerPosition();
    };
    
    minimapImage.onerror = function() {
        alert("게임 미니맵 화면을 가져오는 데 실패했습니다. 게임이 실행 중이며 활성화되어 있는지 확인해 주세요.");
        btnCaptureMinimap.textContent = "📸 현재 게임 미니맵 화면 가져오기";
        btnCaptureMinimap.disabled = false;
    };
}

function handleMinimapClick(e) {
    // Only capture click if the image has been loaded
    if (minimapImage.style.display === "none") return;
    
    const rect = minimapViewer.getBoundingClientRect();
    const x = Math.round(e.clientX - rect.left);
    const y = Math.round(e.clientY - rect.top);
    
    // Bounds check
    const clampedX = Math.max(0, Math.min(400, x));
    const clampedY = Math.max(0, Math.min(400, y));
    
    appState.jump_x = clampedX;
    appState.jump_y = clampedY;
    
    jumpXInput.value = clampedX;
    jumpYInput.value = clampedY;
    
    updateMinimapMarkerPosition();
    saveConfigToServer();
}

function updateMinimapMarkerPosition() {
    if (appState.jump_x !== undefined && appState.jump_y !== undefined) {
        minimapMarker.style.left = appState.jump_x + "px";
        minimapMarker.style.top = appState.jump_y + "px";
        
        // Show marker if there's coordinate config
        minimapMarker.style.display = "block";
    }
}

function updateJumpBadge() {
    if (appState.jump_macro_enabled) {
        jumpBadge.textContent = "활성";
        jumpBadge.className = "jump-badge active";
        jumpConfigContainer.style.display = "flex";
    } else {
        jumpBadge.textContent = "비활성";
        jumpBadge.className = "jump-badge";
        jumpConfigContainer.style.display = "none";
    }
}

function handleMinimapOffsetChange(e) {
    const targetId = e.target.id;
    let val = parseInt(e.target.value);
    if (isNaN(val) || val < 0) val = 0;
    e.target.value = val;
    
    if (targetId === "minimapOffsetX") {
        appState.minimap_offset_x = val;
    } else {
        appState.minimap_offset_y = val;
    }
    saveConfigToServer();
}

function startMinimapOffsetPicking() {
    pickerOverlay.classList.add("active");
    let timeLeft = 3;
    pickerCountdown.textContent = timeLeft;
    
    const interval = setInterval(() => {
        timeLeft--;
        if (timeLeft > 0) {
            pickerCountdown.textContent = timeLeft;
        } else {
            clearInterval(interval);
            // Trigger pick API
            fetch("/api/pick")
                .then(res => {
                    if (!res.ok) throw new Error("Pick request failed");
                    return res.json();
                })
                .then(data => {
                    minimapOffsetX.value = data.x;
                    minimapOffsetY.value = data.y;
                    
                    appState.minimap_offset_x = data.x;
                    appState.minimap_offset_y = data.y;
                    
                    saveConfigToServer();
                })
                .catch(err => {
                    console.error("Error picking minimap offset:", err);
                })
                .finally(() => {
                    pickerOverlay.classList.remove("active");
                });
        }
    }, 1000);
}

function startAbsoluteJumpPicking() {
    pickerOverlay.classList.add("active");
    let timeLeft = 3;
    pickerCountdown.textContent = timeLeft;
    
    const interval = setInterval(() => {
        timeLeft--;
        if (timeLeft > 0) {
            pickerCountdown.textContent = timeLeft;
        } else {
            clearInterval(interval);
            // Trigger pick API
            fetch("/api/pick")
                .then(res => {
                    if (!res.ok) throw new Error("Pick request failed");
                    return res.json();
                })
                .then(data => {
                    // Convert screen absolute coordinate to minimap relative coordinate
                    const relativeX = data.x - appState.minimap_offset_x;
                    const relativeY = data.y - appState.minimap_offset_y;
                    
                    // Clamp inside 0~400 range
                    const clampedX = Math.max(0, Math.min(400, relativeX));
                    const clampedY = Math.max(0, Math.min(400, relativeY));
                    
                    jumpXInput.value = clampedX;
                    jumpYInput.value = clampedY;
                    
                    appState.jump_x = clampedX;
                    appState.jump_y = clampedY;
                    
                    updateMinimapMarkerPosition();
                    saveConfigToServer();
                })
                .catch(err => {
                    console.error("Error picking absolute jump position:", err);
                })
                .finally(() => {
                    pickerOverlay.classList.remove("active");
                });
        }
    }, 1000);
}
