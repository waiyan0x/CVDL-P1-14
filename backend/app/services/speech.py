"""Text-to-speech with the project's ElevenLabs voices; the API key never leaves the server."""
from __future__ import annotations

import logging
import threading
from collections import OrderedDict

from ..errors import AppError

OUTPUT_FORMAT = 'mp3_44100_128'
MEDIA_TYPE = 'audio/mpeg'


def elevenlabs_client(api_key):
    from elevenlabs.client import ElevenLabs
    return ElevenLabs(api_key=api_key)


class SpeechSynthesizer:
    """Turns announcement text into MP3 audio. Repeated phrases are served from a small in-memory cache."""

    def __init__(self, settings, client_factory=elevenlabs_client):
        self.settings = settings
        self.client_factory = client_factory
        self._client = None
        self._cache = OrderedDict()
        self._lock = threading.Lock()

    @property
    def available(self):
        return bool(self.settings.elevenlabs_api_key and self.settings.voices)

    def status(self):
        return {'available': self.available, 'languages': sorted(self.settings.voices) if self.available else []}

    def client(self):
        if self._client is None:
            self._client = self.client_factory(self.settings.elevenlabs_api_key.get_secret_value())
        return self._client

    def synthesize(self, text, language='en'):
        text = ' '.join(str(text or '').split())
        if not text:
            raise AppError(422, 'invalid_options', 'text: must not be empty')
        if len(text) > self.settings.tts_max_chars:
            raise AppError(422, 'invalid_options', f'text: at most {self.settings.tts_max_chars} characters')
        voice = self.settings.voices.get(language)
        if not self.settings.elevenlabs_api_key or not voice:
            raise AppError(503, 'tts_unavailable', 'ElevenLabs speech is not configured.')
        key = (voice, self.settings.elevenlabs_model, text)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
        try:
            chunks = self.client().text_to_speech.convert(
                voice, text=text, model_id=self.settings.elevenlabs_model,
                language_code=language, output_format=OUTPUT_FORMAT)
            audio = b''.join(chunks)
        except Exception as exc:  # The SDK raises ApiError for HTTP failures and httpx errors for network ones.
            logging.warning('ElevenLabs synthesis failed: %s', getattr(exc, 'status_code', type(exc).__name__))
            raise AppError(502, 'tts_failed', 'ElevenLabs could not generate speech.') from exc
        if not audio:
            raise AppError(502, 'tts_failed', 'ElevenLabs returned no audio.')
        with self._lock:
            if self.settings.tts_cache_entries:
                self._cache[key] = audio
                while len(self._cache) > self.settings.tts_cache_entries:
                    self._cache.popitem(last=False)
        return audio
