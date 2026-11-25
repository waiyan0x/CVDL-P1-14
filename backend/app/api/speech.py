"""ElevenLabs text-to-speech for the Read result aloud button and automatic announcements."""
from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import Response
from pydantic import BaseModel

from ..services.speech import MEDIA_TYPE

router = APIRouter(prefix='/api/speech', tags=['speech'])


class SpeechRequest(BaseModel):
    text: str
    language: Literal['en', 'zh'] = 'en'


@router.get('/status')
def speech_status(request: Request):
    return request.app.state.speech.status()


@router.post('/tts')
def text_to_speech(body: SpeechRequest, request: Request):
    audio = request.app.state.speech.synthesize(body.text, body.language)
    return Response(audio, media_type=MEDIA_TYPE, headers={'Cache-Control': 'no-store'})
