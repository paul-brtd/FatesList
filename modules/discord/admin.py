from ..core import *

router = APIRouter(
    prefix = "/admin",
    tags = ["Admin"],
    include_in_schema = False
)

@router.get("/console")
async def admin_dashboard(request: Request, stats: Optional[int] = 0):
    if "userid" in request.session.keys() or stats == 1:
        if "userid" in request.session.keys() and stats != 1:
            guild = client.get_guild(main_server)
            if guild is None:
                return await templates.e(request, "Connecting to Discord API, please wait")
            user = guild.get_member(int(request.session["userid"]))
            if user is None:
                return RedirectResponse("/", status_code = 303)
            staff = is_staff(staff_roles, user.roles, 2)
            if not staff[0]:
                return RedirectResponse("/", status_code = 303)
        certified_bots = len(await db.fetch("SELECT bot_id FROM bots WHERE certified = true"))
        bots = await db.fetchrow("SELECT COUNT(1) FROM bots WHERE queue_state = 0 AND banned = false")
        bots = bots["count"]
        queue = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite,banned FROM bots WHERE queue_state = 1 AND banned = false")
        print(queue)
        banned = await db.fetch("SELECT description, banner,certified,votes,servers,bot_id,invite FROM bots WHERE banned = true OR queue_state = 2")
        queue_bots = await parse_bot_list(queue)
        banned = await parse_bot_list(banned)
        queue_amount = len(queue)
        form = await Form.from_formdata(request)
        return await templates.TemplateResponse("admin_stats.html",{"request": request, "cert": certified_bots,"bots": bots, "queue_bots": queue_bots, "queue_amount": queue_amount, "admin": stats != 1 and staff[1] == 4, "mod": stats != 1 and staff[1] == 3, "owner": stats != 1 and staff[1] == 5, "bot_review": stats != 1 and staff[1] == 2, "form": form, "banned": banned, "stats": stats == 1})
    else:
        return RedirectResponse("/", status_code = 303)

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
    if admin=="certify":
        users = await db.fetchrow("SELECT owner FROM bot_owner WHERE bot_id = $1", bot_id)
        if users is None:
            return RedirectResponse("/admin/console", status_code = 303)
        await db.execute("UPDATE bots SET certified = true WHERE bot_id = $1", bot_id)
        eo = users["owner"]
        for user in eo:
            await db.execute("UPDATE users SET certified = true WHERE user_id = $1", int(user))
        channel = client.get_channel(bot_logs)
        owner=str(request.session["userid"])
        await channel.send(f"<@{owner}> certified the bot <@{bot_id}>")
        return await templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope it certified the bot!", "username": request.session.get("username", False)})
    elif admin=="uncertify":
        await db.execute("UPDATE bots SET certified = false WHERE bot_id = $1", bot_id)
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
    await db.execute("UPDATE users SET vote_epoch = 0")

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
    await db.execute("UPDATE users SET banned = $1 WHERE user_id = $2", ban_type, user_id)
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Banned User Successfully"})


@router.post("/review/{bot_id}")
async def review_tool(request: Request, bot_id: int, accept: str = FForm(""), deny_reason: str = FForm("There was no reason specified. DM/Ping the mod who banned your bot to learn why it was banned"), accept_feedback: str = FForm("There was no feedback given for this bot. It was likely a good bot, but you can ask any staff member about feedback if you wish."), unverify_reason: str = FForm("This is likely due to it breaking Discord ToS or our rules")):
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
        if rc is False:
            return RedirectResponse("/admin/console")
        return await templates.TemplateResponse("last.html",{"request":request,"message":"Bot accepted; You MUST Invite it by this url","username":request.session["username"],"url":f"https://discord.com/oauth2/authorize?client_id={str(bot_id)}&scope=bot&guild_id={guild.id}&disable_guild_select=true&permissions=0"})
    elif accept == "unverify":
        rc = await admin_tool.unverify_bot(unverify_reason)
        if rc is False:
            return RedirectResponse("/admin/console")
        return await templates.TemplateResponse("message.html",{"request":request,"message":"Bot unverified. Please carry on with your day"})
    elif accept == "false":
        rc = await admin_tool.deny_bot(deny_reason)
        if rc is False:
            return RedirectResponse("/admin/console")
        return await templates.TemplateResponse("message.html",{"request":request,"message":"Bot denied. Please carry on with your day"})
    else:
        return RedirectResponse("/")
