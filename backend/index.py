from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlmodel import Session

from config.database import create_db_and_tables, engine, get_session
from routes.nodes import router as nodes_router
from routes.openings import router as openings_router

import models.node  # noqa: F401
import models.opening  # noqa: F401
import models.training  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Chess Openings Trainer", lifespan=lifespan)

app.include_router(openings_router, prefix="/api")
app.include_router(nodes_router, prefix="/api")


@app.get("/api/health")
def health(session: Session = Depends(get_session)):
    session.execute(text("SELECT 1"))
    return {"status": "ok"}