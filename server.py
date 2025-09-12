from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from urllib.parse import urlencode

app = FastAPI()

# Constants for upstream
UPSTREAM_BASE = "https://bkjx.nenu.edu.cn"
CONFIG_PATH = "/new/student/xsxk/xklx/07/config"
SEARCH_PATH = "/new/student/xsxk/xklx/07/hzkc"
KXKC_PATH = "/new/student/xsxk/xklx/07/kxkc"
ADD_PATH = "/new/student/xsxk/xklx/07/add"

# Mount static directory for frontend
app.mount("/static", StaticFiles(directory="static", html=True), name="static")


def path_for(xklx: str, endpoint: str) -> str:
    xklx = str(xklx or "07")
    return f"/new/student/xsxk/xklx/{xklx}/{endpoint}"


def build_headers(client_headers: dict, cookie: str | None, xklx: str = "07") -> dict:
    headers = {
        "User-Agent": client_headers.get("user-agent", "Mozilla/5.0"),
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": client_headers.get("accept-language", "zh-CN,zh;q=0.8"),
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": UPSTREAM_BASE,
        "Referer": f"{UPSTREAM_BASE}/xsxk.html?xklxdm={xklx}",
        "Connection": "keep-alive",
    }
    if cookie:
        headers["Cookie"] = cookie
    return headers


@app.post("/api/config")
async def api_config(request: Request):
    data = await request.json()
    cookie = data.get("cookie")
    xklx = str(data.get("xklx", "07"))
    if not cookie:
        return JSONResponse({"error": "cookie_required"}, status_code=400)

    headers = build_headers(dict(request.headers), cookie, xklx)
    try:
        r = requests.post(UPSTREAM_BASE + path_for(xklx, "config"), headers=headers, data=b"")
        return JSONResponse(r.json())
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/hzkc")
async def api_hzkc(request: Request):
    """首段检索：根据关键字查询课程盘条目（含 kcptdm）。"""
    body = await request.json()
    cookie = body.get("cookie")
    payload = body.get("payload", {})  # 期望至少包含 kcxx
    xklx = str(body.get("xklx", "07"))
    if not cookie:
        return JSONResponse({"error": "cookie_required"}, status_code=400)

    headers = build_headers(dict(request.headers), cookie, xklx)
    try:
        r = requests.post(UPSTREAM_BASE + path_for(xklx, "hzkc"), headers=headers, data=urlencode(payload))
        try:
            return JSONResponse(r.json())
        except Exception:
            return HTMLResponse(r.text, status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/kxkc")
async def api_kxkc(request: Request):
    """二段检索：根据 kcptdm 获取可选课程明细。"""
    body = await request.json()
    cookie = body.get("cookie")
    payload = body.get("payload", {})  # 期望至少包含 kcptdm
    xklx = str(body.get("xklx", "07"))
    if not cookie:
        return JSONResponse({"error": "cookie_required"}, status_code=400)

    headers = build_headers(dict(request.headers), cookie, xklx)
    try:
        r = requests.post(UPSTREAM_BASE + path_for(xklx, "kxkc"), headers=headers, data=urlencode(payload))
        try:
            return JSONResponse(r.json())
        except Exception:
            return HTMLResponse(r.text, status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/search")
async def api_search(request: Request):
    body = await request.json()
    cookie = body.get("cookie")
    payload = body.get("payload", {})
    xklx = str(body.get("xklx", "07"))
    if not cookie:
        return JSONResponse({"error": "cookie_required"}, status_code=400)

    headers = build_headers(dict(request.headers), cookie, xklx)
    try:
        # Step 1: call hzkc to obtain kcptdm
        r1 = requests.post(UPSTREAM_BASE + path_for(xklx, "hzkc"), headers=headers, data=urlencode(payload))
        try:
            j1 = r1.json()
        except Exception:
            return JSONResponse({"error": "invalid_hzkc_response", "status": r1.status_code, "text": r1.text[:500]}, status_code=502)

        # Extract kcptdm from the first response (robustly search in nested structures)
        kcptdm = None

        def find_kcptdm(obj):
            nonlocal kcptdm
            if kcptdm is not None:
                return
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if str(k).lower() == "kcptdm" and v:
                        kcptdm = str(v)
                        return
                    find_kcptdm(v)
            elif isinstance(obj, list):
                for item in obj:
                    find_kcptdm(item)

        find_kcptdm(j1)
        if not kcptdm:
            return JSONResponse({"error": "kcptdm_not_found", "upstream": j1}, status_code=502)

        # Step 2: call kxkc using kcptdm and return its result as search output
        page = payload.get("page", 1)
        rows = payload.get("rows", 50)
        sort = payload.get("sort", "kcrwdm")
        order = payload.get("order", "asc")
        kxkc_payload = {
            "kcptdm": kcptdm,
            "page": page,
            "rows": rows,
            "sort": sort,
            "order": order,
        }
        r2 = requests.post(UPSTREAM_BASE + path_for(xklx, "kxkc"), headers=headers, data=urlencode(kxkc_payload))
        try:
            return JSONResponse(r2.json())
        except Exception:
            return HTMLResponse(r2.text, status_code=r2.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/add")
async def api_add(request: Request):
    body = await request.json()
    cookie = body.get("cookie")
    payload = body.get("payload", {})
    xklx = str(body.get("xklx", "07"))
    if not cookie:
        return JSONResponse({"error": "cookie_required"}, status_code=400)

    headers = build_headers(dict(request.headers), cookie, xklx)
    try:
        r = requests.post(UPSTREAM_BASE + path_for(xklx, "add"), headers=headers, data=urlencode(payload))
        # 有的接口返回 text/plain 或 JSON，这里尽量解析 JSON，否则透传文本
        try:
            j = r.json()
            # 统一将 code != 0 的返回映射为 400，前端能以异常提示
            if isinstance(j, dict) and j.get("code", 0) != 0:
                return JSONResponse(j, status_code=400)
            return JSONResponse(j)
        except Exception:
            return HTMLResponse(r.text, status_code=r.status_code)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/")
async def root():
    return FileResponse("static/index.html")