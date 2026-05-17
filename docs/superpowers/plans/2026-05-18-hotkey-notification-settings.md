# Hotkey Notification Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复快捷键捕捉对 `alt+shift+字母` 的识别，增加捕捉态提示、录音快捷键复用为停止快捷键、以及托盘通知开关。

**Architecture:** 保持当前单文件 GUI 架构，不拆大模块；把易测逻辑限制在 `HotkeyEdit`、`TrayApplication.toggle_recording()`、`TrayApplication.show_tray_notification()` 三个小边界。设置继续写入 `settings.json`，新增布尔字段带默认值，旧配置自动兼容。

**Tech Stack:** Python 3.13, PyQt6, keyboard, unittest, PyInstaller.

---

## File Structure

- Modify: `D:\Git\quickaudiorecorder\gui.py`
  - `HotkeyEdit`: 增加捕捉态、提示文字、`alt+shift+letter` 格式化。
  - `SettingsWindow`: 增加 `stop_with_record_hotkeys` 和 `show_notifications` 两个设置项，保存/加载到 JSON。
  - `TrayApplication`: 热键注册从 `start_recording()` 改为 `toggle_recording()`，并用 `show_tray_notification()` 统一控制托盘弹窗。
- Create: `D:\Git\quickaudiorecorder\tests\test_gui_hotkeys.py`
  - 用 `unittest` 验证快捷键捕捉、录音快捷键复用停止、通知开关。
- Modify: `D:\Git\quickaudiorecorder\README.md`
  - 更新 Usage/Features 中的快捷键和通知行为说明。

---

### Task 1: Add Failing Tests For Hotkey Capture And Toggle Behavior

**Files:**
- Create: `D:\Git\quickaudiorecorder\tests\test_gui_hotkeys.py`
- Test: `D:\Git\quickaudiorecorder\tests\test_gui_hotkeys.py`

- [ ] **Step 1: Create the failing test file**

Create `tests/test_gui_hotkeys.py` with this exact content:

```python
import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from gui import HotkeyEdit, TrayApplication


class FakeRecorder:
    def __init__(self, alive):
        self.alive = alive

    def is_alive(self):
        return self.alive


class FakeSettingsWindow:
    def __init__(self, settings):
        self.settings = settings

    def get_settings(self):
        return dict(self.settings)


class FakeTrayIcon:
    def __init__(self):
        self.messages = []

    def showMessage(self, title, message, icon, duration):
        self.messages.append((title, message, icon, duration))


class HotkeyEditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_alt_shift_letter_hotkey_is_captured(self):
        edit = HotkeyEdit()
        edit.begin_capture()

        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_R.value,
            Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier,
        )
        edit.keyPressEvent(event)

        self.assertEqual(edit.text(), "alt+shift+r")

    def test_capture_prompt_is_visible_and_restores_on_escape(self):
        edit = HotkeyEdit()
        edit.setText("ctrl+alt+r")

        edit.begin_capture()
        self.assertEqual(edit.text(), "Press shortcut...")

        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Escape.value,
            Qt.KeyboardModifier.NoModifier,
        )
        edit.keyPressEvent(event)

        self.assertEqual(edit.text(), "ctrl+alt+r")

    def test_delete_clears_hotkey(self):
        edit = HotkeyEdit()
        edit.setText("ctrl+alt+r")
        edit.begin_capture()

        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_Delete.value,
            Qt.KeyboardModifier.NoModifier,
        )
        edit.keyPressEvent(event)

        self.assertEqual(edit.text(), "")


class TrayApplicationHotkeyTests(unittest.TestCase):
    def test_record_hotkey_stops_active_recording_when_option_enabled(self):
        subject = SimpleNamespace(
            recorder=FakeRecorder(alive=True),
            settings_window=FakeSettingsWindow({"stop_with_record_hotkeys": True}),
            stopped=False,
            started=None,
        )
        subject.stop_recording = lambda: setattr(subject, "stopped", True)
        subject.start_recording = lambda mode: setattr(subject, "started", mode)

        TrayApplication.toggle_recording(subject, "mic")

        self.assertTrue(subject.stopped)
        self.assertIsNone(subject.started)

    def test_record_hotkey_does_not_switch_mode_when_option_disabled(self):
        subject = SimpleNamespace(
            recorder=FakeRecorder(alive=True),
            settings_window=FakeSettingsWindow({"stop_with_record_hotkeys": False}),
            stopped=False,
            started=None,
        )
        subject.stop_recording = lambda: setattr(subject, "stopped", True)
        subject.start_recording = lambda mode: setattr(subject, "started", mode)

        TrayApplication.toggle_recording(subject, "loopback")

        self.assertFalse(subject.stopped)
        self.assertIsNone(subject.started)

    def test_record_hotkey_starts_recording_when_idle(self):
        subject = SimpleNamespace(
            recorder=None,
            settings_window=FakeSettingsWindow({"stop_with_record_hotkeys": True}),
            stopped=False,
            started=None,
        )
        subject.stop_recording = lambda: setattr(subject, "stopped", True)
        subject.start_recording = lambda mode: setattr(subject, "started", mode)

        TrayApplication.toggle_recording(subject, "both")

        self.assertFalse(subject.stopped)
        self.assertEqual(subject.started, "both")


class TrayApplicationNotificationTests(unittest.TestCase):
    def test_notification_is_skipped_when_disabled(self):
        subject = SimpleNamespace(
            tray_icon=FakeTrayIcon(),
            settings_window=FakeSettingsWindow({"show_notifications": False}),
        )

        TrayApplication.show_tray_notification(subject, "Started", "Recording mic")

        self.assertEqual(subject.tray_icon.messages, [])

    def test_notification_is_sent_when_enabled(self):
        subject = SimpleNamespace(
            tray_icon=FakeTrayIcon(),
            settings_window=FakeSettingsWindow({"show_notifications": True}),
        )

        TrayApplication.show_tray_notification(subject, "Started", "Recording mic", duration=1234)

        self.assertEqual(len(subject.tray_icon.messages), 1)
        self.assertEqual(subject.tray_icon.messages[0][0], "Started")
        self.assertEqual(subject.tray_icon.messages[0][1], "Recording mic")
        self.assertEqual(subject.tray_icon.messages[0][3], 1234)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests and verify they fail for the expected reasons**

Run:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m unittest tests.test_gui_hotkeys -v
```

