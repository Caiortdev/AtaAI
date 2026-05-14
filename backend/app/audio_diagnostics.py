"""Audio quality diagnostics for pre-transcription assessment.

Analyzes audio files to detect issues that could impact transcription accuracy.
All functions require FFmpeg to extract raw PCM samples for analysis.
"""

import re
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import numpy as np


class AudioQuality(StrEnum):
    good = "good"
    moderate = "moderate"
    poor = "poor"
    unusable = "unusable"


@dataclass
class AudioDiagnostics:
    snr_db: float = 0.0
    clip_ratio: float = 0.0
    speech_ratio: float = 0.0
    mean_volume_db: float = 0.0
    quality: AudioQuality = AudioQuality.good
    recommendations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def assess_audio_quality(audio_path: Path, ffmpeg: str = "ffmpeg") -> AudioDiagnostics:
    """Run full audio quality assessment. Returns diagnostics with quality grade."""
    samples = _extract_pcm_samples(audio_path, ffmpeg)
    if samples is None or len(samples) == 0:
        return AudioDiagnostics(
            quality=AudioQuality.unusable,
            warnings=["Nao foi possivel analisar o audio."],
        )

    snr = _estimate_snr(samples)
    clip_ratio = _detect_clipping(samples)
    speech_ratio = _estimate_speech_ratio(samples)
    mean_volume = _mean_volume_db(samples)

    recommendations = []
    warnings = []
    quality = AudioQuality.good

    # SNR assessment
    if snr < 5:
        quality = AudioQuality.unusable
        warnings.append("Audio com ruido extremo. A transcricao provavelmente tera muitos erros.")
        recommendations.append("apply_heavy_noise_suppression")
    elif snr < 10:
        quality = AudioQuality.poor
        warnings.append("Audio com muito ruido de fundo. A transcricao pode conter erros.")
        recommendations.append("apply_noise_suppression")
    elif snr < 20:
        quality = AudioQuality.moderate
        recommendations.append("apply_light_filtering")

    # Clipping assessment
    if clip_ratio > 0.05:
        if quality.value in ("good", "moderate"):
            quality = AudioQuality.poor
        warnings.append("Audio com distorcao (microfone estourado). Trechos podem ser ininteligiveis.")
        recommendations.append("apply_declipping")
    elif clip_ratio > 0.01:
        if quality == AudioQuality.good:
            quality = AudioQuality.moderate
        warnings.append("Audio com leve distorcao em picos de volume.")

    # Speech ratio assessment
    if speech_ratio < 0.05:
        quality = AudioQuality.unusable
        warnings.append("Audio nao contem fala detectavel. Verifique se o arquivo esta correto.")
        recommendations.append("reject_no_speech")
    elif speech_ratio < 0.15:
        warnings.append("Audio contem pouca fala (muito silencio ou ruido).")
        recommendations.append("trim_silence")

    # Volume assessment
    if mean_volume < -40:
        if quality == AudioQuality.good:
            quality = AudioQuality.moderate
        warnings.append("Audio com volume muito baixo. Pode afetar a transcricao.")
        recommendations.append("apply_gain_boost")
    elif mean_volume < -30:
        recommendations.append("apply_light_gain")

    return AudioDiagnostics(
        snr_db=round(snr, 1),
        clip_ratio=round(clip_ratio, 4),
        speech_ratio=round(speech_ratio, 2),
        mean_volume_db=round(mean_volume, 1),
        quality=quality,
        recommendations=recommendations,
        warnings=warnings,
    )


def _extract_pcm_samples(
    audio_path: Path, ffmpeg: str, max_seconds: int = 120
) -> np.ndarray | None:
    """Extract raw PCM samples from audio file (first N seconds for speed)."""
    command = [
        ffmpeg,
        "-i", str(audio_path),
        "-t", str(max_seconds),
        "-ar", "16000",
        "-ac", "1",
        "-f", "s16le",
        "-",
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, timeout=60, check=False
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if result.returncode != 0 or len(result.stdout) == 0:
        return None

    return np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32)


def _estimate_snr(samples: np.ndarray) -> float:
    """Estimate Signal-to-Noise Ratio in dB using frame energy percentiles."""
    frame_size = 1600  # 100ms at 16kHz
    num_frames = len(samples) // frame_size
    if num_frames < 10:
        return 0.0

    energies = np.array([
        np.mean(samples[i * frame_size:(i + 1) * frame_size] ** 2)
        for i in range(num_frames)
    ])

    # Bottom 30% of frames assumed to be noise/silence
    noise_threshold = np.percentile(energies, 30)
    noise_frames = energies[energies <= noise_threshold]
    signal_frames = energies[energies > noise_threshold]

    if len(noise_frames) == 0 or len(signal_frames) == 0:
        return 30.0  # Can't determine, assume decent

    noise_energy = np.mean(noise_frames)
    signal_energy = np.mean(signal_frames)

    if noise_energy <= 0:
        return 60.0  # Effectively clean

    snr_db = 10 * np.log10(signal_energy / noise_energy)
    return float(max(0.0, snr_db))


def _detect_clipping(samples: np.ndarray) -> float:
    """Detect percentage of clipped samples (at max int16 value)."""
    max_val = 32767
    clipped = np.sum(np.abs(samples) >= max_val - 1)
    return float(clipped / len(samples)) if len(samples) > 0 else 0.0


def _estimate_speech_ratio(samples: np.ndarray) -> float:
    """Estimate fraction of audio containing speech using energy-based VAD."""
    frame_size = 1600  # 100ms at 16kHz
    num_frames = len(samples) // frame_size
    if num_frames < 5:
        return 0.0

    energies = np.array([
        np.mean(samples[i * frame_size:(i + 1) * frame_size] ** 2)
        for i in range(num_frames)
    ])

    # Adaptive threshold: frames with energy above 3x the 20th percentile
    # are considered speech
    baseline = np.percentile(energies, 20)
    if baseline <= 0:
        baseline = 1.0

    speech_threshold = baseline * 3.0
    speech_frames = np.sum(energies > speech_threshold)

    return float(speech_frames / num_frames)


def _mean_volume_db(samples: np.ndarray) -> float:
    """Calculate mean volume in dBFS."""
    if len(samples) == 0:
        return -96.0

    rms = np.sqrt(np.mean(samples ** 2))
    if rms <= 0:
        return -96.0

    # dBFS relative to int16 max
    db = 20 * np.log10(rms / 32767)
    return float(db)
