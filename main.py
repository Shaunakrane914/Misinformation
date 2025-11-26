from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.main import app as backend_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/api", backend_app)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def index():
    return FileResponse("frontend/index.html")

@app.get("/dashboard")
def dashboard_page():
    return FileResponse("frontend/dashboard.html")

@app.get("/about")
def about_page():
    return FileResponse("frontend/about.html")

@app.get("/submit")
def submit_page():
    return FileResponse("frontend/submit.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)