Expected: FAIL/ERROR because `HotkeyEdit.begin_capture`, `TrayApplication.toggle_recording`, and `TrayApplication.show_tray_notification` do not exist yet, and `alt+shift+r` behavior is not explicitly protected.

- [ ] **Step 3: Commit the failing tests**

```powershell
git add tests/test_gui_hotkeys.py
git commit -m "test: cover hotkey capture and tray notification behavior"
```

---

### Task 2: Fix HotkeyEdit Capture State And Alt+Shift Letter Formatting

**Files:**
- Modify: `D:\Git\quickaudiorecorder\gui.py:29-90`
- Test: `D:\Git\quickaudiorecorder\tests\test_gui_hotkeys.py`

- [ ] **Step 1: Replace the current `HotkeyEdit` class**

In `gui.py`, replace the entire `HotkeyEdit` class with:

```python
class HotkeyEdit(QLineEdit):
    """
    Custom widget to capture hotkeys by pressing them.
    Maps Qt events to 'keyboard' library compatible strings.
    """
    CAPTURE_PROMPT = "Press shortcut..."

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Click to set hotkey...")
        self.setReadOnly(True)
        self.current_sequence = None
        self.is_capturing = False
        self._previous_text = ""

    def begin_capture(self):
        if self.is_capturing:
            return
        self.is_capturing = True
        self._previous_text = self.text()
        self.setText(self.CAPTURE_PROMPT)
        self.selectAll()
        self.setStyleSheet("color: #666;")

    def finish_capture(self, sequence):
        self.is_capturing = False
        self.current_sequence = sequence or None
        self.setStyleSheet("")
        self.setText(sequence)
        self.clearFocus()

    def cancel_capture(self):
        self.is_capturing = False
        self.setStyleSheet("")
        self.setText(self._previous_text)
        self.clearFocus()

    def mousePressEvent(self, event):
        self.setFocus()
        self.begin_capture()
        super().mousePressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)
        self.begin_capture()

    def focusOutEvent(self, event):
        if self.is_capturing:
            self.is_capturing = False
            self.setStyleSheet("")
            self.setText(self._previous_text)
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key in (Qt.Key.Key_Backspace.value, Qt.Key.Key_Delete.value):
            self.finish_capture("")
            return

        if key == Qt.Key.Key_Escape.value:
            self.cancel_capture()
            return

        if key in (
            Qt.Key.Key_Control.value,
            Qt.Key.Key_Shift.value,
            Qt.Key.Key_Alt.value,
            Qt.Key.Key_Meta.value,
        ):
            return

        final_hotkey = self.format_hotkey(key, modifiers)
        if final_hotkey:
            self.finish_capture(final_hotkey)

    def format_hotkey(self, key, modifiers):
        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("windows")

        key_text = self.key_to_text(key)
        if key_text:
            parts.append(key_text)

        return "+".join(parts)

    def key_to_text(self, key):
        if Qt.Key.Key_A.value <= key <= Qt.Key.Key_Z.value:
            return chr(key).lower()

        if Qt.Key.Key_0.value <= key <= Qt.Key.Key_9.value:
            return chr(key)

        key_map = {
            Qt.Key.Key_F1.value: "f1",
            Qt.Key.Key_F2.value: "f2",
            Qt.Key.Key_F3.value: "f3",
            Qt.Key.Key_F4.value: "f4",
            Qt.Key.Key_F5.value: "f5",
            Qt.Key.Key_F6.value: "f6",
            Qt.Key.Key_F7.value: "f7",
            Qt.Key.Key_F8.value: "f8",
            Qt.Key.Key_F9.value: "f9",
            Qt.Key.Key_F10.value: "f10",
            Qt.Key.Key_F11.value: "f11",
            Qt.Key.Key_F12.value: "f12",
            Qt.Key.Key_Left.value: "left",
            Qt.Key.Key_Right.value: "right",
            Qt.Key.Key_Up.value: "up",
            Qt.Key.Key_Down.value: "down",
            Qt.Key.Key_Space.value: "space",
            Qt.Key.Key_Tab.value: "tab",
            Qt.Key.Key_Return.value: "enter",
            Qt.Key.Key_Enter.value: "enter",
            Qt.Key.Key_Insert.value: "insert",
            Qt.Key.Key_Home.value: "home",
            Qt.Key.Key_End.value: "end",
            Qt.Key.Key_PageUp.value: "pageup",
            Qt.Key.Key_PageDown.value: "pagedown",
            Qt.Key.Key_CapsLock.value: "capslock",
            Qt.Key.Key_NumLock.value: "numlock",
            Qt.Key.Key_ScrollLock.value: "scrolllock",
            Qt.Key.Key_Print.value: "print_screen",
            Qt.Key.Key_Pause.value: "pause",
        }
        return key_map.get(key, "")
```

