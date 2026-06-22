from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import miniaudio
import numpy as np
import soundfile as sf

from new_music_builder.domain.models import PlannedAudioWorkItem
from new_music_builder.services.cancelable_file_copy import copy_file_with_cancel
from new_music_builder.services.export_cancellation import ExportAbortedError


ProgressCallback = Callable[[int, str], None]
CancelCheck = Callable[[], bool]
OGG_BITRATE_MODE = "VARIABLE"
OGG_COMPRESSION_LEVEL = 0.5
OGG_PROFILE_ID = f"vorbis-{OGG_BITRATE_MODE.lower()}-{int(OGG_COMPRESSION_LEVEL * 100):02d}"


def ensure_cached_ogg(
    item: PlannedAudioWorkItem,
    cache_path: Path,
    *,
    emit_progress: ProgressCallback,
    cancel_requested: CancelCheck | None = None,
) -> bool:
    emit_progress = _coalesced_progress_emitter(emit_progress)
    _raise_if_cancelled(cancel_requested)
    if item.action == "copy_ogg":
        _copy_source_to_cache(
            Path(item.source_path),
            cache_path,
            emit_progress=emit_progress,
            cancel_requested=cancel_requested,
        )
        emit_progress(100, "Copied source .ogg.")
        return False
    if item.action != "convert_to_ogg":
        raise RuntimeError(item.reason or "Unsupported audio action.")
    _convert_to_cached_ogg(item, cache_path, emit_progress=emit_progress, cancel_requested=cancel_requested)
    return True


