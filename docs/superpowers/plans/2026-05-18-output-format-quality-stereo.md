# Output Format Quality Stereo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add WAV, FLAC, and MP3 output with Balanced/High Quality presets, a stereo toggle, English settings labels, and a live output preview.

**Architecture:** Keep format decisions in `audio_recorder.py` as the single source of truth, then have `gui.py` import those profiles for settings controls and preview text. Recording should capture directly at the selected sample rate and channel count, then encode the final file according to the selected format.

**Tech Stack:** Python threads, `soundcard` capture, `soundfile/libsndfile` WAV/FLAC writing, `lameenc` MP3 encoding, PyQt6 settings UI, `unittest`.

---

## File Structure

- Modify: `audio_recorder.py`
  - Owns `FORMAT_CONFIG`, `QUALITY_CONFIG`, `build_output_profile()`, preview description text, capture sample rate/channel selection, and final output writing.
- Modify: `gui.py`
  - Owns English settings controls: `Format`, `Quality`, `Keep Stereo`, `Preview`, settings persistence, and passing `quality`/`stereo` into `AudioRecorder`.
- Create: `tests/test_audio_output_profile.py`
  - Unit tests for format/quality mapping, preview text, true WAV/FLAC writing, and MP3 bitrate routing.
- Modify: `tests/test_gui_hotkeys.py`
  - Add settings-window tests for default values, legacy config migration, preview update, and `TrayApplication.start_recording()` parameter forwarding.
- Modify: `README.md`
  - Document the new output options in English.

No PRD file exists in this repository, so there is no PRD update step for this change.

---

### Task 1: Add Output Profile Configuration

**Files:**
- Modify: `audio_recorder.py`
- Create: `tests/test_audio_output_profile.py`

- [ ] **Step 1: Write failing profile tests**

Create `tests/test_audio_output_profile.py`:

```python
import unittest

from audio_recorder import (
    FORMAT_CONFIG,
    QUALITY_CONFIG,
    build_output_profile,
    describe_output_profile,
)


class OutputProfileTests(unittest.TestCase):
    def test_format_config_contains_supported_outputs(self):
        self.assertEqual(set(FORMAT_CONFIG), {"wav", "flac", "mp3"})
        self.assertEqual(FORMAT_CONFIG["wav"]["extension"], ".wav")
        self.assertEqual(FORMAT_CONFIG["flac"]["format"], "FLAC")
        self.assertEqual(FORMAT_CONFIG["mp3"]["encoder"], "lameenc")

    def test_quality_config_matches_required_mapping(self):
        self.assertEqual(QUALITY_CONFIG["balanced"]["sample_rate"], 16000)
        self.assertEqual(QUALITY_CONFIG["balanced"]["subtype"], "PCM_16")
        self.assertEqual(QUALITY_CONFIG["balanced"]["mp3_bitrate_kbps"], 64)
        self.assertEqual(QUALITY_CONFIG["high"]["sample_rate"], 48000)
        self.assertEqual(QUALITY_CONFIG["high"]["subtype"], "PCM_24")
        self.assertEqual(QUALITY_CONFIG["high"]["mp3_bitrate_kbps"], 128)

    def test_build_output_profile_applies_mono_channels(self):
        profile = build_output_profile("flac", "balanced", stereo=False)

        self.assertEqual(profile["label"], "FLAC")
        self.assertEqual(profile["extension"], ".flac")
        self.assertEqual(profile["sample_rate"], 16000)
        self.assertEqual(profile["subtype"], "PCM_16")
        self.assertEqual(profile["channels"], 1)

    def test_build_output_profile_applies_stereo_channels(self):
        profile = build_output_profile("mp3", "high", stereo=True)

        self.assertEqual(profile["label"], "MP3")
        self.assertEqual(profile["sample_rate"], 48000)
        self.assertEqual(profile["mp3_bitrate_kbps"], 128)
        self.assertEqual(profile["channels"], 2)

    def test_describe_output_profile_uses_english_preview_text(self):
        self.assertEqual(
            describe_output_profile("flac", "balanced", stereo=False),
            "FLAC / 16 kHz / mono / PCM_16",
        )
        self.assertEqual(
            describe_output_profile("mp3", "high", stereo=True),
            "MP3 / 48 kHz / stereo / 128 kbps",
        )

    def test_invalid_profile_keys_raise_value_error(self):
        with self.assertRaises(ValueError):
            build_output_profile("ogg", "balanced", stereo=False)
        with self.assertRaises(ValueError):
            build_output_profile("flac", "studio", stereo=False)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the new tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_audio_output_profile -v
```