- [ ] **Step 2: Run the hotkey capture tests**

Run:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m unittest tests.test_gui_hotkeys.HotkeyEditTests -v
```

Expected: PASS for `alt+shift+r`, capture prompt, Escape restore, and Delete clear.

- [ ] **Step 3: Run import and syntax checks**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py gui.py audio_recorder.py clipboard_utils.py tests
.\.venv\Scripts\python.exe -c "import main"
```

Expected: both commands exit with code 0 and no output.

- [ ] **Step 4: Commit the hotkey capture fix**

```powershell
git add gui.py tests/test_gui_hotkeys.py
git commit -m "fix: improve hotkey capture feedback"
```

---

### Task 3: Add Stop-With-Record-Hotkeys And Notification Settings

**Files:**
- Modify: `D:\Git\quickaudiorecorder\gui.py:146-258`
- Test: `D:\Git\quickaudiorecorder\tests\test_gui_hotkeys.py`

- [ ] **Step 1: Add the notification checkbox in `SettingsWindow.init_ui()`**

In `gui.py`, after the tray left-click mode group is added, insert:

```python
        # Notifications
        group_notifications = QGroupBox("Notifications")
        layout_notifications = QVBoxLayout()
        self.chk_notifications = QCheckBox("Show tray notifications")
        self.chk_notifications.setChecked(True)
        layout_notifications.addWidget(self.chk_notifications)
        group_notifications.setLayout(layout_notifications)
        layout.addWidget(group_notifications)
```

- [ ] **Step 2: Add the stop-with-record-hotkeys checkbox in the hotkey group**

