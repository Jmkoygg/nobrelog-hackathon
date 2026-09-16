from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import cadastros, dispatch, geo, imports, orgs, plans

settings = get_settings()

app = FastAPI(title="NobreLOG API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(orgs.router)
app.include_router(cadastros.router)
app.include_router(imports.router)
app.include_router(plans.router)
app.include_router(geo.router)
app.include_router(dispatch.router)


@app.get("/health")
def health():
    return {"status": "ok", "supabase_configured": settings.is_configured}
