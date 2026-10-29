from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.evaluation import router
from backend.app.config import Settings


def test_metadata_remains_honest_when_weights_and_ocr_are_unavailable(tmp_path):
    app = FastAPI()
    app.state.settings = Settings(root=tmp_path)
    app.include_router(router)
    with TestClient(app) as client:
        models = client.get("/api/models").json()
        evaluation = client.get("/api/evaluation").json()
    assert not models["detector"]["available"]
    assert len(models["ocr_engines"]) == 3
    assert all(not engine["available"] for engine in models["ocr_engines"])
    assert evaluation["accuracy"] is None
    assert evaluation["historical_checkpoint"]["metrics"] is None
    assert evaluation["status"] == "unmeasured"