In `SettingsWindow.init_ui()`, after `self.hk_stop = HotkeyEdit()`, insert:

```python
        self.chk_stop_with_record_hotkeys = QCheckBox("Use record hotkeys to stop recording")
        self.chk_stop_with_record_hotkeys.setToolTip("When enabled, pressing any record hotkey while recording stops the active recording instead of starting another mode.")
        self.chk_stop_with_record_hotkeys.setChecked(True)
        self.chk_stop_with_record_hotkeys.toggled.connect(self.update_stop_hotkey_state)
```

Then change the hotkey layout rows to:

```python
        layout_hotkeys.addRow("Record Mic:", self.hk_mic)
        layout_hotkeys.addRow("Record Loopback:", self.hk_loop)
        layout_hotkeys.addRow("Record Both:", self.hk_both)
        layout_hotkeys.addRow("", self.chk_stop_with_record_hotkeys)
        layout_hotkeys.addRow("Stop Recording:", self.hk_stop)
```

- [ ] **Step 3: Add the stop hotkey enabled-state helper**

In `SettingsWindow`, after `refresh_devices()`, add:

```python
    def update_stop_hotkey_state(self):
        use_record_hotkeys = self.chk_stop_with_record_hotkeys.isChecked()
        self.hk_stop.setEnabled(not use_record_hotkeys)
        if use_record_hotkeys:
            self.hk_stop.setPlaceholderText("Using record hotkeys")
        else:
            self.hk_stop.setPlaceholderText("Click to set hotkey...")
```

- [ ] **Step 4: Load the new settings with backward-compatible defaults**

In `SettingsWindow.load_settings()`, after the existing clipboard/delete settings load, insert:

```python
                self.chk_notifications.setChecked(data.get("show_notifications", True))
                self.chk_stop_with_record_hotkeys.setChecked(data.get("stop_with_record_hotkeys", True))
                self.update_stop_hotkey_state()
```

Also change the JSON read line from:

```python
                with open(CONFIG_FILE, 'r') as f:
```

to:

```python
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
```

- [ ] **Step 5: Save the new settings**

In `SettingsWindow.save_settings()`, change:

```python
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f)
```

to:

```python
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
```

In `SettingsWindow.get_settings()`, return these two additional fields:

```python
            "show_notifications": self.chk_notifications.isChecked(),
            "stop_with_record_hotkeys": self.chk_stop_with_record_hotkeys.isChecked(),
```

The final return object should keep the existing fields and include:

```python
        return {
            "device_id": self.combo_mic.currentData(),
            "output_folder": self.lbl_folder.text(),
            "format": self.combo_fmt.currentText(),
            "tray_click_mode": self.combo_left_click.currentText(),
            "normalize": self.chk_normalize.isChecked(),
            "clipboard": self.chk_clipboard.isChecked(),
            "delete_after": self.chk_delete.isChecked(),
            "show_notifications": self.chk_notifications.isChecked(),
            "stop_with_record_hotkeys": self.chk_stop_with_record_hotkeys.isChecked(),
            "hk_mic": self.hk_mic.text(),
            "hk_loop": self.hk_loop.text(),
            "hk_both": self.hk_both.text(),
            "hk_stop": self.hk_stop.text()
        }
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m unittest tests.test_gui_hotkeys -v
```

Expected: `HotkeyEditTests` pass; `TrayApplicationHotkeyTests` and `TrayApplicationNotificationTests` still fail until Task 4.

- [ ] **Step 7: Commit the settings UI change**

```powershell
git add gui.py
git commit -m "feat: add hotkey and notification settings"
```

---

### Task 4: Wire Hotkey Toggle Behavior And Notification Filtering

**Files:**
- Modify: `D:\Git\quickaudiorecorder\gui.py:282-443`
- Test: `D:\Git\quickaudiorecorder\tests\test_gui_hotkeys.py`

- [ ] **Step 1: Replace the ready notification call**

In `TrayApplication.__init__()`, change:

```python
        self.tray_icon.showMessage("Ready", "Left-click to toggle recording.", QSystemTrayIcon.MessageIcon.Information, 2000)
```

to:

```python
        self.show_tray_notification("Ready", "Left-click to toggle recording.", QSystemTrayIcon.MessageIcon.Information, 2000)
```