Expected: FAIL because `FORMAT_CONFIG`, `QUALITY_CONFIG`, `build_output_profile`, and `describe_output_profile` are not defined.

- [ ] **Step 3: Add profile config and preview helpers**

In `audio_recorder.py`, insert this block after imports:

```python
FORMAT_CONFIG = {
    "wav": {
        "label": "WAV",
        "extension": ".wav",
        "encoder": "soundfile",
        "format": "WAV",
    },
    "flac": {
        "label": "FLAC",
        "extension": ".flac",
        "encoder": "soundfile",
        "format": "FLAC",
    },
    "mp3": {
        "label": "MP3",
        "extension": ".mp3",
        "encoder": "lameenc",
    },
}

QUALITY_CONFIG = {
    "balanced": {
        "label": "Balanced",
        "sample_rate": 16000,
        "subtype": "PCM_16",
        "mp3_bitrate_kbps": 64,
    },
    "high": {
        "label": "High Quality",
        "sample_rate": 48000,
        "subtype": "PCM_24",
        "mp3_bitrate_kbps": 128,
    },
}


def build_output_profile(fmt, quality, stereo):
    fmt_key = str(fmt or "").lower()
    quality_key = str(quality or "").lower()

    if fmt_key not in FORMAT_CONFIG:
        raise ValueError(f"Unsupported output format: {fmt}")
    if quality_key not in QUALITY_CONFIG:
        raise ValueError(f"Unsupported output quality: {quality}")

    channels = 2 if stereo else 1
    return {
        **FORMAT_CONFIG[fmt_key],
        **QUALITY_CONFIG[quality_key],
        "format_key": fmt_key,
        "quality_key": quality_key,
        "channels": channels,
    }


def describe_output_profile(fmt, quality, stereo):
    profile = build_output_profile(fmt, quality, stereo)
    rate_khz = profile["sample_rate"] // 1000
    channels = "stereo" if profile["channels"] == 2 else "mono"
    encoding = (
        f"{profile['mp3_bitrate_kbps']} kbps"
        if profile["encoder"] == "lameenc"
        else profile["subtype"]
    )
    return f"{profile['label']} / {rate_khz} kHz / {channels} / {encoding}"
```

- [ ] **Step 4: Run profile tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_audio_output_profile -v
```

Expected: PASS for all `OutputProfileTests`.

- [ ] **Step 5: Commit Task 1**

Run:

```powershell
git add audio_recorder.py tests/test_audio_output_profile.py
git commit -m "Add audio output profile configuration"
```

---

### Task 2: Encode Real WAV, FLAC, and MP3 Outputs

**Files:**
- Modify: `audio_recorder.py`
- Modify: `tests/test_audio_output_profile.py`

- [ ] **Step 1: Add failing final-output tests**

Append these tests inside `OutputProfileTests` in `tests/test_audio_output_profile.py`:

```python
    def test_write_final_output_creates_real_flac_file(self):
        import os
        import tempfile

        import numpy as np
        import soundfile as sf

        with tempfile.TemporaryDirectory() as temp_dir:
            source_wav = os.path.join(temp_dir, "source.wav")
            final_flac = os.path.join(temp_dir, "final.flac")
            data = np.zeros((160, 1), dtype=np.float32)
            sf.write(source_wav, data, 16000, format="WAV", subtype="PCM_16")

            recorder = self._make_recorder("flac", "balanced", stereo=False)
            recorder._write_final_output(source_wav, final_flac)

            info = sf.info(final_flac)
            self.assertEqual(info.format, "FLAC")
            self.assertEqual(info.samplerate, 16000)
            self.assertEqual(info.channels, 1)
            self.assertEqual(info.subtype, "PCM_16")

    def test_write_final_output_creates_high_quality_wav_file(self):
        import os
        import tempfile

        import numpy as np
        import soundfile as sf

        with tempfile.TemporaryDirectory() as temp_dir:
            source_wav = os.path.join(temp_dir, "source.wav")
            final_wav = os.path.join(temp_dir, "final.wav")
            data = np.zeros((480, 2), dtype=np.float32)
            sf.write(source_wav, data, 48000, format="WAV", subtype="PCM_24")

            recorder = self._make_recorder("wav", "high", stereo=True)
            recorder._write_final_output(source_wav, final_wav)

            info = sf.info(final_wav)
            self.assertEqual(info.format, "WAV")
            self.assertEqual(info.samplerate, 48000)
            self.assertEqual(info.channels, 2)
            self.assertEqual(info.subtype, "PCM_24")

    def test_write_final_output_uses_profile_mp3_bitrate(self):
        import os
        import tempfile
        from unittest.mock import patch

        import numpy as np
        import soundfile as sf

        with tempfile.TemporaryDirectory() as temp_dir:
            source_wav = os.path.join(temp_dir, "source.wav")
            final_mp3 = os.path.join(temp_dir, "final.mp3")
            data = np.zeros((160, 1), dtype=np.float32)
            sf.write(source_wav, data, 16000, format="WAV", subtype="PCM_16")

            recorder = self._make_recorder("mp3", "balanced", stereo=False)
            with patch.object(recorder, "_convert_to_mp3") as convert_to_mp3:
                recorder._write_final_output(source_wav, final_mp3)

            convert_to_mp3.assert_called_once_with(source_wav, final_mp3, 64)

    def _make_recorder(self, fmt, quality, stereo):
        from audio_recorder import AudioRecorder

        return AudioRecorder(
            mic_id="mic1",
            source_mode="mic",
            output_folder=".",
            output_format=fmt,
            quality=quality,
            stereo=stereo,
        )
