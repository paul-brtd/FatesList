"""
Fates List Templating System
"""

from .imports import *
from .permissions import *
        
# Template class renderer
class templates():
    @staticmethod
    async def TemplateResponse(f, arg_dict: dict, *, context: dict = {}, not_error: bool = True):
        guild = client.get_guild(main_server)
        request = arg_dict["request"]
        worker_session = request.app.state.worker_session
        db = worker_session.postgres
        status = arg_dict.get("status_code")
        if "user_id" in request.session.keys():
            arg_dict["css"] = request.session.get("user_css")
            if guild:
                user = guild.get_member(int(request.session.get("user_id", 0)))
            state = await db.fetchval("SELECT state FROM users WHERE user_id = $1", int(request.session["user_id"]))
            if (state == enums.UserState.global_ban) and not_error:
                ban_type = enums.UserState(state).__doc__
                return await templates.e(request, f"You have been {ban_type} banned from Fates List<br/>", status_code = 403)
            if user is not None:
                staff = is_staff(staff_roles, user.roles, 2)
                request.session["staff"] = staff[0], staff[1], staff[2].dict()
            else:
                pass
            arg_dict["staff"] = request.session.get("staff")
            arg_dict["avatar"] = request.session.get("avatar")
            arg_dict["username"] = request.session.get("username")
            arg_dict["user_id"] = int(request.session.get("user_id"))
            if request.session.get("user_id"):
                arg_dict["user_token"] = await db.fetchval("SELECT api_token FROM users WHERE user_id = $1", arg_dict["user_id"]) 
            arg_dict["intl_text"] = intl_text # This comes from lynxfall.utils.string
            arg_dict["site_lang"] = request.session.get("site_lang", "default")
            arg_dict["scopes"] = request.session.get("scopes")
        else:
            arg_dict["staff"] = [False]
        arg_dict["site_url"] = site_url
        arg_dict["data"] = arg_dict.get("data")
        arg_dict["path"] = request.url.path
        arg_dict["enums"] = enums
        arg_dict["len"] = len
        arg_dict["ireplace"] = ireplace
        arg_dict["ireplacem"] = ireplacem
        
        base_context = {
            "user_id": str(arg_dict["user_id"]) if "user_id" in arg_dict.keys() else None,
            "user_token": arg_dict.get("user_token"),
            "site_lang": arg_dict.get("site_lang"),
            "logged_in": True if "user_id" in arg_dict.keys() else False
        }
        
        arg_dict["context"] = base_context | context
        
        _templates = worker_session.templates
        
        if status is None:
            ret = _templates.TemplateResponse(f, arg_dict)
            
        else:
            ret = _templates.TemplateResponse(f, arg_dict, status_code = status)
            
        return ret

    @staticmethod
    async def error(f, arg_dict, status_code):
        arg_dict["status_code"] = status_code
        return await templates.TemplateResponse(f, arg_dict, not_error = False)

    @staticmethod
    async def e(request, reason: str, status_code: int = 404, *, main: Optional[str] = ""):
        return await templates.error("message.html", {"request": request, "message": main, "reason": reason, "retmain": True}, status_code)
