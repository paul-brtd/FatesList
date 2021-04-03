from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, ORJSONResponse
from fastapi import Request
from starlette.status import HTTP_302_FOUND, HTTP_303_SEE_OTHER
import secrets
import string
from config import site_url
from numba import jit

# Some basic utility functions for Fates List (and other users as well)
def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=HTTP_303_SEE_OTHER)

def abort(code: str) -> StarletteHTTPException:
    raise StarletteHTTPException(status_code=code)

@jit(forceobj = True)
def get_token(length: int) -> str:
    secure_str = ""
    for i in range(0, length):
        secure_str += secrets.choice(string.ascii_letters + string.digits)
    return secure_str

def ip_check(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host

@jit(forceobj = True)
def human_format(num: int) -> str:
    if abs(num) < 1000:
        return str(abs(num))
    num = float('{:.3g}'.format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        if magnitude == 31:
            num /= 10
        num /= 1000.0
    return '{} {}'.format('{:f}'.format(num).rstrip('0').rstrip('.'), ['', 'K', 'M', 'B', 'T', "Quad.", "Quint.", "Sext.", "Sept.", "Oct.", "Non.", "Dec.", "Tre.", "Quat.", "quindec.", "Sexdec.", "Octodec.", "Novemdec.", "Vigint.", "Duovig.", "Trevig.", "Quattuorvig.", "Quinvig.", "Sexvig.", "Septenvig.", "Octovig.", "Nonvig.", "Trigin.", "Untrig.", "Duotrig.", "Googol."][magnitude])

def version_scope(request, def_version):
    if str(request.url).startswith(site_url + "/api/") and not str(request.url).startswith(site_url + "/api/docs") and not str(request.url).startswith(site_url + "/api/v") and not str(request.url).startswith(site_url + "/api/ws"):
        if request.headers.get("FL-API-Version"):
            api_ver = request.headers.get("FL-API-Version")
        else:
            api_ver = str(def_version)
        new_scope = request.scope
        new_scope["path"] = new_scope["path"].replace("/api", f"/api/v{api_ver}")
    else:
        new_scope = request.scope
        if str(request.url).startswith(site_url + "/api/v"):
            print(str(request.url.path))
            api_ver = str(request.url.path).split("/")[2][1:] # Split by / and get 2nd (vX part and then get just X)
            if api_ver == "":
                api_ver = str(def_version)
        else:
            api_ver = str(def_version)
    print(api_ver)
    return new_scope, api_ver
