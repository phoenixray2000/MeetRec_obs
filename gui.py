import sys
import os
import json
import shutil
import tempfile
from PyQt6.QtWidgets import (QApplication, QSystemTrayIcon, QMenu, QMainWindow, 
                             QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                             QPushButton, QFileDialog, QMessageBox, QGroupBox, 
                             QLineEdit, QFormLayout, QCheckBox)
from PyQt6.QtGui import QIcon, QAction, QColor, QPixmap, QPainter, QBrush, QKeySequence
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QUrl, QMimeData, QDir
import soundcard as sc
import keyboard
from audio_recorder import AudioRecorder, get_devices
from clipboard_utils import copy_file_to_clipboard

CONFIG_FILE = "settings.json"

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SignalManager(QObject):
    recording_finished = pyqtSignal(str, str)

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

class SettingsWindow(QMainWindow):
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings - Simple Audio Recorder")
        self.setGeometry(100, 100, 500, 600)
        
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Microphone
        group_mic = QGroupBox("Input Device")
        layout_mic = QVBoxLayout()
        self.combo_mic = QComboBox()
        layout_mic.addWidget(self.combo_mic)
        btn_refresh = QPushButton("Refresh Devices")
        btn_refresh.clicked.connect(self.refresh_devices)
        layout_mic.addWidget(btn_refresh)
        group_mic.setLayout(layout_mic)
        layout.addWidget(group_mic)

        # Output
        group_out = QGroupBox("Output Configuration")
        layout_out = QFormLayout()
        
        layout_folder_inner = QHBoxLayout()
        self.lbl_folder = QLabel(os.getcwd())
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_folder)
        layout_folder_inner.addWidget(self.lbl_folder)
        layout_folder_inner.addWidget(btn_browse)
        
        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems(["MP3", "WAV"])
        
        layout_out.addRow("Folder:", layout_folder_inner)
        layout_out.addRow("Format:", self.combo_fmt)
        group_out.setLayout(layout_out)
        layout.addWidget(group_out)

        # Tray Interaction
        group_tray = QGroupBox("Tray Icon Behavior")
        layout_tray = QFormLayout()
        self.combo_left_click = QComboBox()
        self.combo_left_click.addItems(["Last Used", "Microphone", "Loopback", "Both"])
        layout_tray.addRow("Left Click Action:", self.combo_left_click)
        group_tray.setLayout(layout_tray)
        layout.addWidget(group_tray)

        # Notifications
        group_notifications = QGroupBox("Notifications")
        layout_notifications = QVBoxLayout()
        self.chk_notifications = QCheckBox("Show tray notifications")
        self.chk_notifications.setChecked(True)
        layout_notifications.addWidget(self.chk_notifications)
        group_notifications.setLayout(layout_notifications)
        layout.addWidget(group_notifications)

        # Post-Processing
        group_post = QGroupBox("Post-Processing & Clipboard")
        layout_post = QVBoxLayout()
        self.chk_normalize = QCheckBox("Normalize Audio (Apply first)")
        self.chk_clipboard = QCheckBox("Copy File to Clipboard")
        self.chk_delete = QCheckBox("Delete after Copy (Move to Temp)")
        self.chk_delete.setToolTip("Moves the file to the system temp folder before copying, keeping your output folder clean.")
        self.chk_delete.setEnabled(False)
        self.chk_clipboard.toggled.connect(lambda c: self.chk_delete.setEnabled(c))
        
        layout_post.addWidget(self.chk_normalize)
        layout_post.addWidget(self.chk_clipboard)
        layout_post.addWidget(self.chk_delete)
        group_post.setLayout(layout_post)
        layout.addWidget(group_post)

        # Hotkeys
        group_hotkeys = QGroupBox("Global Hotkeys")
        layout_hotkeys = QFormLayout()
        self.hk_mic = HotkeyEdit()
        self.hk_loop = HotkeyEdit()
        self.hk_both = HotkeyEdit()
        self.hk_stop = HotkeyEdit()
        self.chk_stop_with_record_hotkeys = QCheckBox("Use record hotkeys to stop recording")
        self.chk_stop_with_record_hotkeys.setToolTip("When enabled, pressing any record hotkey while recording stops the active recording instead of starting another mode.")
        self.chk_stop_with_record_hotkeys.setChecked(True)
        self.chk_stop_with_record_hotkeys.toggled.connect(self.update_stop_hotkey_state)
        layout_hotkeys.addRow("Record Mic:", self.hk_mic)
        layout_hotkeys.addRow("Record Loopback:", self.hk_loop)
        layout_hotkeys.addRow("Record Both:", self.hk_both)
        layout_hotkeys.addRow("", self.chk_stop_with_record_hotkeys)
        layout_hotkeys.addRow("Stop Recording:", self.hk_stop)
        group_hotkeys.setLayout(layout_hotkeys)
        layout.addWidget(group_hotkeys)

        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)

        self.refresh_devices()
        self.update_stop_hotkey_state()

    def update_stop_hotkey_state(self):
        use_record_hotkeys = self.chk_stop_with_record_hotkeys.isChecked()
        self.hk_stop.setEnabled(not use_record_hotkeys)
        if use_record_hotkeys:
            self.hk_stop.setPlaceholderText("Using record hotkeys")
        else:
            self.hk_stop.setPlaceholderText("Click to set hotkey...")

    def refresh_devices(self):
        self.combo_mic.clear()
        try:
            mics = get_devices(include_loopback=False)
            default_mic = sc.default_microphone()
            default_index = 0
            for i, m in enumerate(mics):
                self.combo_mic.addItem(f"{m['name']}", m['id'])
                if m['id'] == default_mic.id:
                    default_index = i
            self.combo_mic.setCurrentIndex(default_index)
        except Exception as e:
            print(f"Error refreshing devices: {e}")

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder", options=QFileDialog.Option.DontUseNativeDialog)
        if folder:
            self.lbl_folder.setText(folder)

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                self.lbl_folder.setText(data.get("output_folder", os.getcwd()))
                fmt_idx = self.combo_fmt.findText(data.get("format", "MP3"))
                if fmt_idx >= 0: self.combo_fmt.setCurrentIndex(fmt_idx)
                
                saved_id = data.get("device_id")
                if saved_id:
                    idx = self.combo_mic.findData(saved_id)
                    if idx >= 0: self.combo_mic.setCurrentIndex(idx)

                mode = data.get("tray_click_mode", "Last Used")
                mode_idx = self.combo_left_click.findText(mode)
                if mode_idx >= 0: self.combo_left_click.setCurrentIndex(mode_idx)

                self.chk_normalize.setChecked(data.get("normalize", False))
                self.chk_clipboard.setChecked(data.get("clipboard", False))
                self.chk_delete.setChecked(data.get("delete_after", False))
                self.chk_delete.setEnabled(self.chk_clipboard.isChecked())
                self.chk_notifications.setChecked(data.get("show_notifications", True))
                self.chk_stop_with_record_hotkeys.setChecked(data.get("stop_with_record_hotkeys", True))

                self.hk_mic.setText(data.get("hk_mic", ""))
                self.hk_loop.setText(data.get("hk_loop", ""))
                self.hk_both.setText(data.get("hk_both", ""))
                self.hk_stop.setText(data.get("hk_stop", ""))
            except Exception as e:
                print(f"Error loading settings: {e}")
        self.update_stop_hotkey_state()

    def save_settings(self):
        data = self.get_settings()
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            QMessageBox.information(self, "Settings", "Settings saved successfully.")
            self.settings_saved.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

    def get_settings(self):
        return {
            "device_id": self.combo_mic.currentData(),
            "output_folder": self.lbl_folder.text(),
            "format": self.combo_fmt.currentText(),
            "tray_click_mode": self.combo_left_click.currentText(),
            "show_notifications": self.chk_notifications.isChecked(),
            "normalize": self.chk_normalize.isChecked(),
            "clipboard": self.chk_clipboard.isChecked(),
            "delete_after": self.chk_delete.isChecked(),
            "stop_with_record_hotkeys": self.chk_stop_with_record_hotkeys.isChecked(),
            "hk_mic": self.hk_mic.text(),
            "hk_loop": self.hk_loop.text(),
            "hk_both": self.hk_both.text(),
            "hk_stop": self.hk_stop.text()
        }

