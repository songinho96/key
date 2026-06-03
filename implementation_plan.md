# Mouse Macro Feature Implementation Plan

## Goal
Create a configurable macro that, every N minutes, moves the mouse cursor to a first coordinate, performs a double‑click, then moves to a second coordinate and performs a single click. This will be used to automate the "묘묘상인" item‑selling process.

## User Review Required
> [!IMPORTANT] The UI will be extended with a new **Mouse Macro** panel. Confirm the layout and default values before implementation.

## Open Questions
- Should the interval be in seconds or minutes? (default: 180 s)
- Do you need the option to enable/disable the macro independently of other macros?
- Should the macro run when the main macro is **running** (`state["running"]`) or always?
- Do you want the ability to edit the coordinates via the UI (click‑to‑set) like the existing minimap picker?

## Proposed Changes
---
### Backend (`app.py`)
- Add new state fields:
  ```python
  "mouse_macro_enabled": False,
  "mouse_x1": 100, "mouse_y1": 200,
  "mouse_x2": 300, "mouse_y2": 400,
  "mouse_interval_s": 180.0,
  "mouse_click_type": "double",  # "double" or "single"
  ```
- Extend `load_config()` and `save_config()` to persist these fields.
- Add a new background thread `mouse_macro_thread_func()` that:
  1. Checks `state["running"]` and `state["mouse_macro_enabled"]`.
  2. When the elapsed time exceeds `mouse_interval_s`, performs:
     - `warp_mouse(state["mouse_x1"], state["mouse_y1"])`
     - `click_mouse(button=0, double=True)`
     - `warp_mouse(state["mouse_x2"], state["mouse_y2"])`
     - `click_mouse(button=0, double=False)`
  3. Updates the last‑trigger timestamp stored in a module‑level dict `_mouse_last_trigger`.
- Implement helper functions `warp_mouse(x, y)` and `click_mouse(button=0, double=False)` using the already‑loaded CoreGraphics APIs (`CGWarpMouseCursorPosition`, `CGEventCreateMouseEvent`, `CGEventPost`).
- Update `/api/status` response to include the new mouse fields.
- Update `/api/config` POST handling to accept the new fields.
- In the polling loop of `index.js`, sync the new fields and add UI badge updates.

### Frontend (`web/`)
- **HTML**: Add a new **Mouse Macro** section in the left panel (similar to Scheduled Macro UI) with inputs:
  - Enable toggle
  - Interval (seconds)
  - Coordinate 1 (X/Y) with a "Pick" button to capture current cursor position.
  - Coordinate 2 (X/Y) with a "Pick" button.
  - Click type selector (double / single) for the first position.
- **CSS**: Style the section using existing `.setting-group` patterns and create `.mouse-badge` styles.
- **JS**:
  - Declare DOM elements (`mouseToggle`, `mouseX1Input`, etc.).
  - Bind change events to update `appState` and call `saveConfigToServer()`.
  - Implement `startMousePicking(target)` that shows a full‑screen overlay and records the cursor position on click, similar to existing minimap picker.
  - Add `updateMouseBadge()` to reflect enabled/disabled status.
  - Extend `renderUI` to populate the new fields.
  - Ensure the periodic polling adds `appState.mouse_*` fields and calls `updateMouseBadge()`.

### UI Flow
1. User enables **Mouse Macro** toggle.
2. Sets interval (e.g., 180 s).
3. Clicks **Pick** for the first coordinate → cursor overlay appears → click on game screen → values stored.
4. Optionally selects **Double Click** for the first action.
5. Repeats for second coordinate.
6. Press **Start** to begin main macro; mouse macro runs in parallel when its interval elapses.

## Verification Plan
- **Automated Tests**: None (UI‑driven). Manual verification steps will be documented.
- **Manual Verification**:
  1. Start the server, enable mouse macro, set interval to a short value (e.g., 10 s) and coordinates on a test window.
  2. Observe the cursor moving, double‑clicking, moving again, and clicking.
  3. Check that the macro respects the enable toggle and stops when the main macro is stopped.
  4. Verify the settings persist after restarting the app.
