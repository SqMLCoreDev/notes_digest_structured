#!/usr/bin/env python3
"""
Minimal test server to isolate the hanging issue
"""

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Test Server")

@app.get("/")
async def root():
    return {"status": "working"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/test")
async def test_endpoint(data: dict):
    return {"received": data, "status": "ok"}

if __name__ == "__main__":
    print("🧪 Starting minimal test server...")
    uvicorn.run(app, host="0.0.0.0", port=8001)  # Different port