class TrayApplication(QObject):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.recorder = None
        self.last_mode = "mic" 
        
        self.signals = SignalManager()
        self.signals.recording_finished.connect(self.on_recording_finished)

        self.icon_idle_path = resource_path("icon_idle.png")
        self.icon_rec_path = resource_path("icon_rec.png")
        self.generate_icons()
            
        self.tray_icon = QSystemTrayIcon(QIcon(self.icon_idle_path), self.app)
        self.tray_icon.setToolTip("Simple Audio Recorder (Idle)")
        self.tray_icon.activated.connect(self.on_tray_activated)
        
        self.build_menu()
        self.tray_icon.show()
        
        self.settings_window = SettingsWindow()
        self.settings_window.settings_saved.connect(self.register_hotkeys)
        
        self.tray_icon.showMessage("Ready", "Left-click to toggle recording.", QSystemTrayIcon.MessageIcon.Information, 2000)
        self.register_hotkeys()

    def generate_icons(self):
        if not os.path.exists(self.icon_idle_path):
            pix = QPixmap(64, 64)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(QColor(80, 80, 80)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(4, 4, 56, 56)
            painter.end()
            pix.save(self.icon_idle_path)

        if not os.path.exists(self.icon_rec_path):
            pix = QPixmap(64, 64)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(QColor(220, 0, 0)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(4, 4, 56, 56)
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(22, 22, 20, 20)
            painter.end()
            pix.save(self.icon_rec_path)

    def build_menu(self):
        self.menu = QMenu()
        self.action_record_mic = QAction("Start Recording (Mic)", self)
        self.action_record_mic.triggered.connect(lambda: self.start_recording("mic"))
        self.action_record_loop = QAction("Start Recording (Loopback)", self)
        self.action_record_loop.triggered.connect(lambda: self.start_recording("loopback"))
        self.action_record_both = QAction("Start Recording (Both)", self)
        self.action_record_both.triggered.connect(lambda: self.start_recording("both"))
        self.action_stop = QAction("Stop Recording", self)
        self.action_stop.triggered.connect(self.stop_recording)
        self.action_stop.setEnabled(False)
        self.action_settings = QAction("Settings", self)
        self.action_settings.triggered.connect(self.open_settings)
        self.action_exit = QAction("Exit", self)
        self.action_exit.triggered.connect(self.exit_app)
        
        self.menu.addAction(self.action_record_mic)
        self.menu.addAction(self.action_record_loop)
        self.menu.addAction(self.action_record_both)
        self.menu.addAction(self.action_stop)
        self.menu.addSeparator()
        self.menu.addAction(self.action_settings)
        self.menu.addAction(self.action_exit)
        self.tray_icon.setContextMenu(self.menu)

    def register_hotkeys(self):
        try: keyboard.unhook_all_hotkeys() # Ensure no old hotkeys are active
        except: pass
        settings = self.settings_window.get_settings()
        hk_mic = settings.get("hk_mic")
        hk_loop = settings.get("hk_loop")
        hk_both = settings.get("hk_both")
        hk_stop = settings.get("hk_stop")
        try:
            if hk_mic: keyboard.add_hotkey(hk_mic, lambda: self.start_recording("mic"))
            if hk_loop: keyboard.add_hotkey(hk_loop, lambda: self.start_recording("loopback"))
            if hk_both: keyboard.add_hotkey(hk_both, lambda: self.start_recording("both"))
            if hk_stop: keyboard.add_hotkey(hk_stop, self.stop_recording)
        except Exception as e: print(f"Failed to register hotkeys: {e}")

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.recorder and self.recorder.is_alive():
                self.stop_recording()
            else:
                settings = self.settings_window.get_settings()
                click_mode = settings.get("tray_click_mode", "Last Used")
                target_mode = self.last_mode
                if click_mode == "Microphone": target_mode = "mic"
                elif click_mode == "Loopback": target_mode = "loopback"
                elif click_mode == "Both": target_mode = "both"
                self.start_recording(target_mode)

    def open_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def start_recording(self, mode="mic"):
        if self.recorder and self.recorder.is_alive(): return
        self.last_mode = mode    
        settings = self.settings_window.get_settings()
        target_id = settings['device_id']
        
        def finish_callback(path, error):
            self.signals.recording_finished.emit(path if path else "", error if error else "")

        self.recorder = AudioRecorder(
            mic_id=target_id,
            source_mode=mode,
            output_folder=settings['output_folder'],
            output_format=settings['format'],
            normalize=settings['normalize'],
            on_finish_callback=finish_callback
        )
        self.recorder.start()
        self.action_record_mic.setEnabled(False)
        self.action_record_loop.setEnabled(False)
        self.action_record_both.setEnabled(False)
        self.action_stop.setEnabled(True)
        self.tray_icon.setIcon(QIcon(self.icon_rec_path)) 
        self.tray_icon.setToolTip(f"Recording ({mode})...")
        self.tray_icon.showMessage("Started", f"Recording {mode}", QSystemTrayIcon.MessageIcon.NoIcon, 1000)

    def stop_recording(self):
        if self.recorder: self.recorder.stop()

    def on_recording_finished(self, path, error):
        self.action_record_mic.setEnabled(True)
        self.action_record_loop.setEnabled(True)
        self.action_record_both.setEnabled(True)
        self.action_stop.setEnabled(False)
        self.tray_icon.setIcon(QIcon(self.icon_idle_path))
        self.tray_icon.setToolTip("Simple Audio Recorder (Idle)")
        self.recorder = None
        
        if error:
            self.tray_icon.showMessage("Error", f"Recording failed: {error}", QSystemTrayIcon.MessageIcon.Critical, 4000)
            return
            
        settings = self.settings_window.get_settings()
        final_path = path
        msg = f"Saved to {os.path.basename(path)}"
        
        if settings['clipboard'] and os.path.exists(path):
            try:
                if settings['delete_after']:
                    temp_dir = tempfile.gettempdir()
                    new_path = os.path.join(temp_dir, os.path.basename(path))
                    if os.path.exists(new_path):
                        base, ext = os.path.splitext(new_path)
                        import time
                        new_path = f"{base}_{int(time.time())}{ext}"
                    shutil.move(path, new_path)
                    final_path = new_path
                    msg = "Moved to Temp & Copied to Clipboard."
                else:
                    msg += "\nCopied to clipboard."

                # Use Robust Clipboard Utility
                success, status = copy_file_to_clipboard(final_path)
                if not success:
                    msg += f"\nClipboard Error: {status}"
                else:
                    # Optional: Log success?
                    pass
                
            except Exception as e:
                msg += f"\nClipboard/Move error: {e}"

        self.tray_icon.showMessage("Finished", msg, QSystemTrayIcon.MessageIcon.Information, 2000)

    def exit_app(self):
        if self.recorder: self.recorder.stop()
        self.app.quit()
