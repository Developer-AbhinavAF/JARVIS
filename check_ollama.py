#!/usr/bin/env python3
"""Check available Ollama models."""

import httpx
import asyncio

async def check_ollama():
    """Check what models are available in Ollama."""
    try:
        client = httpx.AsyncClient(timeout=10.0)
        resp = await client.get("http://localhost:11434/api/tags")
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(check_ollama())