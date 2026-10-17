"""Text-layer PDF extraction in a byte/page/time/memory-bounded subprocess.

No OCR, remote model, JavaScript execution or automatic decryption. This is
resource isolation, not an OS security sandbox. PDF tables retain layout text;
financial row/period/unit interpretation remains a separate evidence task.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

MAX_PDF_BYTES = 1_000_000
MAX_PDF_PAGES = 8
MAX_TEXT_CHARS = 24_000
_job_handle = None


def _limit_worker():
    """Fail closed if the worker cannot apply a hard memory/CPU limit."""
    global _job_handle
    if os.name != "nt":
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (384 * 1024 * 1024, 384 * 1024 * 1024))
        resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
        return
    import ctypes
    from ctypes import wintypes
    class Basic(ctypes.Structure):
        _fields_ = [("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
                    ("flags", wintypes.DWORD), ("min_ws", ctypes.c_size_t), ("max_ws", ctypes.c_size_t),
                    ("active", wintypes.DWORD), ("affinity", ctypes.c_size_t),
                    ("priority", wintypes.DWORD), ("scheduling", wintypes.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_ulonglong) for name in ("ro", "wo", "oo", "rb", "wb", "ob")]
    class Extended(ctypes.Structure):
        _fields_ = [("basic", Basic), ("io", IO), ("process_memory", ctypes.c_size_t),
                    ("job_memory", ctypes.c_size_t), ("peak_process", ctypes.c_size_t), ("peak_job", ctypes.c_size_t)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    _job_handle = kernel.CreateJobObjectW(None, None)
    info = Extended()
    info.basic.flags = 0x100 | 0x2  # PROCESS_MEMORY | PROCESS_TIME
    info.basic.process_time = 20_000_000  # two seconds, 100ns units
    info.process_memory = 384 * 1024 * 1024
    if not (_job_handle and kernel.SetInformationJobObject(_job_handle, 9, ctypes.byref(info), ctypes.sizeof(info))
            and kernel.AssignProcessToJobObject(_job_handle, kernel.GetCurrentProcess())):
        raise RuntimeError("PDF worker resource limits unavailable")


def _worker():
    _limit_worker()
    from io import BytesIO
    from pypdf import PdfReader
    body = sys.stdin.buffer.read(MAX_PDF_BYTES + 1)
    if len(body) > MAX_PDF_BYTES or not body.startswith(b"%PDF-"):
        raise ValueError("Invalid or oversized PDF")
    reader = PdfReader(BytesIO(body), strict=True)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDF requires approved separate handling")
    text, pages = "", []
    page_count = len(reader.pages)
    for index in range(min(page_count, MAX_PDF_PAGES)):
        remaining = MAX_TEXT_CHARS - len(text)
        if remaining < 100:
            break
        page_text = reader.pages[index].extract_text(extraction_mode="layout") or ""
        if not page_text.strip():
            continue
        piece = (f"[PDF page {index + 1}]\n" + page_text)[:remaining]
        start = len(text)
        text += piece + "\n\n"
        pages.append({"page": index + 1, "start": start, "end": start + len(piece),
                      "text_truncated": len(piece) < len(page_text) + len(f"[PDF page {index + 1}]\n")})
    result = {"text": text[:MAX_TEXT_CHARS], "page_count": page_count, "pages": pages,
              "truncated": len(pages) < page_count or any(p["text_truncated"] for p in pages),
              "method": "PYPDF_LAYOUT_TEXT_LAYER", "table_structure_verified": False}
    print(json.dumps(result, ensure_ascii=True))


def extract_pdf_text(body, *, timeout=2.5):
    if not isinstance(body, bytes) or len(body) > MAX_PDF_BYTES or not body.startswith(b"%PDF-"):
        raise ValueError("Invalid or oversized PDF")
    if timeout <= 0:
        raise TimeoutError("PDF extraction budget exhausted")
    # Never forward server/API credentials into an untrusted-document parser.
    worker_env = {key: os.environ[key] for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP") if key in os.environ}
    try:
        run = subprocess.run([sys.executable, "-I", str(Path(__file__).resolve()), "--worker"],
            input=body, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=worker_env,
            timeout=min(float(timeout), 2.5), check=False)
    except subprocess.TimeoutExpired as error:
        raise TimeoutError("PDF extraction deadline reached") from error
    if run.returncode or len(run.stdout) > 200_000:
        raise ValueError("PDF parser failed or resource limit reached")
    result = json.loads(run.stdout)
    if not isinstance(result.get("text"), str) or len(result["text"]) > MAX_TEXT_CHARS:
        raise ValueError("Invalid PDF parser output")
    result["source_pdf_sha256"] = hashlib.sha256(body).hexdigest()
    return result


if __name__ == "__main__":
    try:
        _worker()
    except Exception:
        sys.exit(1)
