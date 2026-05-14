from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.predictions import router as predictions_router
from app.api.routes.sessions import router as sessions_router
from app.api.ws.live import router as live_ws_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="GymNet API",
        version="0.1.0",
        description="Realtime gym zone monitoring and exercise analytics backend.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(predictions_router, prefix="/api")
    app.include_router(live_ws_router)

    return app


app = create_app()
