"""Pure Python metric computation for the Voxa specification.

This module intentionally avoids third-party dependencies. It supports:

- PCM WAV loading
- sample-level metrics
- corpus-level summary statistics
- LTASS estimation

The loudness metrics use a documented BS.1770-style gating workflow without the
full K-weighting filter. This keeps the implementation dependency-free while
remaining deterministic and reproducible.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import math
import os
import shutil
import statistics
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Callable, Iterable, Sequence


EPSILON = 1e-12
DEFAULT_LTASS_BANDS = (125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0)
PACKAGE_VERSION = "0.1.0"
IMPLEMENTATION_NAME = "voxa_metrics"
IMPLEMENTATION_LABEL = f"pure-python {IMPLEMENTATION_NAME}/{PACKAGE_VERSION}"
AudioDecoder = Callable[[str | Path], tuple[list[list[float]], int]]
_DECODERS: dict[str, AudioDecoder] = {}


@dataclass(slots=True)
class AnalysisConfig:
    vad_frame_ms: float = 30.0
    vad_hop_ms: float = 10.0
    vad_threshold_dbfs: float = -40.0
    loudness_gate_block_ms: float = 400.0
    loudness_gate_hop_ms: float = 100.0
    loudness_absolute_gate_lufs: float = -70.0
    loudness_relative_gate_lu: float = -10.0
    lra_window_ms: float = 3000.0
    lra_hop_ms: float = 1000.0
    lra_relative_gate_lu: float = -20.0
    ltass_window_ms: float = 25.0
    ltass_hop_ms: float = 10.0
    ltass_bands_hz: tuple[float, ...] = DEFAULT_LTASS_BANDS
    ltass_use_active_speech: bool = True


@dataclass(slots=True)
class MetricSummary:
    mean: float
    std: float
    min: float
    max: float
    p10: float
    p50: float
    p90: float


@dataclass(slots=True)
class LTASSResult:
    method: str
    band_hz: list[float]
    level_db: list[float]


@dataclass(slots=True)
class MetricPipeline:
    implementation: str = IMPLEMENTATION_NAME
    version: str = PACKAGE_VERSION
    parameters: dict[str, object] = field(default_factory=dict)

    def to_voxa_dict(self) -> dict[str, object]:
        return {
            "implementation": self.implementation,
            "version": self.version,
            "parameters": _json_ready(self.parameters),
        }


@dataclass(slots=True)
class SampleMetrics:
    duration_s: float
    rms_dbfs: float
    integrated_lufs: float
    active_speech_rms_dbfs: float
    peak_dbfs: float
    crest_factor_db: float
    speech_activity_ratio: float
    loudness_range_lu: float
    ltass: LTASSResult | None = None
    implementation: str = IMPLEMENTATION_LABEL

    def to_voxa_dict(self, include_ltass: bool = False) -> dict[str, object]:
        metrics = {
            "rms_dbfs": self.rms_dbfs,
            "integrated_lufs": self.integrated_lufs,
            "active_speech_rms_dbfs": self.active_speech_rms_dbfs,
            "peak_dbfs": self.peak_dbfs,
            "crest_factor_db": self.crest_factor_db,
            "speech_activity_ratio": self.speech_activity_ratio,
            "loudness_range_lu": self.loudness_range_lu,
        }
        if include_ltass and self.ltass is not None:
            metrics["ltass"] = asdict(self.ltass)
        return metrics


@dataclass(slots=True)
class CorpusStatistics:
    sample_count: int
    total_duration_s: float
    duration: MetricSummary
    rms_dbfs: MetricSummary
    integrated_lufs: MetricSummary
    overall_rms_dbfs: float | None = None
    active_speech_rms_dbfs: MetricSummary | None = None
    crest_factor_db: MetricSummary | None = None
    peak_dbfs: MetricSummary | None = None
    speech_activity_ratio: MetricSummary | None = None
    loudness_range_lu: MetricSummary | None = None
    ltass: LTASSResult | None = None

    def to_voxa_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "sample_count": self.sample_count,
            "total_duration_s": self.total_duration_s,
            "duration": asdict(self.duration),
            "rms_dbfs": asdict(self.rms_dbfs),
            "integrated_lufs": asdict(self.integrated_lufs),
        }
        if self.overall_rms_dbfs is not None:
            payload["overall_rms_dbfs"] = self.overall_rms_dbfs
        optional = {
            "active_speech_rms_dbfs": self.active_speech_rms_dbfs,
            "crest_factor_db": self.crest_factor_db,
            "peak_dbfs": self.peak_dbfs,
            "speech_activity_ratio": self.speech_activity_ratio,
            "loudness_range_lu": self.loudness_range_lu,
        }
        for key, value in optional.items():
            if value is not None:
                payload[key] = asdict(value)
        if self.ltass is not None:
            payload["ltass"] = asdict(self.ltass)
        return payload


def build_metric_pipeline(config: AnalysisConfig | None = None) -> MetricPipeline:
    cfg = config or AnalysisConfig()
    return MetricPipeline(
        parameters={
            "vad": {
                "frame_ms": cfg.vad_frame_ms,
                "hop_ms": cfg.vad_hop_ms,
                "threshold_dbfs": cfg.vad_threshold_dbfs,
            },
            "loudness": {
                "method": "BS.1770-style gating without K-weighting",
                "block_ms": cfg.loudness_gate_block_ms,
                "hop_ms": cfg.loudness_gate_hop_ms,
                "absolute_gate_lufs": cfg.loudness_absolute_gate_lufs,
                "relative_gate_lu": cfg.loudness_relative_gate_lu,
            },
            "loudness_range": {
                "window_ms": cfg.lra_window_ms,
                "hop_ms": cfg.lra_hop_ms,
                "relative_gate_lu": cfg.lra_relative_gate_lu,
            },
            "ltass": {
                "window_ms": cfg.ltass_window_ms,
                "hop_ms": cfg.ltass_hop_ms,
                "bands_hz": list(cfg.ltass_bands_hz),
                "use_active_speech": cfg.ltass_use_active_speech,
            },
        }
    )


def load_wav(path: str | Path) -> tuple[list[list[float]], int]:
    """Load an integer PCM WAV file as channel-major floats in [-1, 1]."""

    with wave.open(str(path), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        channel_count = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_count = wav_file.getnframes()
        frames = wav_file.readframes(frame_count)

    if sample_width not in (1, 2, 3, 4):
        raise ValueError(f"unsupported PCM sample width: {sample_width}")

    channels = [[] for _ in range(channel_count)]
    step = sample_width * channel_count
    max_int = float(2 ** (sample_width * 8 - 1))

    for offset in range(0, len(frames), step):
        frame = frames[offset : offset + step]
        for channel in range(channel_count):
            start = channel * sample_width
            raw = frame[start : start + sample_width]
            if sample_width == 1:
                value = (raw[0] - 128) / 128.0
            elif sample_width == 3:
                extended = raw + (b"\xff" if raw[-1] & 0x80 else b"\x00")
                value = int.from_bytes(extended, "little", signed=True) / max_int
            else:
                value = int.from_bytes(raw, "little", signed=True) / max_int
            channels[channel].append(max(-1.0, min(1.0, value)))

    return channels, sample_rate


def register_decoder(extension: str, decoder: AudioDecoder) -> None:
    normalized = extension.lower().lstrip(".")
    if not normalized:
        raise ValueError("extension must not be empty")
    _DECODERS[normalized] = decoder


def load_audio(
    path: str | Path,
    decoder: AudioDecoder | None = None,
    allow_ffmpeg: bool = True,
) -> tuple[list[list[float]], int]:
    source = Path(path)
    if decoder is not None:
        return decoder(source)

    extension = source.suffix.lower().lstrip(".")
    if extension in _DECODERS:
        return _DECODERS[extension](source)
    if allow_ffmpeg:
        return _load_with_ffmpeg(source)
    raise ValueError(f"no decoder registered for {source.suffix or '<no extension>'}")


def analyze_audio_file(
    path: str | Path,
    config: AnalysisConfig | None = None,
    decoder: AudioDecoder | None = None,
    allow_ffmpeg: bool = True,
) -> SampleMetrics:
    channels, sample_rate = load_audio(path, decoder=decoder, allow_ffmpeg=allow_ffmpeg)
    return analyze_signal(channels, sample_rate, config=config)


def analyze_wav(path: str | Path, config: AnalysisConfig | None = None) -> SampleMetrics:
    channels, sample_rate = load_wav(path)
    return analyze_signal(channels, sample_rate, config=config)


def analyze_signal(
    samples: Sequence[float] | Sequence[Sequence[float]],
    sample_rate: int,
    config: AnalysisConfig | None = None,
) -> SampleMetrics:
    cfg = config or AnalysisConfig()
    channels = _normalize_channels(samples)
    if not channels or not channels[0]:
        raise ValueError("signal must contain at least one sample")

    duration_s = len(channels[0]) / float(sample_rate)
    rms_dbfs = _rms_dbfs(channels)
    peak_dbfs = _peak_dbfs(channels)
    crest_factor_db = peak_dbfs - rms_dbfs if math.isfinite(rms_dbfs) else math.inf

    activity_mask = _speech_activity_mask(channels, sample_rate, cfg)
    active_speech_rms_dbfs = _masked_rms_dbfs(channels, activity_mask)
    speech_activity_ratio = (
        sum(1 for active in activity_mask if active) / len(activity_mask) if activity_mask else 0.0
    )

    integrated_lufs = _integrated_lufs(channels, sample_rate, cfg)
    loudness_range_lu = _loudness_range(channels, sample_rate, cfg)
    ltass = _ltass(channels, sample_rate, cfg, activity_mask)

    return SampleMetrics(
        duration_s=duration_s,
        rms_dbfs=rms_dbfs,
        integrated_lufs=integrated_lufs,
        active_speech_rms_dbfs=active_speech_rms_dbfs,
        peak_dbfs=peak_dbfs,
        crest_factor_db=crest_factor_db,
        speech_activity_ratio=speech_activity_ratio,
        loudness_range_lu=loudness_range_lu,
        ltass=ltass,
    )


def compute_corpus_statistics(
    sample_metrics: Iterable[SampleMetrics],
    include_ltass: bool = True,
    overall_rms_dbfs: float | None = None,
) -> CorpusStatistics:
    metrics = list(sample_metrics)
    if not metrics:
        raise ValueError("sample_metrics must not be empty")

    ltass = _aggregate_ltass([item.ltass for item in metrics if item.ltass is not None]) if include_ltass else None
    return CorpusStatistics(
        sample_count=len(metrics),
        total_duration_s=sum(item.duration_s for item in metrics),
        duration=_summary([item.duration_s for item in metrics]),
        rms_dbfs=_summary([item.rms_dbfs for item in metrics]),
        overall_rms_dbfs=overall_rms_dbfs,
        integrated_lufs=_summary([item.integrated_lufs for item in metrics]),
        active_speech_rms_dbfs=_summary_optional([item.active_speech_rms_dbfs for item in metrics]),
        crest_factor_db=_summary_optional([item.crest_factor_db for item in metrics]),
        peak_dbfs=_summary_optional([item.peak_dbfs for item in metrics]),
        speech_activity_ratio=_summary_optional([item.speech_activity_ratio for item in metrics]),
        loudness_range_lu=_summary_optional([item.loudness_range_lu for item in metrics]),
        ltass=ltass,
    )


def _normalize_channels(samples: Sequence[float] | Sequence[Sequence[float]]) -> list[list[float]]:
    if not samples:
        return []
    first = samples[0]  # type: ignore[index]
    if isinstance(first, (int, float)):
        return [[float(value) for value in samples]]  # type: ignore[arg-type]

    channels = [[float(value) for value in channel] for channel in samples]  # type: ignore[arg-type]
    lengths = {len(channel) for channel in channels}
    if len(lengths) != 1:
        raise ValueError("all channels must have the same number of samples")
    return channels


def _json_ready(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


def _db(value: float) -> float:
    if value <= EPSILON:
        return float("-inf")
    return 20.0 * math.log10(value)


def _power_db(value: float) -> float:
    if value <= EPSILON:
        return float("-inf")
    return 10.0 * math.log10(value)


def _rms_dbfs(channels: Sequence[Sequence[float]]) -> float:
    total = 0.0
    count = 0
    for channel in channels:
        for sample in channel:
            total += sample * sample
            count += 1
    rms = math.sqrt(total / max(count, 1))
    return _db(rms)


def _masked_rms_dbfs(channels: Sequence[Sequence[float]], mask: Sequence[bool]) -> float:
    total = 0.0
    count = 0
    for channel in channels:
        for sample, active in zip(channel, mask):
            if active:
                total += sample * sample
                count += 1
    if count == 0:
        return float("-inf")
    return _db(math.sqrt(total / count))


def _peak_dbfs(channels: Sequence[Sequence[float]]) -> float:
    peak = max(abs(sample) for channel in channels for sample in channel)
    return _db(peak)


def _speech_activity_mask(
    channels: Sequence[Sequence[float]], sample_rate: int, config: AnalysisConfig
) -> list[bool]:
    sample_count = len(channels[0])
    frame_size = max(1, round(sample_rate * config.vad_frame_ms / 1000.0))
    hop_size = max(1, round(sample_rate * config.vad_hop_ms / 1000.0))
    mask = [False] * sample_count

    for start in range(0, sample_count, hop_size):
        end = min(sample_count, start + frame_size)
        if start >= end:
            break
        frame_rms = _frame_rms(channels, start, end)
        if _db(frame_rms) >= config.vad_threshold_dbfs:
            for idx in range(start, end):
                mask[idx] = True
    return mask


def _frame_rms(channels: Sequence[Sequence[float]], start: int, end: int) -> float:
    total = 0.0
    count = 0
    for channel in channels:
        for sample in channel[start:end]:
            total += sample * sample
            count += 1
    return math.sqrt(total / max(count, 1))


def _integrated_lufs(
    channels: Sequence[Sequence[float]], sample_rate: int, config: AnalysisConfig
) -> float:
    blocks = _block_loudness(
        channels,
        sample_rate,
        window_ms=config.loudness_gate_block_ms,
        hop_ms=config.loudness_gate_hop_ms,
    )
    if not blocks:
        return float("-inf")

    gated = [block for block in blocks if block >= config.loudness_absolute_gate_lufs]
    if not gated:
        return float("-inf")

    preliminary = _mean(gated)
    relative_gate = preliminary + config.loudness_relative_gate_lu
    final_blocks = [block for block in gated if block >= relative_gate]
    if not final_blocks:
        return preliminary
    return _mean(final_blocks)


def _loudness_range(
    channels: Sequence[Sequence[float]], sample_rate: int, config: AnalysisConfig
) -> float:
    short_term = _block_loudness(
        channels,
        sample_rate,
        window_ms=config.lra_window_ms,
        hop_ms=config.lra_hop_ms,
    )
    if not short_term:
        return 0.0

    gated = [value for value in short_term if value >= config.loudness_absolute_gate_lufs]
    if not gated:
        return 0.0

    relative_gate = _mean(gated) + config.lra_relative_gate_lu
    final = [value for value in gated if value >= relative_gate]
    if len(final) < 2:
        return 0.0
    return _percentile(final, 95.0) - _percentile(final, 10.0)


def _block_loudness(
    channels: Sequence[Sequence[float]], sample_rate: int, window_ms: float, hop_ms: float
) -> list[float]:
    sample_count = len(channels[0])
    window_size = max(1, round(sample_rate * window_ms / 1000.0))
    hop_size = max(1, round(sample_rate * hop_ms / 1000.0))
    results: list[float] = []

    for start in range(0, sample_count, hop_size):
        end = min(sample_count, start + window_size)
        if end - start < max(1, window_size // 2):
            continue
        mean_square = 0.0
        for channel in channels:
            block = channel[start:end]
            mean_square += sum(sample * sample for sample in block) / len(block)
        mean_square /= len(channels)
        results.append(-0.691 + _power_db(mean_square))
    return results


def _ltass(
    channels: Sequence[Sequence[float]],
    sample_rate: int,
    config: AnalysisConfig,
    activity_mask: Sequence[bool],
) -> LTASSResult:
    window_size = max(8, round(sample_rate * config.ltass_window_ms / 1000.0))
    hop_size = max(1, round(sample_rate * config.ltass_hop_ms / 1000.0))
    frequencies = [sample_rate * idx / window_size for idx in range(window_size // 2 + 1)]
    spectrum = [0.0] * len(frequencies)
    frame_count = 0
    mono = _mixdown(channels)
    hamming = [0.54 - 0.46 * math.cos((2.0 * math.pi * n) / (window_size - 1)) for n in range(window_size)]

    for start in range(0, len(mono) - window_size + 1, hop_size):
        end = start + window_size
        if config.ltass_use_active_speech and activity_mask and not any(activity_mask[start:end]):
            continue
        windowed = [mono[start + idx] * hamming[idx] for idx in range(window_size)]
        power = _rfft_power(windowed)
        for idx, value in enumerate(power):
            spectrum[idx] += value
        frame_count += 1

    if frame_count == 0:
        levels = [float("-inf")] * len(config.ltass_bands_hz)
        method = "1/3-octave average over active-speech frames (no active frames detected)"
        return LTASSResult(method=method, band_hz=list(config.ltass_bands_hz), level_db=levels)

    average = [value / frame_count for value in spectrum]
    levels = []
    for center in config.ltass_bands_hz:
        lower = center / (2.0 ** (1.0 / 6.0))
        upper = center * (2.0 ** (1.0 / 6.0))
        band_values = [
            power
            for frequency, power in zip(frequencies, average)
            if lower <= frequency < upper
        ]
        levels.append(_power_db(_mean(band_values)) if band_values else float("-inf"))

    method = "1/3-octave average over active-speech frames" if config.ltass_use_active_speech else "1/3-octave average over all frames"
    return LTASSResult(method=method, band_hz=list(config.ltass_bands_hz), level_db=levels)


def _rfft_power(signal: Sequence[float]) -> list[float]:
    size = len(signal)
    limit = size // 2 + 1
    result: list[float] = []
    for k in range(limit):
        real = 0.0
        imag = 0.0
        for n, sample in enumerate(signal):
            angle = 2.0 * math.pi * k * n / size
            real += sample * math.cos(angle)
            imag -= sample * math.sin(angle)
        result.append((real * real + imag * imag) / size)
    return result


def _mixdown(channels: Sequence[Sequence[float]]) -> list[float]:
    sample_count = len(channels[0])
    return [sum(channel[idx] for channel in channels) / len(channels) for idx in range(sample_count)]


def _aggregate_ltass(items: Sequence[LTASSResult]) -> LTASSResult | None:
    if not items:
        return None
    bands = items[0].band_hz
    levels: list[float] = []
    for idx in range(len(bands)):
        values = [item.level_db[idx] for item in items if math.isfinite(item.level_db[idx])]
        levels.append(_mean(values) if values else float("-inf"))
    return LTASSResult(method="mean of per-sample LTASS levels", band_hz=list(bands), level_db=levels)


def _summary(values: Sequence[float]) -> MetricSummary:
    filtered = [value for value in values if math.isfinite(value)]
    if not filtered:
        raise ValueError("summary requires at least one finite value")
    return MetricSummary(
        mean=_mean(filtered),
        std=statistics.pstdev(filtered) if len(filtered) > 1 else 0.0,
        min=min(filtered),
        max=max(filtered),
        p10=_percentile(filtered, 10.0),
        p50=_percentile(filtered, 50.0),
        p90=_percentile(filtered, 90.0),
    )


def _summary_optional(values: Sequence[float]) -> MetricSummary | None:
    filtered = [value for value in values if math.isfinite(value)]
    return _summary(filtered) if filtered else None


def _mean(values: Sequence[float]) -> float:
    if not values:
        return float("-inf")
    return sum(values) / len(values)


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (percentile / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _load_with_ffmpeg(path: Path) -> tuple[list[list[float]], int]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise ValueError(f"no decoder registered for {path.suffix or '<no extension>'} and ffmpeg is unavailable")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        temp_path = Path(handle.name)

    try:
        command = [
            ffmpeg,
            "-v",
            "error",
            "-y",
            "-i",
            os.fspath(path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            os.fspath(temp_path),
        ]
        subprocess.run(command, check=True, capture_output=True)
        return load_wav(temp_path)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"ffmpeg failed to decode {path}: {stderr}") from exc
    finally:
        temp_path.unlink(missing_ok=True)


register_decoder("wav", load_wav)
