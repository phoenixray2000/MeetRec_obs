import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from gui import (
    HotkeyEdit,
    TrayApplication,
    WindowsLowLevelHotkeyManager,
    parse_windows_hotkey,
)


class FakeSettingsWindow:
    def __init__(self, settings):
        self.settings = settings

    def get_settings(self):
        return dict(self.settings)


class FakeHotkeyManager:
    def __init__(self):
        self.cleared = False
        self.registrations = []

    def clear(self):
        self.cleared = True

    def register(self, hotkey, callback):
        self.registrations.append((hotkey, callback))


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

    def test_shortcut_override_alt_shift_letter_is_captured(self):
        edit = HotkeyEdit()
        edit.begin_capture()

        event = QKeyEvent(
            QEvent.Type.ShortcutOverride,
            Qt.Key.Key_R.value,
            Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier,
        )
        QApplication.sendEvent(edit, event)

        self.assertEqual(edit.text(), "alt+shift+r")
        self.assertTrue(event.isAccepted())

    def test_native_virtual_key_fallback_captures_letter(self):
        edit = HotkeyEdit()
        edit.begin_capture()

        event = QKeyEvent(
            QEvent.Type.KeyPress,
            Qt.Key.Key_unknown.value,
            Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.ShiftModifier,
            0,
            ord("R"),
            0,
        )
        edit.keyPressEvent(event)

        self.assertEqual(edit.text(), "alt+shift+r")

    def test_keyboard_hook_captures_alt_shift_letter(self):
        for alt_name in ("alt", "left alt", "right alt"):
            with self.subTest(alt_name=alt_name):
                edit = HotkeyEdit()
                edit.is_capturing = True

                edit.handle_keyboard_hook(
                    SimpleNamespace(event_type="down", name=alt_name, scan_code=56)
                )
                edit.handle_keyboard_hook(
                    SimpleNamespace(event_type="down", name="shift", scan_code=42)
                )
                edit.handle_keyboard_hook(
                    SimpleNamespace(event_type="down", name="r", scan_code=19)
                )

                self.assertEqual(edit.text(), "alt+shift+r")

    def test_keyboard_hook_captures_physical_alt_when_ctrl_alt_are_swapped(self):
        cases = (
            ("ctrl", 56, "alt+shift+r"),
            ("alt", 29, "ctrl+shift+r"),
        )

        for mapped_name, scan_code, expected in cases:
            with self.subTest(mapped_name=mapped_name, scan_code=scan_code):
                edit = HotkeyEdit()
                edit.is_capturing = True

                edit.handle_keyboard_hook(
                    SimpleNamespace(
                        event_type="down", name=mapped_name, scan_code=scan_code
                    )
                )
                edit.handle_keyboard_hook(
                    SimpleNamespace(event_type="down", name="shift", scan_code=42)
                )
                edit.handle_keyboard_hook(
                    SimpleNamespace(event_type="down", name="r", scan_code=19)
                )

                self.assertEqual(edit.text(), expected)

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

    def test_punctuation_hotkeys_are_captured(self):
        cases = (
            (Qt.Key.Key_Minus.value, "ctrl+alt+-"),
            (Qt.Key.Key_Slash.value, "ctrl+alt+/"),
        )

        for key, expected in cases:
            with self.subTest(expected=expected):
                edit = HotkeyEdit()
                edit.begin_capture()

                event = QKeyEvent(
                    QEvent.Type.KeyPress,
                    key,
                    Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.AltModifier,
                )
                edit.keyPressEvent(event)

                self.assertEqual(edit.text(), expected)

    def test_hotkey_separator_punctuation_uses_keyboard_names(self):
        cases = (
            (Qt.Key.Key_Plus.value, "ctrl+alt+plus"),
            (Qt.Key.Key_Comma.value, "ctrl+alt+comma"),
        )

        for key, expected in cases:
            with self.subTest(expected=expected):
                edit = HotkeyEdit()
                edit.begin_capture()

                event = QKeyEvent(
                    QEvent.Type.KeyPress,
                    key,
                    Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.AltModifier,
                )
                edit.keyPressEvent(event)

                self.assertEqual(edit.text(), expected)

    def test_modifier_only_unknown_key_is_ignored(self):
        edit = HotkeyEdit()

        self.assertEqual(
            edit.format_hotkey(
                0,
                Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier,
            ),
            "",
        )


