from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, movements, products, summary

app = FastAPI(title="S-Pback")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"ok": True}


app.include_router(auth.router)
app.include_router(products.router)
app.include_router(movements.router)
app.include_router(summary.router)
