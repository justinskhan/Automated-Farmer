import sys
import json

_IS_BROWSER = sys.platform in ("emscripten", "wasi")

# Update this to your hosted backend URL once deployed.
# For local development the backend runs at localhost:8000.
API_BASE = "https://automated-farmer-backend.onrender.com"


async def _post(endpoint: str, data: dict) -> dict:
    url = f"{API_BASE}{endpoint}"
    if _IS_BROWSER:
        return await _browser_post(url, data)
    return await _desktop_post(url, data)


async def _desktop_post(url: str, data: dict) -> dict:
    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=data,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                body = await resp.json()
                if resp.status in (200, 201):
                    return body
                return {"error": body.get("detail", "Request failed")}
    except Exception as e:
        return {"error": f"Could not connect to server: {e}"}


async def _browser_post(url: str, data: dict) -> dict:
    try:
        import platform
        body_str = json.dumps(data)
        # Single JS async IIFE: fetch + read body in one await to avoid
        # Pygbag issues with chained sequential JavaScript Promise awaits.
        js = (
            "(async()=>{"
            "const r=await fetch(" + json.dumps(url) + ","
            "{method:'POST',body:" + json.dumps(body_str) + ","
            "headers:{'Content-Type':'application/json'}});"
            "return r.status+'|||'+(await r.text());"
            "})()"
        )
        raw = str(await platform.window.eval(js))
        status_str, body_text = raw.split("|||", 1)
        result = json.loads(body_text)
        if int(status_str) in (200, 201):
            return result
        return {"error": result.get("detail", "Request failed")}
    except Exception as e:
        return {"error": f"Could not connect to server: {e}"}


async def login(username: str, password: str) -> dict:
    return await _post("/auth/login", {"username": username, "password": password})


async def signup(username: str, password: str) -> dict:
    return await _post("/auth/signup", {"username": username, "password": password})
