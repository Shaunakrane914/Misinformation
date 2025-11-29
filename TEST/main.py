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

@app.get("/agents")
def agents_page():
    return FileResponse("frontend/agents.html")

@app.get("/scout-agent")
def scout_agent_page():
    return FileResponse("frontend/scout-agent.html")

@app.get("/trending-agent")
def trending_agent_page():
    return FileResponse("frontend/trending-agent.html")

@app.get("/brandshield-agent")
def brandshield_agent_page():
    return FileResponse("frontend/brandshield-agent.html")

@app.get("/personal-watch-agent")
def personal_watch_agent_page():
    return FileResponse("frontend/personal-watch-agent.html")

@app.get("/dashboard.css")
def serve_css():
    return FileResponse("frontend/dashboard.css")

@app.get("/dashboard.js")
def serve_js():
    return FileResponse("frontend/dashboard.js")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