def _copy_source_to_cache(
    source_path: Path,
    cache_path: Path,
    *,
    emit_progress: ProgressCallback,
    cancel_requested: CancelCheck | None = None,
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        emit_progress(100, "Using cached source .ogg.")
        return
    copy_file_with_cancel(
        source_path,
        cache_path,
        cancel_requested=cancel_requested,
        emit_progress=emit_progress,
        progress_message="Caching source .ogg...",
    )


def _convert_to_cached_ogg(
    item: PlannedAudioWorkItem,
    cache_path: Path,
    *,
    emit_progress: ProgressCallback,
    cancel_requested: CancelCheck | None = None,
) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    if cache_path.exists():
        emit_progress(100, "Using cached conversion.")
        return

    _raise_if_cancelled(cancel_requested)
    emit_progress(5, "Decoding source audio...")
    pcm = _decode_audio(Path(item.source_path), target_rate=item.sample_rate, target_channels=2)
    emit_progress(35, "Preparing PCM data...")
    _write_ogg_vorbis(
        cache_path,
        pcm,
        item.sample_rate,
        emit_progress=emit_progress,
        cancel_requested=cancel_requested,
    )


def _decode_audio(source: Path, *, target_rate: int, target_channels: int) -> np.ndarray:
    decode_error: Exception | None = None
    try:
        data, sample_rate = sf.read(str(source), dtype="int16", always_2d=True)
        pcm = np.ascontiguousarray(data.astype(np.int16, copy=False))
    except Exception as exc:
        decode_error = exc
        pcm, sample_rate = _decode_with_miniaudio(
            source,
            target_channels=target_channels,
            soundfile_error=decode_error,
        )

    pcm = _reshape_channels(pcm, target_channels)
    if sample_rate != target_rate:
        pcm = _resample_pcm16(pcm, sample_rate, target_rate)
    if pcm.size == 0:
        raise RuntimeError("Decoded audio is empty.")
    return np.ascontiguousarray(pcm.astype(np.int16, copy=False))


def _decode_with_miniaudio(
    source: Path,
    *,
    target_channels: int,
    soundfile_error: Exception | None = None,
) -> tuple[np.ndarray, int]:
    try:
        decoded = miniaudio.decode_file(
            str(source),
            output_format=miniaudio.SampleFormat.SIGNED16,
        )
    except Exception as exc:
        if soundfile_error is not None:
            raise RuntimeError(
                f"Unable to decode audio. soundfile: {soundfile_error}; miniaudio: {exc}"
            ) from exc
        raise RuntimeError(f"Unable to decode audio with miniaudio: {exc}") from exc

    sample_rate = int(getattr(decoded, "sample_rate", 0) or 0)
    channels = int(getattr(decoded, "nchannels", 0) or 0)
    if sample_rate <= 0 or channels <= 0:
        raise RuntimeError("Decoded audio metadata is invalid.")

    pcm = np.frombuffer(decoded.samples, dtype=np.int16).copy()
    if pcm.size == 0:
        raise RuntimeError("Decoded audio is empty.")
    pcm = pcm.reshape(-1, channels)
    return _reshape_channels(pcm, target_channels), sample_rate


def _reshape_channels(data: np.ndarray, target_channels: int) -> np.ndarray:
    if data.ndim == 1:
        data = data.reshape(-1, 1)
    current_channels = data.shape[1]
    if current_channels == target_channels:
        return data
    if current_channels == 1 and target_channels == 2:
        return np.repeat(data, 2, axis=1)
    if current_channels >= 2 and target_channels == 1:
        mixed = np.mean(data[:, :2].astype(np.float32), axis=1, keepdims=True)
        return np.clip(mixed, -32768, 32767).astype(np.int16)
    trimmed = data[:, :target_channels]
    if trimmed.shape[1] == target_channels:
        return trimmed
    pad = np.zeros((trimmed.shape[0], target_channels - trimmed.shape[1]), dtype=np.int16)
    return np.concatenate([trimmed, pad], axis=1)


def _resample_pcm16(data: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or data.size == 0:
        return data
    frames = data.shape[0]
    channels = data.shape[1]
    out_frames = max(1, int(round(frames * (dst_rate / src_rate))))
    x_old = np.linspace(0.0, 1.0, num=frames, endpoint=False)
    x_new = np.linspace(0.0, 1.0, num=out_frames, endpoint=False)
    out = np.empty((out_frames, channels), dtype=np.float32)
    for channel_index in range(channels):
        out[:, channel_index] = np.interp(x_new, x_old, data[:, channel_index].astype(np.float32))
    return np.clip(out, -32768, 32767).astype(np.int16)


def _write_ogg_vorbis(
    target: Path,
    pcm: np.ndarray,
    sample_rate: int,
    *,
    emit_progress: ProgressCallback,
    cancel_requested: CancelCheck | None = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    total_frames = max(1, pcm.shape[0])
    frame_step = 16384
    try:
        with sf.SoundFile(
            str(target),
            mode="w",
            samplerate=sample_rate,
            channels=2,
            format="OGG",
            subtype="VORBIS",
            compression_level=OGG_COMPRESSION_LEVEL,
            bitrate_mode=OGG_BITRATE_MODE,
        ) as out_sf:
            for frame_index in range(0, pcm.shape[0], frame_step):
                _raise_if_cancelled(cancel_requested)
                chunk = np.ascontiguousarray(pcm[frame_index : frame_index + frame_step], dtype=np.int16)
                out_sf.buffer_write(chunk.tobytes(), dtype="int16")
                written_frames = min(total_frames, frame_index + chunk.shape[0])
                percent = 35 + int(round((written_frames / total_frames) * 65))
                emit_progress(min(100, max(35, percent)), "Converting song...")
    except ExportAbortedError:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    emit_progress(100, "Conversion complete.")


def _raise_if_cancelled(cancel_requested: CancelCheck | None) -> None:
    if cancel_requested is not None and cancel_requested():
        raise ExportAbortedError("Build aborted by user.")


def _coalesced_progress_emitter(emit_progress: ProgressCallback) -> ProgressCallback:
    last_percent = -1
    last_message = ""

    def _emit(percent: int, message: str) -> None:
        nonlocal last_percent, last_message
        if percent == last_percent and message == last_message:
            return
        last_percent = percent
        last_message = message
        emit_progress(percent, message)

    return _emit
