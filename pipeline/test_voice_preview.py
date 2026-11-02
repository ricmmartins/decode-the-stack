import unittest

from pydub import AudioSegment
from pydub.generators import Sine

from create_voice_preview import TURNS, prepare_turn


class VoicePreviewTests(unittest.TestCase):
    def test_padding_is_reduced_without_cutting_voiced_audio(self):
        tone = Sine(440).to_audio_segment(duration=1000).apply_gain(-10)
        audio = AudioSegment.silent(duration=200) + tone + AudioSegment.silent(duration=850)
        result = prepare_turn(audio)
        self.assertAlmostEqual(len(result), 1300, delta=20)
        self.assertGreater(result[120:1120].rms, 0)
        self.assertLessEqual(result.max_dBFS, -0.99)

    def test_empty_or_silent_turn_is_rejected(self):
        for audio in (AudioSegment.empty(), AudioSegment.silent(duration=100)):
            with self.assertRaises(ValueError):
                prepare_turn(audio)

    def test_preview_keeps_all_three_original_hosts(self):
        self.assertEqual({host for host, _ in TURNS}, {"Anna", "Maria", "Pedro"})
        self.assertEqual(len(TURNS), 6)
