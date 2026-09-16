import uvicorn
import os
import socket
from backend.main import app

def find_available_port(preferred: int = 8000) -> int:
    env_port = os.getenv("PORT")
    if env_port:
        return int(env_port)
    for p in [preferred, 8001, 8080, 5050]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", p))
                return p
            except OSError:
                continue
    return preferred

if __name__ == "__main__":
    port = find_available_port(8000)
    print(f"Starting Aegis Protocol server on port {port}...")
    try:
        with open("port.txt", "w") as f:
            f.write(str(port))
    except Exception:
        pass
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False, access_log=True)