- [ ] **Step 2: Add notification helper methods**

In `TrayApplication`, after `build_menu()`, add:

```python
    def notifications_enabled(self):
        try:
            return self.settings_window.get_settings().get("show_notifications", True)
        except Exception:
            return True

    def show_tray_notification(self, title, message, icon=QSystemTrayIcon.MessageIcon.Information, duration=2000):
        if self.notifications_enabled():
            self.tray_icon.showMessage(title, message, icon, duration)
```

- [ ] **Step 3: Add the toggle recording method**

In `TrayApplication`, before `start_recording()`, add:

```python
    def toggle_recording(self, mode="mic"):
        if self.recorder and self.recorder.is_alive():
            settings = self.settings_window.get_settings()
            if settings.get("stop_with_record_hotkeys", True):
                self.stop_recording()
            return

        self.start_recording(mode)
```

- [ ] **Step 4: Register record hotkeys against `toggle_recording()`**

In `TrayApplication.register_hotkeys()`, replace the hotkey registration block with:

```python
        try:
            if hk_mic:
                keyboard.add_hotkey(hk_mic, lambda: self.toggle_recording("mic"))
            if hk_loop:
                keyboard.add_hotkey(hk_loop, lambda: self.toggle_recording("loopback"))
            if hk_both:
                keyboard.add_hotkey(hk_both, lambda: self.toggle_recording("both"))
            if hk_stop and not settings.get("stop_with_record_hotkeys", True):
                keyboard.add_hotkey(hk_stop, self.stop_recording)
        except Exception as e:
            print(f"Failed to register hotkeys: {e}")
```

- [ ] **Step 5: Replace remaining tray `showMessage()` calls**

In `start_recording()`, change:

```python
        self.tray_icon.showMessage("Started", f"Recording {mode}", QSystemTrayIcon.MessageIcon.NoIcon, 1000)
```

to:

```python
        self.show_tray_notification("Started", f"Recording {mode}", QSystemTrayIcon.MessageIcon.NoIcon, 1000)
```

In `on_recording_finished()`, change:

```python
            self.tray_icon.showMessage("Error", f"Recording failed: {error}", QSystemTrayIcon.MessageIcon.Critical, 4000)
```

to:

```python
            self.show_tray_notification("Error", f"Recording failed: {error}", QSystemTrayIcon.MessageIcon.Critical, 4000)
```

At the end of `on_recording_finished()`, change:

```python
        self.tray_icon.showMessage("Finished", msg, QSystemTrayIcon.MessageIcon.Information, 2000)
```

to:

```python
        self.show_tray_notification("Finished", msg, QSystemTrayIcon.MessageIcon.Information, 2000)
```

- [ ] **Step 6: Run all unit tests**

Run:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: all tests pass.

- [ ] **Step 7: Run syntax and import checks**

Run:

```powershell
.\.venv\Scripts\python.exe -m compileall -q main.py gui.py audio_recorder.py clipboard_utils.py tests
.\.venv\Scripts\python.exe -c "import main"
```

Expected: both commands exit with code 0 and no output.

- [ ] **Step 8: Commit the behavior wiring**

```powershell
git add gui.py tests/test_gui_hotkeys.py
git commit -m "feat: allow record hotkeys to stop recording"
```

---

### Task 5: Update User Documentation

**Files:**
- Modify: `D:\Git\quickaudiorecorder\README.md`

- [ ] **Step 1: Update the feature list**

In `README.md`, under `**Control:**`, replace the hotkey bullet:

```markdown
    -   **Global Hotkeys:** Start/Stop recording from anywhere (e.g., `Ctrl+Alt+R`).
```

with:

```markdown
    -   **Global Hotkeys:** Start/stop recording from anywhere, including `Alt+Shift+<letter>` combinations.
    -   **Notification Toggle:** Turn tray balloon notifications on or off from Settings.
```

- [ ] **Step 2: Update Usage**

In `README.md`, after:

```markdown
3.  Set your **Hotkeys** (optional).
```

insert:

```markdown
    - Enable **Use record hotkeys to stop recording** if you want the same hotkey to stop the active recording.
    - Disable **Show tray notifications** if you prefer silent tray operation.
```

- [ ] **Step 3: Commit documentation**

