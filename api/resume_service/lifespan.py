"""FastAPI lifespan events (placeholder for future startup/shutdown logic)."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # startup
    yield
    # shutdown
