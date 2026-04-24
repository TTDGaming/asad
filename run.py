"""Khởi động Asad ở local.

Windows:   python run.py
iPhone:    mở Safari tới http://<IP-máy-Windows>:8000 rồi "Add to Home Screen"
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
