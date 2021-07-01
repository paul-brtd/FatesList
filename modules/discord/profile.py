from ..badges import *
from ..core import *

router = APIRouter(
    prefix = "/profile",
    tags = ["Profile"],
    include_in_schema = False
)

@router.get("/me")
async def redirect_me(request: Request, preview: bool = False):
    if "user_id" not in request.session.keys():
        return RedirectResponse("/")
    return await get_user_profile(request, int(request.session.get("user_id")), preview = preview)

@router.get("/{user_id}")
async def profile_of_user_generic(request: Request, user_id: int, preview: bool = False):
    return await get_user_profile(request, user_id, preview = preview)

async def get_user_profile(request, user_id: int, preview: bool):
    guild = client.get_guild(main_server)
    if guild is None:
        return await templates.e(request, "Site is still loading...")
    
    if request.session.get("user_id"):
        dpy_viewer = guild.get_member(int(request.session.get("user_id")))
    
    else:
        dpy_viewer = None

    dpy_member = guild.get_member(user_id)
    if dpy_viewer is None:
        admin = False
    
    else:
        admin = is_staff(staff_roles, dpy_viewer.roles, 4)[0]
    
    if user_id == int(request.session.get("user_id", -1)) and not preview:
        personal = True
    else:
        personal = False

    user = await core.User(id = user_id, db = request.scope["db"], client = request.scope["discord_client"]).profile()
    if not user:
        return await templates.e(request, "Profile Not Found", 404)
    
    return await templates.TemplateResponse(
        "profile.html", 
        {
            "request": request, 
            "user": user, 
            "personal": personal, 
            "admin": admin
        }
    )
