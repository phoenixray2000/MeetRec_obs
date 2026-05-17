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
