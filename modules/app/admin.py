from ..deps import *

router = APIRouter(
    prefix = "/admin",
    tags = ["Admin"]
)

@router.get("/")
@csrf_protect
async def admin(request:Request):
    if "userid" in request.session.keys():
        guild = client.get_guild(reviewing_server)
        user = guild.get_member(int(request.session["userid"]))
        staff = is_staff(staff_roles, user.roles, 2)
        if not staff[0]:
            return RedirectResponse("/")
        certified_bots = len(await db.fetch("SELECT bot_id FROM bots WHERE certified = true"))
        bots = len(await db.fetch("SELECT bot_id FROM bots WHERE queue = false"))
        fetch = await db.fetch("SELECT queue_username, queue_avatar, votes, servers, description FROM bots WHERE queue = true")
        print(staff[1])
        queue_bots = []
        queue_amount = len(fetch)
        form = await Form.from_formdata(request)
        # TOP VOTED BOTS
        for bot in fetch:
            bot_info = {"username": bot["queue_username"], "avatar": bot["queue_avatar"], "form": form}
            if bot_info:
                queue_bots.append({"bot": bot, "avatar": bot_info["avatar"], "username": bot_info["username"], "votes": await human_format(bot["votes"]), "servers": await human_format(bot["servers"]), "description": bot["description"], "form": form})
        return templates.TemplateResponse("admin.html",{"request": request, "cert": certified_bots,"bots": bots, "queue_bots": queue_bots, "queue_amount": queue_amount, "admin": staff[1] == 4, "mod": staff[1] == 3, "owner": staff[1] == 5, "bot_review": staff[1] == 2, "username": request.session["username"], "form": form})
    else:
        return RedirectResponse("/")

@router.post("/")
@csrf_protect
async def admin_api(request:Request, admin: str = FForm(""), bot_id: int = FForm(0)):
    print(bot_id)
    guild = client.get_guild(reviewing_server)
    user = guild.get_member(int(request.session["userid"]))
    if not is_staff(staff_roles, user.roles, 2):
        return RedirectResponse("/") 
    if admin=="certify":
        await db.execute("UPDATE bots SET certified = true WHERE bot_id = $1", bot_id)
        channel = client.get_channel(bot_logs)
        owner=str(request.session["userid"])
        await channel.send(f"<@{owner}> certified the bot <@{bot_id}>")
        return templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope it certified the bot!", "username": request.session.get("username", False)})
    elif admin=="uncertify":
        await db.execute("UPDATE bots SET certified = false WHERE bot_id = $1", bot_id)
        channel = client.get_channel(bot_logs)
        owner=str(request.session["userid"])
        await channel.send(f"<@{owner}> uncertified the bot <@{bot_id}>")
        return templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope it uncertified the bot!", "username": request.session.get("username", False)})
    elif admin=="reset":
        if not is_staff(staff_roles, user.roles, 4):
            return RedirectResponse("/admin")
        await db.execute("UPDATE bots SET votes = 0")
        return templates.TemplateResponse("message.html", {"request": request, "message": "Hey mikes, i hope your wish comes true ;)", "username": request.session.get("username", False)})
    else:
        return RedirectResponse("/admin")

@router.get("/review/{bot_id}")
async def review(request:Request, bot_id: int):
    if "userid" in request.session.keys():
        guild = client.get_guild(reviewing_server)
        user = guild.get_member(int(request.session["userid"]))
        s = is_staff(staff_roles, user.roles, 2)
        if not s[0]:
            return RedirectResponse("/")
        bot = await db.fetchrow("SELECT * FROM bots WHERE bot_id = $1 and queue=true", bot_id)
        if not bot:
            return templates.TemplateResponse("message.html",{"request":request,"message":"Bot does not exist! Idk how","username":request.session["username"]})
        form = await Form.from_formdata(request)
        return templates.TemplateResponse("review.html",{"request": request, "bot": bot, "guild": test_server, "form": form})
    else:
        return RedirectResponse("/") 

@router.post("/review/{bot_id}")
async def review_api(request:Request, bot_id: int, accept: str = FForm("")):
    guild = client.get_guild(reviewing_server)
    user = guild.get_member(int(request.session["userid"]))
    s = is_staff(staff_roles, user.roles, 2)
    if not s[0]:
        return RedirectResponse("/")                
    elif accept == "true":
        api_token = get_token(64)
        await db.execute("UPDATE bots SET queue=false,api_token=$1 WHERE bot_id = $2", api_token, bot_id)
        channel = guild.get_channel(bot_logs)
        await channel.send(f"<@{bot_id}> has been approved")
        return templates.TemplateResponse("last.html",{"request":request,"message":"Bot accepted; You MUST Invite it by this url","username":request.session["username"],"url":f"https://discord.com/oauth2/authorize?client_id={str(bot_id)}&scope=bot&guild_id={guild}&disable_guild_select=true&permissions=0"})
    elif accept == "false":
        return RedirectResponse("/admin/review/"+str(bot_id)+"/deny", status_code=HTTP_303_SEE_OTHER)
    else:
        return RedirectResponse("/")

@router.get("/review/{bot_id}/deny")
async def review_deny(request:Request, bot_id: int):
    if "userid" in request.session.keys():
        form = await Form.from_formdata(request)
        guild = client.get_guild(reviewing_server)
        user = guild.get_member(int(request.session["userid"]))
        s = is_staff(staff_roles, user.roles, 2)
        if not s[0]:
            return RedirectResponse("/")            
        else:    
            bot = await db.fetchrow("SELECT * FROM bots WHERE bot_id = $1 and queue=true",int(bot_id))
            if not bot:
                return templates.TemplateResponse("message.html",{"request":request,"message":"Bot does not exist! Idk how"})
            return templates.TemplateResponse("last_deny.html",{"request":request,"bot":bot,"username":request.session["username"], "form": form})

@router.post("/review/{bot_id}/deny")
async def review_deny_api(request:Request, bot_id: str, reason: str = FForm("There was no reason specified")):
    guild = client.get_guild(reviewing_server)
    user = guild.get_member(int(request.session["userid"]))
    s = is_staff(staff_roles, user.roles, 2)
    if not s[0]:
        return RedirectResponse("/")
    else:
        check = await db.fetchrow("SELECT * FROM bots WHERE bot_id=$1 and queue=true",int(bot_id))
        if not check:
                return templates.TemplateResponse("message.html",{"request":request,"message":"Bot does not exist! Idk how"})
        channel = client.get_channel(bot_logs)
        deny = await db.execute("DELETE FROM bots WHERE bot_id = $1", int(bot_id))
        channel = client.get_channel(bot_logs)
        owner=str(request.session["userid"])
        await channel.send(f"<@{owner}> denied the bot <@{bot_id}> with the reason: {reason}")
        return templates.TemplateResponse("message.html",{"request":request,"message":"I hope it DENIED the bot review GUY","username":request.session["username"]})
