import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class TuiroError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(TuiroError)
    async def tuiro_error_handler(_: Request, exc: TuiroError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": {"code": exc.code, "message": exc.message}})

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception) -> JSONResponse:
        """Never expose a traceback or return an HTML 500 to API clients."""
        logger.exception("Unhandled API exception", exc_info=exc)
        return JSONResponse(status_code=500, content={"success": False, "error": {"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected server error occurred."}})
