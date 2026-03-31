import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave

from voxa_metrics import (
    AnalysisConfig,
    analyze_audio_file,
    analyze_signal,
    build_metric_pipeline,
    compute_corpus_statistics,
)


class MetricsTest(unittest.TestCase):
    def test_constant_tone_metrics(self) -> None:
        sample_rate = 1000
        signal = [0.5] * sample_rate

        metrics = analyze_signal(
            signal,
            sample_rate,
            config=AnalysisConfig(
                vad_threshold_dbfs=-20.0,
                ltass_window_ms=100.0,
                ltass_hop_ms=50.0,
                ltass_use_active_speech=False,
                ltass_bands_hz=(125.0, 250.0),
            ),
        )

        self.assertAlmostEqual(metrics.duration_s, 1.0, places=6)
        self.assertAlmostEqual(metrics.rms_dbfs, -6.0206, places=3)
        self.assertAlmostEqual(metrics.peak_dbfs, -6.0206, places=3)
        self.assertAlmostEqual(metrics.crest_factor_db, 0.0, places=3)
        self.assertGreater(metrics.speech_activity_ratio, 0.9)
        self.assertTrue(math.isfinite(metrics.integrated_lufs))
        self.assertEqual(len(metrics.ltass.band_hz), 2)

    def test_activity_detection_with_leading_silence(self) -> None:
        sample_rate = 1000
        signal = [0.0] * 500 + [0.5] * 500

        metrics = analyze_signal(
            signal,
            sample_rate,
            config=AnalysisConfig(
                vad_frame_ms=100.0,
                vad_hop_ms=100.0,
                vad_threshold_dbfs=-20.0,
                ltass_window_ms=100.0,
                ltass_hop_ms=100.0,
                ltass_use_active_speech=False,
            ),
        )

        self.assertAlmostEqual(metrics.speech_activity_ratio, 0.5, places=2)
        self.assertAlmostEqual(metrics.active_speech_rms_dbfs, -6.0206, places=2)
        self.assertLess(metrics.rms_dbfs, metrics.active_speech_rms_dbfs)

    def test_corpus_statistics(self) -> None:
        sample_rate = 1000
        metric_a = analyze_signal([0.5] * sample_rate, sample_rate, config=AnalysisConfig(vad_threshold_dbfs=-20.0))
        metric_b = analyze_signal([0.25] * sample_rate, sample_rate, config=AnalysisConfig(vad_threshold_dbfs=-20.0))

        corpus = compute_corpus_statistics(
            [metric_a, metric_b],
            include_ltass=False,
            overall_rms_dbfs=-7.9588,
        )

        self.assertEqual(corpus.sample_count, 2)
        self.assertAlmostEqual(corpus.total_duration_s, 2.0, places=6)
        self.assertLess(corpus.rms_dbfs.min, corpus.rms_dbfs.max)
        self.assertLessEqual(corpus.duration.p10, corpus.duration.p90)
        self.assertAlmostEqual(corpus.to_voxa_dict()["overall_rms_dbfs"], -7.9588, places=4)

    def test_build_metric_pipeline_payload(self) -> None:
        pipeline = build_metric_pipeline(
            AnalysisConfig(
                vad_frame_ms=25.0,
                vad_hop_ms=5.0,
                ltass_bands_hz=(125.0, 500.0, 1000.0),
                ltass_use_active_speech=False,
            )
        ).to_voxa_dict()

        self.assertEqual(pipeline["implementation"], "voxa_metrics")
        self.assertEqual(pipeline["version"], "0.1.0")
        self.assertEqual(pipeline["parameters"]["vad"]["frame_ms"], 25.0)
        self.assertEqual(pipeline["parameters"]["vad"]["hop_ms"], 5.0)
        self.assertEqual(pipeline["parameters"]["ltass"]["bands_hz"], [125.0, 500.0, 1000.0])
        self.assertFalse(pipeline["parameters"]["ltass"]["use_active_speech"])

    def test_analyze_audio_file_uses_ffmpeg_for_mp3(self) -> None:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            self.skipTest("ffmpeg is required for compressed container decoding")

        with tempfile.TemporaryDirectory() as tmpdir:
            wav_path = Path(tmpdir) / "sample.wav"
            mp3_path = Path(tmpdir) / "sample.mp3"
            self._write_wav(wav_path, [0.5] * 1000, sample_rate=1000)

            subprocess.run(
                [ffmpeg, "-v", "error", "-y", "-i", os.fspath(wav_path), os.fspath(mp3_path)],
                check=True,
                capture_output=True,
            )

            metrics = analyze_audio_file(
                mp3_path,
                config=AnalysisConfig(
                    vad_threshold_dbfs=-20.0,
                    ltass_window_ms=100.0,
                    ltass_hop_ms=50.0,
                    ltass_use_active_speech=False,
                ),
            )
            self.assertAlmostEqual(metrics.duration_s, 1.0, places=2)
            self.assertTrue(math.isfinite(metrics.rms_dbfs))

    def _write_wav(self, path: Path, samples: list[float], sample_rate: int) -> None:
        with wave.open(os.fspath(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            frames = b"".join(struct.pack("<h", max(-32768, min(32767, round(sample * 32767)))) for sample in samples)
            wav_file.writeframes(frames)


if __name__ == "__main__":
    unittest.main()