class WindowsHotkeyParserTests(unittest.TestCase):
    def test_parse_alt_shift_letter_for_register_hotkey(self):
        self.assertEqual(parse_windows_hotkey("alt+shift+r"), (0x0001 | 0x0004, 0x52))

    def test_parse_common_keys_for_register_hotkey(self):
        cases = {
            "ctrl+alt+plus": (0x0002 | 0x0001, 0xBB),
            "ctrl+alt+comma": (0x0002 | 0x0001, 0xBC),
            "ctrl+alt+-": (0x0002 | 0x0001, 0xBD),
            "ctrl+alt+/": (0x0002 | 0x0001, 0xBF),
            "windows+shift+f12": (0x0008 | 0x0004, 0x7B),
        }

        for hotkey, expected in cases.items():
            with self.subTest(hotkey=hotkey):
                self.assertEqual(parse_windows_hotkey(hotkey), expected)

    def test_parse_unknown_key_returns_none(self):
        self.assertIsNone(parse_windows_hotkey("alt+shift+unknown-key"))


class WindowsLowLevelHotkeyManagerTests(unittest.TestCase):
    def test_alt_shift_letter_triggers_from_low_level_events(self):
        manager = WindowsLowLevelHotkeyManager(install_hook=False)
        calls = []
        manager.register("alt+shift+r", lambda: calls.append("mic"))

        manager.process_key_event(0x0104, 0xA4)
        manager.process_key_event(0x0100, 0xA0)
        manager.process_key_event(0x0100, 0x52)

        self.assertEqual(calls, ["mic"])

    def test_repeated_keydown_does_not_repeat_until_keyup(self):
        manager = WindowsLowLevelHotkeyManager(install_hook=False)
        calls = []
        manager.register("alt+shift+r", lambda: calls.append("mic"))

        manager.process_key_event(0x0104, 0xA4)
        manager.process_key_event(0x0100, 0xA0)
        manager.process_key_event(0x0100, 0x52)
        manager.process_key_event(0x0100, 0x52)
        manager.process_key_event(0x0101, 0x52)
        manager.process_key_event(0x0100, 0x52)

        self.assertEqual(calls, ["mic", "mic"])

    def test_clear_removes_low_level_registrations(self):
        manager = WindowsLowLevelHotkeyManager(install_hook=False)
        calls = []
        manager.register("alt+shift+r", lambda: calls.append("mic"))

        manager.clear()
        manager.process_key_event(0x0104, 0xA4)
        manager.process_key_event(0x0100, 0xA0)
        manager.process_key_event(0x0100, 0x52)

        self.assertEqual(calls, [])


class TrayApplicationHotkeyTests(unittest.TestCase):
    def test_register_hotkeys_uses_app_hotkey_manager(self):
        hotkey_manager = FakeHotkeyManager()
        subject = SimpleNamespace(
            hotkey_manager=hotkey_manager,
            settings_window=FakeSettingsWindow(
                {
                    "hk_mic": "alt+shift+r",
                    "hk_loop": "ctrl+shift+l",
                    "hk_both": "",
                    "hk_stop": "ctrl+shift+s",
                }
            ),
            started=[],
            stopped=False,
        )
        subject.start_recording = lambda mode: subject.started.append(mode)
        subject.stop_recording = lambda: setattr(subject, "stopped", True)

        with patch("gui.keyboard.add_hotkey") as add_hotkey, patch(
            "gui.keyboard.unhook_all_hotkeys"
        ) as unhook_all_hotkeys:
            TrayApplication.register_hotkeys(subject)

        self.assertTrue(hotkey_manager.cleared)
        self.assertEqual(
            [item[0] for item in hotkey_manager.registrations],
            [
                "alt+shift+r",
                "ctrl+shift+l",
                "ctrl+shift+s",
            ],
        )
        self.assertFalse(add_hotkey.called)
        self.assertFalse(unhook_all_hotkeys.called)

        hotkey_manager.registrations[0][1]()
        hotkey_manager.registrations[2][1]()

        self.assertEqual(subject.started, ["mic"])
        self.assertTrue(subject.stopped)


if __name__ == "__main__":
    unittest.main()
