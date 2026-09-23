from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.auth import me
from app.api.auth import router as auth_router
from app.api.people import router as people_router
from app.api.groups import router as groups_router
from app.api.workflows import router as workflows_router
from app.core.config import settings
from app.core.errors import register_error_handlers


class HealthResponse(BaseModel):
    status: str
    service: str


app = FastAPI(title="Tuiro API", version="0.2.0")
register_error_handlers(app)
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(people_router, prefix="/api/v1", tags=["people"])
app.include_router(groups_router, prefix="/api/v1")
app.include_router(workflows_router, prefix="/api/v1", tags=["workflows"])
app.add_api_route("/api/v1/me", me, methods=["GET"], tags=["auth"])


@app.get("/api/v1/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="tuiro-api")


# CORS must be the outermost ASGI layer.  Registering it with add_middleware
# leaves Starlette's ServerErrorMiddleware outside it, which can strip CORS
# headers from an unhandled 500 and make the browser report a misleading CORS
# failure.  Wrapping the completed app guarantees headers on every response.
app = CORSMiddleware(
    app=app,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
