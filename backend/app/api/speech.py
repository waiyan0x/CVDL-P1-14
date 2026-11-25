"""ElevenLabs speech for Read result aloud and automatic announcements."""

from typing import Literal

from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse, Response

from ..services.speech import MEDIA_TYPE


class SpeechRequest(BaseModel):
    text: str
    language: Literal['en', 'zh'] = 'en'


def speech_status(request):
    return JSONResponse(request.app.state.speech.status())


async def text_to_speech(request):
    body = SpeechRequest.model_validate_json(await request.body())
    audio = await run_in_threadpool(request.app.state.speech.synthesize, body.text, body.language)
    return Response(audio, media_type=MEDIA_TYPE, headers={'Cache-Control': 'no-store'})