```

- [ ] **Step 2: Run final-output tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_audio_output_profile -v
```

Expected: FAIL because `AudioRecorder.__init__()` does not accept `quality` or `stereo`, and `_write_final_output()` does not exist.

- [ ] **Step 3: Update `AudioRecorder.__init__()` to store profile settings**

Replace the constructor signature and format fields in `audio_recorder.py` with:

```python
    def __init__(
        self,
        mic_id,
        source_mode,
        output_folder,
        output_format="flac",
        quality="balanced",
        stereo=False,
        normalize=False,
        on_finish_callback=None,
    ):
        super().__init__()
        self.mic_id = mic_id
        self.source_mode = source_mode  # "mic", "loopback", "both"
        self.output_folder = output_folder
        self.output_format = str(output_format or "flac").lower()
        self.quality = str(quality or "balanced").lower()
        self.stereo = bool(stereo)
        self.profile = build_output_profile(
            self.output_format,
            self.quality,
            self.stereo,
        )
        self.normalize = normalize
        self.callback = on_finish_callback
```

- [ ] **Step 4: Capture temp WAV at selected sample rate and channels**

Update `RawRecorder` to accept the selected WAV subtype:

```python
class RawRecorder(threading.Thread):
    """
    Helper thread to record a single device to a WAV file.
    """
    def __init__(self, device, filepath, samplerate=44100, channels=2, subtype="PCM_16"):
        super().__init__()
        self.device = device
        self.filepath = filepath
        self.samplerate = samplerate
        self.channels = channels
        self.subtype = subtype
        self.stop_event = threading.Event()
        self.error = None
```

Update `RawRecorder.run()` so the temporary capture file uses the selected subtype:

```python
            with sf.SoundFile(
                self.filepath,
                mode="w",
                samplerate=self.samplerate,
                channels=self.channels,
                format="WAV",
                subtype=self.subtype,
            ) as f_wav:
```

In `AudioRecorder.run()`, before recorder setup, add:

```python
            samplerate = self.profile["sample_rate"]
            channels = self.profile["channels"]
            subtype = self.profile["subtype"]
```

Replace every `RawRecorder(...)` creation with the selected values:

```python
                self.recorders.append(RawRecorder(dev_mic, t1, samplerate=samplerate, channels=channels, subtype=subtype))
                self.recorders.append(RawRecorder(dev_loop, t2, samplerate=samplerate, channels=channels, subtype=subtype))
```

```python
                self.recorders.append(RawRecorder(dev, t1, samplerate=samplerate, channels=channels, subtype=subtype))
```

```python
                self.recorders.append(RawRecorder(dev, t1, samplerate=samplerate, channels=channels, subtype=subtype))
```

