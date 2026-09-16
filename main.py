"""
Main application entry point for Aegis Protocol.
Serves the unified FastAPI backend and all frontend interfaces.
"""
from backend.main import app

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("backend.main:app", host="127.0.0.1", port=port, reload=False)
