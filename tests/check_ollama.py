#!/usr/bin/env python3
"""Check available Ollama models."""

import httpx
import asyncio
import os

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "https://kiersten-nonpunishable-carry.ngrok-free.dev")

async def check_ollama():
    """Check what models are available in Ollama."""
    try:
        client = httpx.AsyncClient(timeout=10.0, headers={"ngrok-skip-browser-warning": "true"})
        resp = await client.get(f"{OLLAMA_URL}/api/tags")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_ollama())