Replace the mixed-audio call:

```python
                self._mix_audio(self.temp_files[0], self.temp_files[1], mixed_wav)
```

with:

```python
                self._mix_audio(self.temp_files[0], self.temp_files[1], mixed_wav, subtype)
```

Update the filename creation block:

```python
            filename = f"Recording_{timestamp}{self.profile['extension']}"
            self.final_filepath = os.path.join(self.output_folder, filename)
            self._write_final_output(source_wav, self.final_filepath)
```

- [ ] **Step 5: Add final-output writer and bitrate-aware MP3 conversion**

Replace `_mix_audio()` with a subtype-preserving version:

```python
    def _mix_audio(self, file1, file2, out_file, subtype):
        d1, sr1 = sf.read(file1)
        d2, sr2 = sf.read(file2)

        max_len = max(len(d1), len(d2))

        if len(d1) < max_len:
            pad_width = max_len - len(d1)
            shape = (pad_width, d1.shape[1]) if d1.ndim > 1 else (pad_width,)
            d1 = np.concatenate((d1, np.zeros(shape, dtype=d1.dtype)))

        if len(d2) < max_len:
            pad_width = max_len - len(d2)
            shape = (pad_width, d2.shape[1]) if d2.ndim > 1 else (pad_width,)
            d2 = np.concatenate((d2, np.zeros(shape, dtype=d2.dtype)))

        mixed = np.clip(d1 + d2, -1.0, 1.0)
        sf.write(out_file, mixed, sr1, format="WAV", subtype=subtype)
```

Replace `_normalize_audio()` with a format-preserving version:

```python
    def _normalize_audio(self, filepath):
        try:
            info = sf.info(filepath)
            data, sr = sf.read(filepath)
            max_val = np.max(np.abs(data))
            if max_val > 0:
                target_peak = 0.99
                factor = target_peak / max_val
                data = data * factor
                sf.write(filepath, data, sr, format=info.format, subtype=info.subtype)
        except Exception as e:
            print(f"Normalization failed: {e}")
```

Replace the old finalize branch and `_convert_to_mp3()` with:

```python
    def _write_final_output(self, source_wav, final_filepath):
        if self.profile["encoder"] == "lameenc":
            self._convert_to_mp3(
                source_wav,
                final_filepath,
                self.profile["mp3_bitrate_kbps"],
            )
            return

        data, sr = sf.read(source_wav, always_2d=True)
        if self.profile["channels"] == 1 and data.shape[1] > 1:
            data = np.mean(data, axis=1, keepdims=True)

        sf.write(
            final_filepath,
            data,
            sr,
            format=self.profile["format"],
            subtype=self.profile["subtype"],
        )

    def _convert_to_mp3(self, src_wav, dst_mp3, bitrate_kbps):
        data, sr = sf.read(src_wav, always_2d=True)
        if self.profile["channels"] == 1 and data.shape[1] > 1:
            data = np.mean(data, axis=1, keepdims=True)
        channels = data.shape[1]

        pcm_data = (data * 32767).clip(-32768, 32767).astype(np.int16)

        encoder = lameenc.Encoder()
        encoder.set_bit_rate(bitrate_kbps)
        encoder.set_in_sample_rate(sr)
        encoder.set_channels(channels)
        encoder.set_quality(2)

        mp3_data = encoder.encode(pcm_data.tobytes())
        mp3_data += encoder.flush()

        with open(dst_mp3, "wb") as f_mp3:
            f_mp3.write(mp3_data)
```

