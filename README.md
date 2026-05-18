# Quick Audio Recorder

**Quick Audio Recorder** is a minimalist, yet powerful tool for Windows to quickly record audio from your microphone, system audio (loopback), or both simultaneously.  
It sits quietly in your system tray and is always ready with a single click or global hotkey.

<img width="393" height="156" alt="image" src="https://github.com/user-attachments/assets/7e3bfcaf-6f58-4404-b85a-4ba0b6fea085" />

## Features




<img width="575" height="724" alt="image" src="https://github.com/user-attachments/assets/b35131bc-1ff8-41e1-87b5-1e472f9da981" />


-   **Modes:**
    -   🎤 **Microphone:** Record your voice.
    -   🔊 **System Audio:** Record what you hear (Loopback).
    -   🎙️+🔊 **Both:** Record both tracks simultaneously (mixed).
-   **Output Profiles:**
    -   **Format:** Save recordings as WAV, FLAC, or MP3.
    -   **Quality:** Choose Balanced for compact 16 kHz output or High Quality for 48 kHz output.
    -   **Stereo:** Keep stereo channels when needed, or leave it off for mono recordings.
-   **Post-Processing:**
    -   **Auto-Normalize:** Lifts the main voice/body of each source before mixing and limits sharp peaks so brief spikes do not bury the recording.
    -   **Clipboard Integration:** Automatically copies the file (or file path) to your clipboard.
    -   **Clean Workflow:** Option to move the file to a temp folder and copy it, keeping your desktop clean.
-   **Control:**
    -   **Global Hotkeys:** Start/Stop recording from anywhere (e.g., `Ctrl+Alt+R`).
    -   **Tray Icon:** Left-click to toggle recording immediately; right-click to open the recordings folder, settings, or exit.
    -   **Visual Feedback:** Tray icon changes color when recording, and an optional always-on-top floating timer shows recording status with the same right-click menu.

## Installation

1.  Go to the [Releases](https://github.com/lukmay/QuickAudioRecorder/releases) page.
2.  Download `QuickAudioRecorder.exe`.
3.  Run it! (No installation required).

## Usage

1.  **Right-click** the tray icon to open **Settings**.
2.  Select your **Microphone**, **Output Folder**, **Format**, **Quality**, and **Stereo** preference.
3.  Set your **Hotkeys** (optional).
    - Disable **Show floating recording timer** if you do not want the compact always-on-top recording indicator.
4.  **Left-click** the tray icon or use a hotkey to start recording.
5.  Click the tray icon again, use a stop hotkey, or click the floating timer to stop. The floating timer changes state immediately, then hides after 5 seconds; click it again before it hides to open the recordings folder.

## Development

### Requirements
-   Python 3.12+
-   `pip install PyQt6 soundcard soundfile numpy lameenc keyboard`

### Build from Source
To create the standalone executable:
```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name QuickAudioRecorder main.py
```
