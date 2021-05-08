from ..core import *

router = APIRouter(
    prefix = "/admin",
    tags = ["Admin"],
    include_in_schema = False
)    

@router.get("/console")
async def admin_dashboard(request: Request):
    if request.session.get("userid"):
        try:
            guild = client.get_guild(main_server)
            user = guild.get_member(int(request.session.get("userid")))
            staff = is_staff(staff_roles, user.roles, 2)
        except:
            staff = [False, 0, StaffMember(name = "user", id = 0, perm = 0)]
    else:
        staff = [False, 0, StaffMember(name = "user", id = 0, perm = 0)]
    certified = await do_index_query(state = 6, limit = None) # State 0 and state 6 are approved and certified
    bot_amount = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    queue = await do_index_query(state = 1, limit = None, add_query = "ORDER BY created_at ASC")
    under_review = await do_index_query(state = 5, limit = None, add_query = "ORDER BY created_at ASC")
    denied = await do_index_query(state = 2, limit = None, add_query = "ORDER BY created_at ASC")
    banned = await do_index_query(state = 4, limit = None, add_query = "ORDER BY created_at ASC")
    data = {"certified": certified, "bot_amount": bot_amount, "queue": queue, "denied": denied, "banned": banned, "under_review": under_review, "admin": staff[1] == 4, "mod": staff[1] == 3, "owner": staff[1] == 5, "bot_review": staff[1] == 2, "perm": staff[2].name}
    if str(request.url.path).startswith("/api"): # Check for API
        return data # Return JSON if so
    return await templates.TemplateResponse("admin.html", {"request": request} | data) # Otherwise, render the template

@router.post("/console")
@csrf_protect
async def admin_api(request: Request, bt: BackgroundTasks, admin: str = FForm(""), bot_id: int = FForm(0)):
    print(bot_id)
    try:
        guild = client.get_guild(main_server)
        user = guild.get_member(int(request.session["userid"]))
    except:
        return HTMLResponse("Discord API is down right now")
    if user is None:
        return RedirectResponse("/")
    if not is_staff(staff_roles, user.roles, 5)[0]:
        return RedirectResponse("/admin/console", status_code = 303) 
    admin_tool = BotListAdmin(bot_id, int(request.session["userid"]))
    if admin=="certify":
        rc = await admin_tool.certify_bot()
        if rc is not None:
            return rc
        
        return await templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope it certified the bot!", "username": request.session.get("username", False)})
    elif admin=="uncertify":
        await db.execute("UPDATE bots SET state = 0 WHERE bot_id = $1", bot_id)
        channel = client.get_channel(bot_logs)
        owner=str(request.session["userid"])
        await channel.send(f"<@{owner}> uncertified the bot <@{bot_id}>")
        return await templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope it uncertified the bot!", "username": request.session.get("username", False)})
    elif admin=="reset":
        bt.add_task(stat_update_bt)        
        return await templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope your wish comes true ;)", "username": request.session.get("username", False)})
    else:
        return RedirectResponse("/admin/console", status_code = 303)

async def stat_update_bt():
    bots = await db.fetch("SELECT bot_id, votes FROM bots")
    epoch = time.time()
    for bot in bots:
        await db.execute("INSERT INTO bot_stats_votes_pm (bot_id, epoch, votes) VALUES ($1, $2, $3)", bot["bot_id"], epoch, bot["votes"])
    await db.execute("UPDATE bots SET votes = 0")
    await db.execute("UPDATE users SET vote_epoch = NULL")

@router.post("/console/ban")
async def ban_user_admin(request: Request, user_id: int = FForm(1), ban_type: int = FForm(100)):
    if "userid" not in request.session.keys():
        return RedirectResponse("/")
    guild = client.get_guild(main_server)
    user = guild.get_member(int(request.session["userid"]))
    try:
        user_ban = guild.get_member(int(user_id))
    except:
        user_ban = None
    s = is_staff(staff_roles, user.roles, 2)
    if user_ban is None or user_ban.roles is None:
        pass
    elif is_staff(staff_roles, user_ban.roles, 2)[0] and ban_type != 0:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "You cannot ban Fates List Staff..."})
    if not s[0]:
        return RedirectResponse("/")
    if user_id is None or ban_type not in [0, 1, 2, 3]:
        return RedirectResponse("/")
    await db.execute("UPDATE users SET state = $1 WHERE user_id = $2", ban_type, user_id)
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Banned User Successfully"})


@router.post("/review/{bot_id}")
async def review_tool(request: Request, bot_id: int, accept: str = FForm(""), deny_reason: str = FForm(deny_feedback), accept_feedback: str = FForm(approve_feedback), unverify_reason: str = FForm("This is likely due to it breaking Discord ToS or our rules")):
    if "userid" not in request.session.keys():
        return RedirectResponse("/")
    guild = client.get_guild(main_server)
    if guild is None:
        return HTMLResponse("We are currently connecting to Discord, please wait")
    user = guild.get_member(int(request.session["userid"]))
    s = is_staff(staff_roles, user.roles, 2)
    bot = await get_bot(bot_id)
    admin_tool = BotListAdmin(bot_id, int(request.session["userid"]))
    if not s[0] or not bot:
        return RedirectResponse("/")             
    elif accept == "true":
        rc = await admin_tool.approve_bot(accept_feedback)
        if rc is not None:
            return rc
        return await templates.TemplateResponse("last.html",{"request":request,"message":"Bot accepted; You MUST Invite it by this url","username":request.session["username"],"url":f"https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot&guild_id={guild.id}&disable_guild_select=true&permissions=0"})
    elif accept == "unverify":
        rc = await admin_tool.unverify_bot(unverify_reason)
        if rc is False:
            return RedirectResponse("/admin/console")
        return await templates.TemplateResponse("message.html",{"request":request,"message":"Bot unverified. Please carry on with your day"})
    elif accept == "false":
        rc = await admin_tool.deny_bot(deny_reason)
        if rc is not None:
            return rc
        return await templates.TemplateResponse("message.html",{"request":request,"message":"Bot denied. Please carry on with your day"})
    else:
        return RedirectResponse("/")
