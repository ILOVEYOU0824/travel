from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="Travel Planner BFF")
    app.include_router(router)

    web_dir = Path(__file__).resolve().parents[1] / "web"
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(web_dir / "index.html")

    return app


app = create_app()
