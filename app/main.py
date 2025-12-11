# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.db.mongo import init_client, get_client, close_client, get_master_db, get_org_collection
from app.routes.auth import router as auth_router
from app.routes.org import router as org_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: create client and verify connection
    init_client()
    try:
        await get_client().admin.command("ping")
        print("Connected to MongoDB")
    except Exception as e:
        print("Mongo ping failed:", e)
        # you can raise to stop app startup if you prefer
    yield
    # shutdown: close client
    close_client()
    print("MongoDB connection closed")

app = FastAPI(lifespan=lifespan)

# include routers etc.
@app.get("/help")
async def root():
    return {"message": "Organization Management Service is running."}

@app.get("/ping")
async def ping():
    db = get_master_db()
    count = await db["organizations"].count_documents({})
    return {"message": "pong", "organizations_in_master": count}

app.include_router(auth_router)
app.include_router(org_router)