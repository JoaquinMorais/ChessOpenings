from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlmodel import Session

from config.database import engine, get_session
from config.migrations import run_migrations
from routes.evaluation import router as evaluation_router
from routes.io import router as io_router
from routes.meta import router as meta_router
from routes.nodes import router as nodes_router
from routes.openings import router as openings_router
from routes.stats import router as stats_router
from routes.training import router as training_router
from utils.data_permissions import normalize_data_permissions
from utils.preferences import apply_favorites
from utils.seed import load_seed

import models.node  # noqa: F401
import models.opening  # noqa: F401
import models.seed_import  # noqa: F401
import models.training  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    run_migrations()
    normalize_data_permissions()
    with Session(engine) as session:
        load_seed(session)
        apply_favorites(session)
    yield


app = FastAPI(title="Chess Openings Trainer", lifespan=lifespan)

app.include_router(openings_router, prefix="/api")
app.include_router(nodes_router, prefix="/api")
app.include_router(io_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api")
app.include_router(meta_router, prefix="/api")
app.include_router(training_router, prefix="/api")
app.include_router(stats_router, prefix="/api")


@app.get("/api/health")
def health(session: Session = Depends(get_session)):
    session.execute(text("SELECT 1"))
    return {"status": "ok"}