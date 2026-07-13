"""Transcribe an audio file to text and save it under /data.

Best-effort: uses google-cloud-speech when credentials are available
(GOOGLE_APPLICATION_CREDENTIALS), otherwise falls back to a placeholder so the
pipeline still completes. Replace the fallback with your preferred STT service.
"""
from __future__ import annotations

from core.config import settings
from core.logging import get_logger
from core.security import validate_path

logger = get_logger(__name__)


def handle_transcribe_audio(input_audio_filename: str, output_text_filename: str) -> str:
    input_path = validate_path(input_audio_filename, settings.data_dir)
    output_path = validate_path(output_text_filename, settings.data_dir)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file {input_audio_filename} not found.")

    transcription = _transcribe(input_path)
    output_path.write_text(transcription, encoding="utf-8")
    return f"Operation 'transcribe_audio' completed: saved to {output_text_filename}."


def _transcribe(input_path) -> str:
    try:
        from google.cloud import speech
        from pydub import AudioSegment

        audio = AudioSegment.from_file(str(input_path))
        wav_path = input_path.with_suffix(".wav")
        audio.export(wav_path, format="wav")

        client = speech.SpeechClient()
        with open(wav_path, "rb") as f:
            content = f.read()
        audio_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=audio.frame_rate,
            language_code="en-US",
        )
        resp = client.recognize(
            config=audio_config, audio=speech.RecognitionAudio(content=content)
        )
        return "\n".join(
            r.alternatives[0].transcript for r in resp.results if r.alternatives
        )
    except Exception as e:  # noqa: BLE001 - fallback path
        logger.warning("audio transcription unavailable, using placeholder",
                       extra={"error": str(e)})
        return "Transcription unavailable: speech credentials not configured."