- [ ] **Step 6: Run final-output tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_audio_output_profile -v
```

Expected: PASS for profile and final-output tests.

- [ ] **Step 7: Commit Task 2**

Run:

```powershell
git add audio_recorder.py tests/test_audio_output_profile.py
git commit -m "Encode selected audio output formats"
```

---

### Task 3: Update Settings UI and Persistence

**Files:**
- Modify: `gui.py`
- Modify: `tests/test_gui_hotkeys.py`

- [ ] **Step 1: Add failing settings-window tests**

Append this class to `tests/test_gui_hotkeys.py` after `SettingsWindowLegacyHotkeyTests`:

```python
class SettingsWindowOutputProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_settings_window(self, settings):
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        previous_cwd = os.getcwd()
        os.chdir(temp_dir.name)
        self.addCleanup(os.chdir, previous_cwd)

        if settings is not None:
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(settings, f)

        patches = [
            patch("gui.get_devices", return_value=[{"name": "Default Mic", "id": "mic1"}]),
            patch("gui.sc.default_microphone", return_value=SimpleNamespace(id="mic1")),
        ]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

        window = SettingsWindow()
        self.addCleanup(window.close)
        return window

    def test_default_output_profile_is_flac_balanced_mono(self):
        window = self.make_settings_window(None)

        settings = window.get_settings()

        self.assertEqual(settings["format"], "flac")
        self.assertEqual(settings["quality"], "balanced")
        self.assertFalse(settings["stereo"])
        self.assertEqual(window.lbl_preview.text(), "FLAC / 16 kHz / mono / PCM_16")

    def test_legacy_uppercase_format_is_loaded(self):
        window = self.make_settings_window({"format": "MP3"})

        settings = window.get_settings()

        self.assertEqual(settings["format"], "mp3")
        self.assertEqual(settings["quality"], "balanced")
        self.assertFalse(settings["stereo"])
        self.assertEqual(window.lbl_preview.text(), "MP3 / 16 kHz / mono / 64 kbps")

    def test_high_quality_stereo_preview_updates(self):
        window = self.make_settings_window(None)

        window.combo_fmt.setCurrentIndex(window.combo_fmt.findData("wav"))
        window.combo_quality.setCurrentIndex(window.combo_quality.findData("high"))
        window.chk_stereo.setChecked(True)

        self.assertEqual(window.lbl_preview.text(), "WAV / 48 kHz / stereo / PCM_24")
```

- [ ] **Step 2: Run settings-window tests and verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gui_hotkeys.SettingsWindowOutputProfileTests -v
```

Expected: FAIL because `combo_quality`, `chk_stereo`, and `lbl_preview` are not defined, and `get_settings()` still returns uppercase format text.

- [ ] **Step 3: Import profile helpers into `gui.py`**

Replace:

```python
from audio_recorder import AudioRecorder, get_devices
```

with:

```python
from audio_recorder import (
    AudioRecorder,
    FORMAT_CONFIG,
    QUALITY_CONFIG,
    describe_output_profile,
    get_devices,
)
```

- [ ] **Step 4: Replace output controls with format, quality, stereo, and preview**

In `SettingsWindow.init_ui()`, replace:

```python
        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems(["MP3", "WAV"])

        layout_out.addRow("Folder:", layout_folder_inner)
        layout_out.addRow("Format:", self.combo_fmt)
```

with:

```python
        self.combo_fmt = QComboBox()
        for key, config in FORMAT_CONFIG.items():
            self.combo_fmt.addItem(config["label"], key)

        self.combo_quality = QComboBox()
        for key, config in QUALITY_CONFIG.items():
            self.combo_quality.addItem(config["label"], key)

        self.chk_stereo = QCheckBox("Keep Stereo")
        self.lbl_preview = QLabel()

        self.combo_fmt.currentIndexChanged.connect(self.update_output_preview)
        self.combo_quality.currentIndexChanged.connect(self.update_output_preview)
        self.chk_stereo.toggled.connect(self.update_output_preview)

        layout_out.addRow("Folder:", layout_folder_inner)
        layout_out.addRow("Format:", self.combo_fmt)
        layout_out.addRow("Quality:", self.combo_quality)
        layout_out.addRow("Stereo:", self.chk_stereo)
        layout_out.addRow("Preview:", self.lbl_preview)
```

- [ ] **Step 5: Add settings normalization and preview methods**

Add these methods inside `SettingsWindow` before `load_settings()`:

```python
    def _set_combo_by_data(self, combo, value, default_value):
        normalized = str(value or default_value).lower()
        idx = combo.findData(normalized)
        if idx < 0:
            idx = combo.findData(default_value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def update_output_preview(self):
        fmt = self.combo_fmt.currentData() or "flac"
        quality = self.combo_quality.currentData() or "balanced"
        stereo = self.chk_stereo.isChecked()
        self.lbl_preview.setText(describe_output_profile(fmt, quality, stereo))
```

- [ ] **Step 6: Update settings load/save defaults**

In `load_settings()`, replace:

```python
                fmt_idx = self.combo_fmt.findText(data.get("format", "MP3"))
                if fmt_idx >= 0: self.combo_fmt.setCurrentIndex(fmt_idx)
```