```powershell
git add README.md
git commit -m "docs: document hotkey and notification settings"
```

---

### Task 6: Package And Verify The EXE

**Files:**
- Read: `D:\Git\quickaudiorecorder\README.md`
- Output: `D:\Git\quickaudiorecorder\dist\QuickAudioRecorder.exe`

- [ ] **Step 1: Confirm no running executable will lock the output**

Run:

```powershell
Get-Process QuickAudioRecorder -ErrorAction SilentlyContinue | Select-Object Id,Path,StartTime
```

Expected: no output. If a process is listed, stop only that process before packaging:

```powershell
Stop-Process -Name QuickAudioRecorder
```

- [ ] **Step 2: Run the full verification set**

Run:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q main.py gui.py audio_recorder.py clipboard_utils.py tests
.\.venv\Scripts\python.exe -c "import main"
```

Expected: tests pass, compile/import checks exit with code 0.

- [ ] **Step 3: Build the executable**

Run:

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconsole --onefile --name QuickAudioRecorder main.py
```

Expected: PyInstaller exits with code 0 and reports:

```text
Build complete! The results are available in: D:\Git\quickaudiorecorder\dist
```

- [ ] **Step 4: Verify the artifact**

Run:

```powershell
Get-Item -LiteralPath 'dist\QuickAudioRecorder.exe' | Select-Object FullName,Length,LastWriteTime
Get-FileHash -LiteralPath 'dist\QuickAudioRecorder.exe' -Algorithm SHA256
```

Expected: `dist\QuickAudioRecorder.exe` exists, has a current timestamp, and has a non-empty SHA256 hash.

- [ ] **Step 5: Review PyInstaller warnings**

Run:

```powershell
Get-Content -LiteralPath 'build\QuickAudioRecorder\warn-QuickAudioRecorder.txt' -Encoding UTF8
```

Expected: warnings may include optional POSIX/macOS modules, cffi parser tables, and numpy optional imports. Treat compile errors, missing PyQt6 DLLs, or missing `soundcard`, `soundfile`, `lameenc`, `keyboard` as blockers.

- [ ] **Step 6: Commit final state if there are source/doc changes not yet committed**

Run:

```powershell
git status --short --branch
git diff --stat
```

Expected: only ignored build artifacts are present. If source/doc/test changes remain unstaged, commit them:

```powershell
git add gui.py README.md tests/test_gui_hotkeys.py
git commit -m "feat: improve hotkey and notification settings"
```

---

## Manual Acceptance Checklist

- [ ] Click a hotkey field: the field immediately displays `Press shortcut...`.
- [ ] Press `Alt+Shift+R`: the field stores `alt+shift+r`.
- [ ] Press Escape while capturing: the previous hotkey text is restored.
- [ ] Press Delete while capturing: the hotkey is cleared.
- [ ] Enable `Use record hotkeys to stop recording`, start Mic recording with its hotkey, press the same hotkey again, and recording stops.
- [ ] While recording Mic, press another configured record hotkey; the active recording stops and does not switch mode mid-recording.
- [ ] Disable `Use record hotkeys to stop recording`, start recording, press a record hotkey again, and recording continues.
- [ ] Configure a separate Stop Recording hotkey while `Use record hotkeys to stop recording` is disabled; pressing it stops the active recording.
- [ ] Disable `Show tray notifications`; Ready/Started/Error/Finished tray balloons do not appear.
- [ ] Re-enable `Show tray notifications`; Started and Finished tray balloons appear again.

## Self-Review

- Spec coverage:
  - `alt+shift+字母键` 识别: Task 1 and Task 2.
  - 捕捉态文字提示: Task 1 and Task 2.
  - 结束快捷键增加“使用与开始录音相同的快捷键”: Task 3.
  - 录音中再次按快捷键结束录音: Task 4.
  - 是否开启通知弹出提示: Task 3 and Task 4.
  - 打包 exe 验证: Task 6.
- Placeholder scan: no placeholder markers, undefined function names, or unspecified test commands remain.
- Type consistency:
  - Setting keys are `show_notifications` and `stop_with_record_hotkeys` in load, save, tests, and runtime.
  - Runtime methods are `toggle_recording()`, `notifications_enabled()`, and `show_tray_notification()` in tests and implementation steps.
