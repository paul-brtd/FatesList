from ..core import *

router = APIRouter(
    prefix = "/admin",
    tags = ["Admin"],
    include_in_schema = False
)    

@router.get("/console")
async def admin_dashboard(request: Request):
    if request.session.get("user_id"):
        try:
            guild = client.get_guild(main_server)
            user = guild.get_member(int(request.session.get("user_id")))
            staff = is_staff(staff_roles, user.roles, 2)
        except:
            staff = [False, 0, StaffMember(name = "user", id = 0, perm = 0, staff_id = 0)]
    else:
        staff = [False, 0, StaffMember(name = "user", id = 0, perm = 0, staff_id = 0)]
    certified = await do_index_query(state = 6, limit = None) # State 0 and state 6 are approved and certified
    bot_amount = await db.fetchval("SELECT COUNT(1) FROM bots WHERE state = 0 OR state = 6")
    queue = await do_index_query(state = 1, limit = None, add_query = "ORDER BY created_at ASC")
    under_review = await do_index_query(state = enums.BotState.under_review, limit = None, add_query = "ORDER BY created_at ASC")
    denied = await do_index_query(state = 2, limit = None, add_query = "ORDER BY created_at ASC")
    banned = await do_index_query(state = 4, limit = None, add_query = "ORDER BY created_at ASC")
    data = {"certified": certified, "bot_amount": bot_amount, "queue": queue, "denied": denied, "banned": banned, "under_review": under_review, "admin": staff[1] == 4, "mod": staff[1] == 3, "owner": staff[1] == 5, "bot_review": staff[1] == 2, "perm": staff[2].name}
    if str(request.url.path).startswith("/api"): # Check for API
        return data # Return JSON if so
    return await templates.TemplateResponse("admin.html", {"request": request} | data) # Otherwise, render the template

@router.post("/console")
async def admin_api(request: Request, bt: BackgroundTasks, admin: str = FForm(""), bot_id: int = FForm(0)):
    logger.debug(f"Got admin task request for {bot_id}")
    try:
        guild = client.get_guild(main_server)
        user = guild.get_member(int(request.session["user_id"]))
    except:
        return HTMLResponse("Discord API is down right now")
    if user is None:
        return RedirectResponse("/")
    if not is_staff(staff_roles, user.roles, 5)[0]:
        return RedirectResponse("/admin/console", status_code = 303) 
    admin_tool = BotListAdmin(bot_id, int(request.session["user_id"]))
    if admin=="certify":
        rc = await admin_tool.certify_bot()
        if rc is not None:
            return rc
        
        return await templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope it certified the bot!", "username": request.session.get("username", False)})
    elif admin=="uncertify":
        rc = await admin_tool.uncertify_bot()
        if rc is not None:
            return rc

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
    if "user_id" not in request.session.keys():
        return RedirectResponse("/")
    guild = client.get_guild(main_server)
    user = guild.get_member(int(request.session["user_id"]))
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
async def review_tool(request: Request, bot_id: int, task: str = FForm(""), feedback: str = FForm("")):
    if "user_id" not in request.session.keys():
        return RedirectResponse("/")
    guild = client.get_guild(main_server)
    if guild is None:
        return HTMLResponse("We are currently connecting to Discord, please wait")
    user = guild.get_member(int(request.session["user_id"])) 
    s = is_staff(staff_roles, user.roles, 2)
    bot = await get_bot(bot_id)
    
    if not s[0] or not bot:
        return RedirectResponse("/")

    admin_tool = BotListAdmin(bot_id, int(request.session["user_id"]))
    
    def _feedback(default_feedback):
        return feedback if feedback else default_feedback

    match task:
        case "approve":
            feedback = _feedback(approve_feedback)
            rc = await admin_tool.approve_bot(feedback)
            message = f"Bot accepted; You MUST Invite it by clicking <a href='https://discord.com/oauth2/authorize?client_id={bot_id}&scope=bot&guild_id={guild.id}&disable_guild_select=true&permissions=0' class='long-desc-link'>here</a>"
        case "deny":
            feedback = _feedback(deny_feedback)
            rc = await admin_tool.deny_bot(feedback)
            message = "Bot denied. Please carry on with your day"
        case "unverify":
            feedback = _feedback("This is likely due to it breaking Discord ToS or our rules")
            rc = await admin_tool.unverify_bot(feedback)
            message = "Bot unverified. Please carry on with your day"
        case "claim":
            rc = await admin_tool.claim_bot()
            message = "Claimed bot"
        case "unclaim":
            rc = await admin_tool.unclaim_bot()
            message = "Unclaimed bot!"
        case _:
            return "Invalid task!"
    if rc:
        return rc
    elif rc is False:
        return RedirectResponse("/admin/console")
    return await templates.TemplateResponse("message.html",{"request":request, "message": message})
