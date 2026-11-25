import threading
import uvicorn
from fastapi import FastAPI, HTTPException
from app.data_loader import load_college_dataframe
from app.recommender import rank_colleges_with_groq
from app.schemas import RecommendationRequest, RecommendationResponse

app = FastAPI(title="College Recommendation API", version="1.0.0")
_DF = load_college_dataframe()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "rows_loaded": int(len(_DF))}


@app.post("/recommend", response_model=RecommendationResponse)
def recommend_colleges(payload: RecommendationRequest) -> RecommendationResponse:
    try:
        return rank_colleges_with_groq(_DF, payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def start_fastapi_in_background(host: str = "127.0.0.1", port: int = 8000) -> None:
    def _run() -> None:
        uvicorn.run(app, host=host, port=port, log_level="warning")

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
