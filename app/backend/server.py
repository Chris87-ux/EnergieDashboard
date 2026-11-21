import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pymongo.errors import PyMongoError
from dotenv import load_dotenv
import os
import logging
from pathlib import Path


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
from lib.db import client, db, ensure_indexes  # noqa: E402
from lib.recorder import recorder_loop  # noqa: E402
from routers import energy, flows, settings, acquisition, config_csv  # noqa: E402

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        try:
            await ensure_indexes()
            from lib.migrations import migrate
            await migrate()
        except Exception:
            logger.exception("MongoDB-Start fehlgeschlagen. MONGO_URL und DB_NAME prüfen.")
            raise
        recorder = asyncio.create_task(recorder_loop())
        try:
            yield
        finally:
            recorder.cancel()
            with suppress(asyncio.CancelledError):
                await recorder
            from lib.acquisition import close_connections
            await close_connections()
    finally:
        await client.close()


app = FastAPI(lifespan=lifespan, title="Energieboard", version="2.3.0")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    try:
        await db.command("ping")
    except PyMongoError as exc:
        raise HTTPException(status_code=503, detail="MongoDB ist derzeit nicht erreichbar.") from exc
    return {"message": "Energieboard API", "status": "ok", "version": "2.3.0", "schema_version": 5}


api_router.include_router(flows.router)
api_router.include_router(settings.router)
api_router.include_router(energy.router)
api_router.include_router(acquisition.router)
api_router.include_router(config_csv.router)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

app.include_router(api_router)

frontend = Path(os.getenv("FRONTEND_DIST", str(ROOT_DIR.parent / "frontend" / "dist")))
if (frontend / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=frontend / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend_page(path: str):
        if path == "api" or path.startswith("api/"):
            raise HTTPException(status_code=404)
        return FileResponse(frontend / "index.html")