with:

```python
                self._set_combo_by_data(self.combo_fmt, data.get("format"), "flac")
                self._set_combo_by_data(self.combo_quality, data.get("quality"), "balanced")
                self.chk_stereo.setChecked(data.get("stereo", False))
                self.update_output_preview()
```

After the `if os.path.exists(CONFIG_FILE):` block and before `self.update_stop_hotkey_state()`, add:

```python
        else:
            self._set_combo_by_data(self.combo_fmt, None, "flac")
            self._set_combo_by_data(self.combo_quality, None, "balanced")
            self.chk_stereo.setChecked(False)
        self.update_output_preview()
```

In `get_settings()`, replace:

```python
            "format": self.combo_fmt.currentText(),
```

with:

```python
            "format": self.combo_fmt.currentData(),
            "quality": self.combo_quality.currentData(),
            "stereo": self.chk_stereo.isChecked(),
```

- [ ] **Step 7: Run settings-window tests and verify they pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gui_hotkeys.SettingsWindowOutputProfileTests -v
```

Expected: PASS for all output-profile settings tests.

- [ ] **Step 8: Commit Task 3**

Run:

```powershell
git add gui.py tests/test_gui_hotkeys.py
git commit -m "Add output profile settings UI"
```

---

### Task 4: Pass Output Profile Settings Into Recording

**Files:**
- Modify: `gui.py`
- Modify: `tests/test_gui_hotkeys.py`

- [ ] **Step 1: Add failing recorder-parameter test**

Append this test to `TrayApplicationHotkeyTests` in `tests/test_gui_hotkeys.py`:

```python
    def test_start_recording_passes_output_profile_settings(self):
        subject = SimpleNamespace(
            recorder=None,
            last_mode=None,
            settings_window=FakeSettingsWindow(
                {
                    "device_id": "mic1",
                    "output_folder": "D:/recordings",
                    "format": "flac",
                    "quality": "balanced",
                    "stereo": False,
                    "normalize": True,
                }
            ),
            signals=SimpleNamespace(recording_finished=SimpleNamespace(emit=lambda path, error: None)),
            action_record_mic=SimpleNamespace(setEnabled=lambda value: None),
            action_record_loop=SimpleNamespace(setEnabled=lambda value: None),
            action_record_both=SimpleNamespace(setEnabled=lambda value: None),
            action_stop=SimpleNamespace(setEnabled=lambda value: None),
            tray_icon=SimpleNamespace(
                setIcon=lambda icon: None,
                setToolTip=lambda text: None,
            ),
            icon_rec_path="icon_rec.png",
            shown=[],
        )
        subject.show_tray_notification = lambda *args: subject.shown.append(args)

        with patch("gui.QIcon", return_value=object()), patch("gui.AudioRecorder") as recorder_cls:
            recorder = recorder_cls.return_value
            recorder.is_alive.return_value = False

            TrayApplication.start_recording(subject, "mic")

        recorder_cls.assert_called_once()
        kwargs = recorder_cls.call_args.kwargs
        self.assertEqual(kwargs["mic_id"], "mic1")
        self.assertEqual(kwargs["source_mode"], "mic")
        self.assertEqual(kwargs["output_folder"], "D:/recordings")
        self.assertEqual(kwargs["output_format"], "flac")
        self.assertEqual(kwargs["quality"], "balanced")
        self.assertFalse(kwargs["stereo"])
        self.assertTrue(kwargs["normalize"])
        recorder.start.assert_called_once()
```

- [ ] **Step 2: Run the recorder-parameter test and verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gui_hotkeys.TrayApplicationHotkeyTests.test_start_recording_passes_output_profile_settings -v
```

Expected: FAIL because `TrayApplication.start_recording()` does not pass `quality` or `stereo`.

- [ ] **Step 3: Forward `quality` and `stereo` to `AudioRecorder`**

In `TrayApplication.start_recording()`, replace:

```python
            output_format=settings['format'],
            normalize=settings['normalize'],
```

with:

```python
            output_format=settings["format"],
            quality=settings["quality"],
            stereo=settings["stereo"],
            normalize=settings["normalize"],
```

