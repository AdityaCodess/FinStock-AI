# finstock-ai/backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api import endpoints
from app.api import websockets 
# ... (app = FastAPI(...) and CORSMiddleware setup is the same) ...
app = FastAPI(
    title="FinStock AI",
    description="An AI-Powered Indian Stock Market Analysis and Prediction Dashboard.",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- API Endpoints ---
app.include_router(endpoints.router)
app.include_router(websockets.router)  # <-- 2. INCLUDE THE NEW ROUTER

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the FinStock AI API!"}


# ... (if __name__ == "__main__": block is the same) ...
if __name__ == "__main__":
    # This block is only for running with 'python main.py'
    # Recommended to run from 'backend/' folder with:
    # uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    print("Starting FinStock AI backend server at http://127.0.0.1:8000")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)