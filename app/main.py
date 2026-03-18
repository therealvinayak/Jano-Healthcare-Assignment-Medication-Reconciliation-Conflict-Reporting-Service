from fastapi import FastAPI

from app.api.routes import history, ingest, patients, reporting, resolution
from app.core.config import get_settings
from app.core.error_handlers import install_error_handlers

settings = get_settings()
app = FastAPI(title=settings.app_name)
install_error_handlers(app)

app.include_router(patients.router, prefix="/api/v1")
app.include_router(ingest.router, prefix="/api/v1")
app.include_router(reporting.router, prefix="/api/v1")
app.include_router(history.router, prefix="/api/v1")
app.include_router(resolution.router, prefix="/api/v1")


@app.get("/health")
def healthcheck():
    return {"status": "ok"}
