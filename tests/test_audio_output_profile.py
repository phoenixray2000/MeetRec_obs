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
        self.assertEqual(FORMAT_CONFIG["wav"]["label"], "WAV")
        self.assertEqual(FORMAT_CONFIG["wav"]["extension"], ".wav")
        self.assertEqual(FORMAT_CONFIG["wav"]["encoder"], "soundfile")
        self.assertEqual(FORMAT_CONFIG["wav"]["format"], "WAV")
        self.assertEqual(FORMAT_CONFIG["flac"]["label"], "FLAC")
        self.assertEqual(FORMAT_CONFIG["flac"]["extension"], ".flac")
        self.assertEqual(FORMAT_CONFIG["flac"]["encoder"], "soundfile")
        self.assertEqual(FORMAT_CONFIG["flac"]["format"], "FLAC")
        self.assertEqual(FORMAT_CONFIG["mp3"]["label"], "MP3")
        self.assertEqual(FORMAT_CONFIG["mp3"]["extension"], ".mp3")
        self.assertEqual(FORMAT_CONFIG["mp3"]["encoder"], "lameenc")

    def test_quality_config_matches_required_mapping(self):
        self.assertEqual(set(QUALITY_CONFIG), {"balanced", "high"})
        self.assertEqual(QUALITY_CONFIG["balanced"]["label"], "Balanced")
        self.assertEqual(QUALITY_CONFIG["balanced"]["sample_rate"], 16000)
        self.assertEqual(QUALITY_CONFIG["balanced"]["subtype"], "PCM_16")
        self.assertEqual(QUALITY_CONFIG["balanced"]["mp3_bitrate_kbps"], 64)
        self.assertEqual(QUALITY_CONFIG["high"]["label"], "High Quality")
        self.assertEqual(QUALITY_CONFIG["high"]["sample_rate"], 48000)
        self.assertEqual(QUALITY_CONFIG["high"]["subtype"], "PCM_24")
        self.assertEqual(QUALITY_CONFIG["high"]["mp3_bitrate_kbps"], 128)

    def test_build_output_profile_applies_mono_channels(self):
        profile = build_output_profile(" FLAC ", " BALANCED ", stereo=False)

        self.assertEqual(profile["label"], "FLAC")
        self.assertEqual(profile["format_label"], "FLAC")
        self.assertEqual(profile["quality_label"], "Balanced")
        self.assertEqual(profile["extension"], ".flac")
        self.assertEqual(profile["sample_rate"], 16000)
        self.assertEqual(profile["subtype"], "PCM_16")
        self.assertEqual(profile["channels"], 1)
        self.assertEqual(profile["format_key"], "flac")
        self.assertEqual(profile["quality_key"], "balanced")

    def test_build_output_profile_applies_stereo_channels(self):
        profile = build_output_profile("mp3", "high", stereo=True)

        self.assertEqual(profile["label"], "MP3")
        self.assertEqual(profile["format_label"], "MP3")
        self.assertEqual(profile["quality_label"], "High Quality")
        self.assertEqual(profile["sample_rate"], 48000)
        self.assertEqual(profile["mp3_bitrate_kbps"], 128)
        self.assertEqual(profile["channels"], 2)
        self.assertEqual(profile["format_key"], "mp3")
        self.assertEqual(profile["quality_key"], "high")
        self.assertNotIn("format", profile)

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
