"""ElevenLabs text-to-speech route, with the ElevenLabs client faked."""
from fastapi.testclient import TestClient
import pytest

from backend.app.config import Settings, read_env_file
from backend.app.main import create_app
from backend.app.services.runtime import Runtime
from backend.app.services.speech import SpeechSynthesizer


class IdleRuntime(Runtime):
    def start(self):
        return self


class FakeTextToSpeech:
    def __init__(self, fail=False):
        self.calls, self.fail = [], fail

    def convert(self, voice_id, **kwargs):
        self.calls.append((voice_id, kwargs))
        if self.fail:
            raise RuntimeError('quota exceeded')
        return iter([b'ID3', b'audio'])


class FakeClient:
    def __init__(self, fail=False):
        self.text_to_speech = FakeTextToSpeech(fail)


CONFIGURED = dict(elevenlabs_api_key='secret', elevenlabs_voice_en='voice-en', elevenlabs_voice_zh='voice-zh')


def make_client(settings, fake):
    app = create_app(settings, IdleRuntime)
    app.state.speech = SpeechSynthesizer(settings, client_factory=lambda key: fake)
    return TestClient(app)


def test_speaks_with_the_configured_voice_and_caches_repeats():
    fake = FakeClient()
    with make_client(Settings(**CONFIGURED), fake) as client:
        assert client.get('/api/speech/status').json() == {'available': True, 'languages': ['en', 'zh']}
        for _ in range(2):
            response = client.post('/api/speech/tts', json={'text': 'Bus  1 7 4 to Kampong Bahru.'})
            assert response.status_code == 200
            assert response.headers['content-type'] == 'audio/mpeg'
            assert response.content == b'ID3audio'
        zh = client.post('/api/speech/tts', json={'text': '巴士 174', 'language': 'zh'})
        assert zh.status_code == 200
    calls = fake.text_to_speech.calls
    assert [voice for voice, _ in calls] == ['voice-en', 'voice-zh']
    assert calls[0][1]['text'] == 'Bus 1 7 4 to Kampong Bahru.'
    assert calls[0][1]['model_id'] == 'eleven_flash_v2_5'


def test_unconfigured_failed_and_invalid_requests_have_clear_errors():
    with make_client(Settings(), FakeClient()) as client:
        assert client.get('/api/speech/status').json() == {'available': False, 'languages': []}
        response = client.post('/api/speech/tts', json={'text': 'Hello'})
        assert response.status_code == 503 and response.json()['error']['code'] == 'tts_unavailable'
    with make_client(Settings(**CONFIGURED), FakeClient(fail=True)) as client:
        response = client.post('/api/speech/tts', json={'text': 'Hello'})
        assert response.status_code == 502 and response.json()['error']['code'] == 'tts_failed'
        assert 'secret' not in response.text
        assert client.post('/api/speech/tts', json={'text': '   '}).status_code == 422
        assert client.post('/api/speech/tts', json={'text': 'x' * 601}).status_code == 422
        assert client.post('/api/speech/tts', json={'text': 'Hi', 'language': 'fr'}).status_code == 422


def test_settings_read_env_file_and_environment_wins(tmp_path, monkeypatch):
    env = tmp_path / '.env.local'
    env.write_text('# comment\nELEVENLABS_API_KEY="from-file"\nELEVENLABS_VOICE_ID_EN=file-en\n', encoding='utf-8')
    assert read_env_file(env)['ELEVENLABS_API_KEY'] == 'from-file'
    for key in ('ELEVENLABS_API_KEY', 'ELEVENLABS_VOICE_ID_ZH', 'ELEVENLABS_MODEL_ID'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('ELEVENLABS_VOICE_ID_EN', 'env-en')
    settings = Settings.from_env(env)
    assert settings.elevenlabs_api_key.get_secret_value() == 'from-file'
    assert settings.voices == {'en': 'env-en'}
    assert 'from-file' not in repr(settings)


@pytest.mark.parametrize('missing', ['elevenlabs_api_key', 'elevenlabs_voice_en'])
def test_missing_key_or_voice_means_unavailable(missing):
    values = {**CONFIGURED, missing: None, 'elevenlabs_voice_zh': None}
    assert not SpeechSynthesizer(Settings(**values)).available
