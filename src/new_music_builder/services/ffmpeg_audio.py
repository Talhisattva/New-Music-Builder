from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path
import re
import subprocess

import numpy as np

from new_music_builder.platform.binaries import locate_binary
from new_music_builder.platform.paths import resource_root, runtime_root

try:
    import imageio_ffmpeg
except ImportError:  # Allows an existing source environment to use ffmpeg from PATH.
    imageio_ffmpeg = None  # type: ignore[assignment]


_DURATION_PATTERN = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2}(?:\.\d+)?)")


@lru_cache(maxsize=1)
def ffmpeg_executable() -> str | None:
    """Return a bundled, Python-package, or system ffmpeg executable."""
    bundled_dirs = (
        resource_root() / "bin",
        runtime_root() / "bin",
        resource_root(),
        runtime_root(),
    )
    for bundled_dir in bundled_dirs:
        for binary_name in ("ffmpeg", "ffmpeg.exe"):
            bundled = bundled_dir / binary_name
            if bundled.is_file():
                return str(bundled)

    if imageio_ffmpeg is not None:
        try:
            resolved = str(imageio_ffmpeg.get_ffmpeg_exe()).strip()
            if resolved and Path(resolved).is_file():
                return resolved
        except Exception:
            pass

    return locate_binary("ffmpeg")


def probe_audio_duration(source: str | Path) -> float:
    """Read container duration with ffmpeg, returning zero when it is unavailable."""
    executable = ffmpeg_executable()
    if executable is None:
        return 0.0

    completed = subprocess.run(
        [executable, "-hide_banner", "-nostdin", "-i", str(source)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_creation_flags(),
    )
    match = _DURATION_PATTERN.search(completed.stderr or "")
    if match is None:
        return 0.0
    hours, minutes, seconds = match.groups()
    return (int(hours) * 3600.0) + (int(minutes) * 60.0) + float(seconds)


def decode_audio_to_pcm(
    source: str | Path,
    *,
    target_rate: int,
    target_channels: int,
) -> tuple[np.ndarray, int]:
    """Decode the first audio stream to interleaved float32 PCM with ffmpeg."""
    executable = ffmpeg_executable()
    if executable is None:
        raise RuntimeError(
            "This audio format requires FFmpeg. Reinstall New Music Builder or install ffmpeg and add it to PATH."
        )

    completed = subprocess.run(
        [
            executable,
            "-v",
            "error",
            "-nostdin",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-sn",
            "-dn",
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-ac",
            str(target_channels),
            "-ar",
            str(target_rate),
            "pipe:1",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        creationflags=_creation_flags(),
    )
    if completed.returncode != 0:
        details = completed.stderr.decode("utf-8", errors="replace").strip()
        if not details:
            details = f"FFmpeg exited with status {completed.returncode}."
        raise RuntimeError(f"Unable to decode audio with FFmpeg: {details}")

    pcm = np.frombuffer(completed.stdout, dtype="<f4")
    if pcm.size == 0:
        raise RuntimeError("FFmpeg decoded no audio samples.")
    if pcm.size % target_channels != 0:
        raise RuntimeError("FFmpeg returned incomplete audio samples.")
    return np.ascontiguousarray(pcm.reshape(-1, target_channels)), target_rate


def _creation_flags() -> int:
    if os.name == "nt":
        return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return 0
