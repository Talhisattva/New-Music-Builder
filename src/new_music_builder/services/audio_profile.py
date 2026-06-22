from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AudioCompressionPreset:
    label: str
    value: float


AUDIO_COMPRESSION_PRESETS: tuple[AudioCompressionPreset, ...] = (
    AudioCompressionPreset("Lowest", 0.20),
    AudioCompressionPreset("Low", 0.35),
    AudioCompressionPreset("Medium", 0.50),
    AudioCompressionPreset("High", 0.65),
    AudioCompressionPreset("Highest", 0.80),
)

DEFAULT_COMPRESSION_QUALITY = 0.50


def snap_compression_quality(value: object) -> float:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        resolved = DEFAULT_COMPRESSION_QUALITY
    nearest = nearest_compression_preset(resolved)
    return nearest.value


def nearest_compression_preset(value: object) -> AudioCompressionPreset:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        resolved = DEFAULT_COMPRESSION_QUALITY
    return min(
        AUDIO_COMPRESSION_PRESETS,
        key=lambda preset: (abs(preset.value - resolved), -preset.value),
    )


def compression_quality_label(value: object) -> str:
    return nearest_compression_preset(value).label


def compression_profile_id(value: object) -> str:
    snapped = snap_compression_quality(value)
    return f"vorbis-cl{int(round(snapped * 100)):02d}"


def compression_bucket_name(sample_rate: object, quality: object) -> str:
    try:
        resolved_rate = int(sample_rate)
    except (TypeError, ValueError):
        resolved_rate = 44100
    return f"{resolved_rate}hz - {compression_quality_label(quality)}"