- [ ] **Step 4: Run the recorder-parameter test and verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_gui_hotkeys.TrayApplicationHotkeyTests.test_start_recording_passes_output_profile_settings -v
```

Expected: PASS.

- [ ] **Step 5: Commit Task 4**

Run:

```powershell
git add gui.py tests/test_gui_hotkeys.py
git commit -m "Pass output profile into recordings"
```

---

### Task 5: Update English Documentation

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README feature bullets**

In `README.md`, under `## Features`, replace the output-related area after the mode bullets with:

```markdown
-   **Output Profiles:**
    -   **Format:** Save recordings as WAV, FLAC, or MP3.
    -   **Quality:** Choose Balanced for compact 16 kHz output or High Quality for 48 kHz output.
    -   **Stereo:** Keep stereo channels when needed, or leave it off for mono recordings.
-   **Post-Processing:**
    -   **Auto-Normalize:** Automatically adjusts volume to optimal levels after recording.
    -   **Clipboard Integration:** Automatically copies the file (or file path) to your clipboard.
    -   **Clean Workflow:** Option to move the file to a temp folder and copy it, keeping your desktop clean.
```

- [ ] **Step 2: Update usage step for output profile selection**

In `README.md`, replace:

```markdown
2.  Select your **Microphone** and **Output Folder**.
```

with:

```markdown
2.  Select your **Microphone**, **Output Folder**, **Format**, **Quality**, and **Stereo** preference.
```

- [ ] **Step 3: Update dependency note if needed**

Keep the existing requirements line because the change reuses current dependencies:

```markdown
-   `pip install PyQt6 soundcard soundfile numpy lameenc keyboard`
```

- [ ] **Step 4: Commit Task 5**

Run:

```powershell
git add README.md
git commit -m "Document output profile options"
```

---

### Task 6: Full Verification

**Files:**
- Verify: `audio_recorder.py`
- Verify: `gui.py`
- Verify: `tests/test_audio_output_profile.py`
- Verify: `tests/test_gui_hotkeys.py`
- Verify: `README.md`

- [ ] **Step 1: Run all unit tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: PASS for all tests in `tests/test_audio_output_profile.py` and `tests/test_gui_hotkeys.py`.

- [ ] **Step 2: Verify `soundfile` FLAC support in the active venv**

Run:

```powershell
.\.venv\Scripts\python.exe -c "import soundfile as sf; print(sf.available_formats().get('FLAC')); print(sf.available_subtypes('FLAC'))"
```

Expected output includes:

```text
FLAC (Free Lossless Audio Codec)
{'PCM_S8': 'Signed 8 bit PCM', 'PCM_16': 'Signed 16 bit PCM', 'PCM_24': 'Signed 24 bit PCM'}
```

- [ ] **Step 3: Launch the app for a UI smoke test**

Run:

```powershell
.\.venv\Scripts\python.exe main.py
```

Expected visible behavior:
- Settings window output section contains `Format`, `Quality`, `Stereo`, and `Preview`.
- Default settings show `FLAC`, `Balanced`, unchecked `Keep Stereo`, and `FLAC / 16 kHz / mono / PCM_16`.
- Changing `Format` to `MP3` changes preview encoding to `64 kbps` or `128 kbps`.
- Checking `Keep Stereo` changes preview channel text from `mono` to `stereo`.

- [ ] **Step 4: Manual recording smoke test**

Record three short clips with these settings:

```text
FLAC / Balanced / Keep Stereo off
WAV / High Quality / Keep Stereo on
MP3 / Balanced / Keep Stereo off
```

Expected files:

```text
Recording_YYYYMMDD_HHMMSS.flac
Recording_YYYYMMDD_HHMMSS.wav
Recording_YYYYMMDD_HHMMSS.mp3
```

Expected technical properties:
- FLAC file opens through `soundfile` as `format == "FLAC"`, `samplerate == 16000`, `channels == 1`, `subtype == "PCM_16"`.
- WAV file opens through `soundfile` as `format == "WAV"`, `samplerate == 48000`, `channels == 2`, `subtype == "PCM_24"`.
- MP3 file has `.mp3` extension and is playable in Windows media players.

- [ ] **Step 5: Inspect final diff**

Run:

```powershell
git diff --stat HEAD
git status --short --branch
```

Expected:
- No uncommitted changes after Task 5 commits, unless the manual smoke test created ignored runtime files.
- Branch remains the current feature branch.
