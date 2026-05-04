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
    """
    Browser POST using a polling pattern.
    Pygbag's event loop does not reliably resolve JavaScript Promises back
    to Python `await`, so we trigger the fetch in JS, write the result onto
    `window._apResult`, and poll from Python until it becomes non-null.
    """
    try:
        import platform
        import asyncio
        body_str = json.dumps(data)
        js_code = (
            "window._apResult=null;"
            "fetch(" + json.dumps(url) + ","
            "{method:'POST',body:" + json.dumps(body_str) + ","
            "headers:{'Content-Type':'application/json'}})"
            ".then(function(r){"
            "return r.text().then(function(t){"
            "window._apResult={status:r.status,body:t};"
            "});"
            "}).catch(function(e){"
            "window._apResult={status:0,body:String(e)};"
            "});"
        )
        platform.window.eval(js_code)
        # Poll up to 30 seconds for the JS callback to set _apResult
        res = None
        for _ in range(600):
            res = platform.window._apResult
            if res is not None:
                break
            await asyncio.sleep(0.05)
        if res is None:
            return {"error": "Request timed out"}
        status = int(res.status)
        body_text = str(res.body)
        if status == 0:
            return {"error": body_text}
        try:
            result = json.loads(body_text)
        except json.JSONDecodeError:
            return {"error": f"Invalid response: {body_text[:100]}"}
        if status in (200, 201):
            return result
        if isinstance(result, dict):
            return {"error": result.get("detail", "Request failed")}
        return {"error": "Request failed"}
    except Exception as e:
        return {"error": f"Could not connect to server: {e}"}


async def login(username: str, password: str) -> dict:
    return await _post("/auth/login", {"username": username, "password": password})


async def signup(username: str, password: str) -> dict:
    return await _post("/auth/signup", {"username": username, "password": password})
