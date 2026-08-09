from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    database: str


@router.get("/health", response_model=Health)
async def healthcheck(request: Request) -> Health:
    pool = request.app.state.pool
    try:
        async with pool.acquire() as connection:
            await connection.fetchval("SELECT 1")
        database = "up"
    except Exception:
        database = "down"

    return Health(status="ok" if database == "up" else "degraded", database=database)
