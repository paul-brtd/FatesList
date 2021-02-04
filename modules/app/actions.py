from ..deps import *

router = APIRouter(
    prefix = "/bot",
    tags = ["Actions"],
    include_in_schema = False
)

@router.get("/admin/add")
@csrf_protect
async def add_bot(request: Request):
    if "userid" in request.session.keys():
        form = await Form.from_formdata(request)
        if request.method == "GET":
            # TAGS
            tags_fixed = {}
            for tag in TAGS:
                new_tag = tag.replace("_", " ")
                tags_fixed.update({tag: new_tag.capitalize()})
            return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": {"form": form}, "error": None, "mode": "add"})
        else:
            owner_check = await get_user(request.session["userid"])
            if owner_check:
                pass
            else:
                return templates.TemplateResponse("message.html", {"request": request, "message": "Something has went wrong getting your account. Please join our support server and contact us there"})
    else:
        request.session["RedirectResponse"] = "/bot/admin/add"
        return RedirectResponse("/auth/login")


@router.post("/admin/add")
@csrf_protect
async def add_bot_api(
        request: Request,
        bt: BackgroundTasks, 
        bot_id: int = FForm(""),
        prefix: str = FForm(""),
        library: Optional[str] = FForm(""),
        invite: str = FForm(""),
        website: Optional[str] = FForm(""),
        description: str = FForm(""),
        tags: str = FForm(""),
        banner: str = FForm("none"),
        extra_owners: str = FForm(""),
        support: Optional[str] = FForm(""),
        long_description: str = FForm(""),
        custom_prefix: str = FForm("off"),
        open_source: str = FForm("off")
    ):
    guild = client.get_guild(reviewing_server)
    bot_dict = locals()
    bot_dict["request"] = None
    bot_dict["bt"] = None
    bot_dict["form"] = await Form.from_formdata(request)
    # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})
    if bot_id == "" or prefix == "" or invite == "" or description == "" or long_description == "" or len(prefix) > 9:
        return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": "Please ensure you have filled out all the required fields and that your prefix is less than 9 characters.", "mode": "add"})
    fetch = await db.fetch("SELECT bot_id FROM bots WHERE bot_id = $1", bot_id)
    if fetch:
        return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": "This bot already exists on Fates List", "mode": "add"})
    if invite.startswith("https://discord.com") and "oauth" in invite:
        pass
    else:
        return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": "Invalid Bot Invite: Your bot invite must be in the format of https://discord.com/api/oauth2... or https://discord.com/oauth2...", "mode": "add"})
    if len(description) > 101:
        return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": "Your short description must be shorter than 100 characters", "mode": "add"})
    description = description.replace("\n", " ").replace("\t", " ")
    try:
        bot_object = await get_bot(bot_id)
    except:
        return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours.", "mode": "add"})
    if not bot_object:
        return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours.", "mode": "add"})
    if tags == "":
        return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": "You must select tags for your bot", "mode": "add"})
    selected_tags = tags.split(",")
    for test in selected_tags:
        if test in TAGS:
            pass
        else:
            return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": "One of your tags doesn't exist internally. Please choose a different tags", "mode": "add"})
    creation = time.time()
    if extra_owners == "":
        extra_owners = None
    else:
        try:
            extra_owners = [int(id) for id in extra_owners.split(",")]
        except:
            return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": "One of your extra owners doesn't exist or you haven't comma-seperated them.", "mode": "add"})
    # Feature check + add
    features = [f for f in bot_dict.keys() if bot_dict[f] == "on" and f in ["custom_prefix", "open_source"]]
    bt.add_task(add_bot_bt, request, bot_id, prefix, library, website, banner, support, long_description, description, selected_tags, extra_owners, creation, bot_object, invite, features)
    return RedirectResponse("/bot/" + str(bot_id), status_code = 303)

async def add_bot_bt(request, bot_id, prefix, library, website, banner, support, long_description, description, selected_tags, extra_owners, creation, bot_object, invite, features):
    await db.execute("INSERT INTO bots(bot_id,prefix,bot_library,invite,website,banner,discord,long_description,description,tags,owner,extra_owners,votes,servers,shard_count,created_at,api_token,features) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)", bot_id, prefix, library, invite, website, banner, support, long_description, description, selected_tags, int(request.session["userid"]), extra_owners, 0, 0, 0, int(creation), get_token(101), features)
    await add_event(bot_id, "add_bot", "NULL")
    owner=str(request.session["userid"])
    channel = client.get_channel(bot_logs)
    bot_name = bot_object["username"]
    await channel.send(f"<@{owner}> added the bot <@{bot_id}>({bot_name}) to queue")


@router.get("/{bid}/edit")
@csrf_protect
async def bot_edit(request: Request, bid: int):
    guild = client.get_guild(reviewing_server)
    if "userid" in request.session.keys():
        check = await db.fetchrow("SELECT owner,extra_owners FROM bots WHERE bot_id = $1", bid)
        if not check:
            return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database.", "username": request.session.get("username", False)})
        user = guild.get_member(int(request.session.get("userid")))
        if check["extra_owners"] is None:
            eo = []
        else:
            eo = check["extra_owners"]
        if check["owner"] == int(request.session["userid"]) or int(request.session["userid"]) in eo or (user is not None and is_staff(staff_roles, user.roles, 4)[0]):
            pass
        else:
            return templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "username": request.session.get("username", False), "avatar": request.session.get("avatar")})
        tags_fixed = {}
        for tag in TAGS:
            new_tag = tag.replace("_", " ")
            tags_fixed.update({tag: new_tag.capitalize()})
        form = await Form.from_formdata(request)
        fetch = await db.fetchrow("SELECT bot_id, prefix, bot_library AS library, invite, website, banner, long_description, description, tags, owner, extra_owners,  webhook, discord AS support, api_token, banner, banned, github, features FROM bots WHERE bot_id = $1", bid)
        vanity = await db.fetchrow("SELECT vanity_url AS vanity FROM vanity WHERE redirect = $1", bid)
        if vanity is None:
            vanity = {"vanity": None}
        bot = dict(fetch) | dict(vanity)
        bot["form"] = form
        return templates.TemplateResponse("add_edit.html", {"request": request, "mode": "edit", "tags_fixed": tags_fixed, "username": request.session.get("username", False),"data": bot, "avatar": request.session.get("avatar"), "epoch": time.time(), "vanity": vanity["vanity"]})
    else:
        return RedirectResponse("/")

@router.post("/{bid}/edit")
@csrf_protect
async def bot_edit_api(
        request: Request,
        bt: BackgroundTasks,
        bid: int,
        prefix: str = FForm(""),
        library: Optional[str] = FForm(""),
        invite: str = FForm(""),
        website: Optional[str] = FForm(""),
        description: str = FForm(""),
        tags: str = FForm(""),
        banner: str = FForm(""),
        extra_owners: str = FForm(""),
        support: Optional[str] = FForm(""),
        long_description: str = FForm(""),
        webhook: str = FForm(""),
        vanity: str = FForm(""),
        github: str = FForm(""),
        custom_prefix: str = FForm("off"),
        open_source: str = FForm("off")
    ):
    guild = client.get_guild(reviewing_server)
    bot_dict = locals()
    bot_dict["request"] = None
    bot_dict["bt"] = None
    bot_dict["form"] = await Form.from_formdata(request)
    # TAGS
    tags_fixed = {}
    for tag in TAGS:
        new_tag = tag.replace("_", " ")
        tags_fixed.update({tag: new_tag.capitalize()})
    if bid == "" or prefix == "" or invite == "" or description == "" or long_description == "" or len(prefix) > 9:
        return templates.TemplateResponse("add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": "Please ensure you have filled out all the required fields and that your prefix is less than 9 characters", "mode": "edit"})
    if "userid" in request.session.keys():
        check = await db.fetchrow("SELECT owner, extra_owners FROM bots WHERE bot_id = $1", bid)
        if not check:
            return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database.", "username": request.session.get("username", False)})
        user = guild.get_member(int(request.session.get("userid")))
        if check["extra_owners"] is None:
            eo = []
        else:
            eo = check["extra_owners"]
        if check["owner"] == int(request.session["userid"]) or int(request.session["userid"]) in eo or (user is not None and is_staff(staff_roles, user.roles, 4)[0]):    
            pass
        else:
            return templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "username": request.session.get("username", False)})
    else:
        return RedirectResponse("/")
    owner_check = await get_user(request.session["userid"])
    if owner_check:
        pass
    else:
        return templates.TemplateResponse("message.html", {"request": request, "message": "You are either not in the support server or you do not exist on the Discord API", "username": request.session.get("username", False)})
    if invite.startswith("https://discord.com") and "oauth" in invite:
        pass
    else:
        return templates.TemplateResponse("message.html", {"request": request, "message": "Invalid Bot Invite", "context": "Your bot invite must be in the format of https://discord.com/api/oauth2... or https://discord.com/oauth2...", "username": request.session.get("username", False)})
    description = description.replace("\n", " ").replace("\t", " ")
    if len(description) > 101:
        return templates.TemplateResponse("message.html", {"request": request, "message": "Short description is too long.", "username": request.session.get("username", False)})
    if tags == "":
        return templates.TemplateResponse("message.html", {"request": request, "message": "You need to select tags for your bot", "username": request.session.get("username", False)})
    selected_tags = tags.split(",")
    for test in selected_tags:
        if test in TAGS:
            pass
        else:
            return templates.TemplateResponse("message.html", {"request": request, "message": "One of your bot tags didn't exist internally", "username": request.session.get("username", False)})
    if vanity == "":
        pass
    else:
        vanity_check = await db.fetchrow("SELECT type FROM vanity WHERE vanity_url = $1 AND redirect != $2", vanity.replace(" ", "").lower(), bid)
        if vanity_check is not None or vanity.replace("", "").lower() in ["bot", "docs", "redoc", "doc", "profile", "server", "bots", "servers", "search", "invite", "discord", "login", "logout", "register", "admin"] or vanity.replace("", "").lower().__contains__("/"):
            return templates.TemplateResponse("message.html", {"request": request, "message": "Your custom vanity URL is already in use or is reserved"})
    if github != "" and not github.startswith("https://www.github.com"):
        return templates.TemplateResponse("message.html", {"request": request, "message": "Your github link must start with https://www.github.com", "username": request.session.get("username", False)})
    creation = time.time()
    if extra_owners == "":
        extra_owners = None
    else:
        try:
            extra_owners = [int(id) for id in extra_owners.split(",")]
        except:
            return templates.TemplateResponse("message.html", {"request": request, "message": "One of your extra owners is invalid"})
    features = [f for f in bot_dict.keys() if bot_dict[f] == "on" and f in ["custom_prefix", "open_source"]]
    print(features)
    bt.add_task(edit_bot_bt, request, bid, prefix, library, website, banner, support, long_description, description, selected_tags, extra_owners, creation, invite, webhook, vanity, github, features)
    return templates.TemplateResponse("message.html", {"request": request, "message": "Bot has been edited.<script>window.location.replace('/bot/" + str(bid) + "')</script>", "username": request.session.get("username", False), "avatar": request.session.get('avatar')}) 

async def edit_bot_bt(request, botid, prefix, library, website, banner, support, long_description, description, selected_tags, extra_owners, creation, invite, webhook, vanity, github, features):
    await db.execute("UPDATE bots SET bot_library=$2, webhook=$3, description=$4, long_description=$5, prefix=$6, website=$7, discord=$8, tags=$9, banner=$10, invite=$11, extra_owners = $12, github = $13, features = $14 WHERE bot_id = $1", botid, library, webhook, description, long_description, prefix, website, support, selected_tags, banner, invite, extra_owners, github, features)
    check = await db.fetchrow("SELECT vanity FROM vanity WHERE redirect = $1", botid)
    if check is None:
        print("am here")
        await db.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, vanity, botid)
    else:
        await db.execute("UPDATE vanity SET vanity_url = $1 WHERE redirect = $2", vanity, botid)
    await add_event(botid, "edit_bot", f"user:{str(request.session['userid'])}")
    channel = client.get_channel(bot_logs)
    owner=str(request.session["userid"])
    await channel.send(f"<@{owner}> edited the bot <@{botid}>")

@router.post("/{bot_id}/vote")
@csrf_protect
async def vote_for_bot(
        request: Request,
        bot_id: int
    ):
    if request.session.get("userid") is None:
        request.session["RedirectResponse"] = "/bot/" + str(bot_id)
        return RedirectResponse("/auth/login", status_code = 303)
    uid = request.session.get("userid")
    ret = await vote_bot(uid, request.session.get("username"), bot_id)
    if ret == []:
        return RedirectResponse("/bot/" + str(bot_id), status_code = 303)
    elif ret[0] in [404, 500]:
        return abort(ret[0])
    elif ret[0] == 401:
        wait_time = int(float(ret[1]))
        wait_time_hr = wait_time//(60*60)
        wait_time_mp = (wait_time - (wait_time_hr*60*60)) # Minutes
        wait_time_min = wait_time_mp//60
        wait_time_sec = (wait_time_mp - wait_time_min*60)
        if wait_time_min < 1:
            wait_time_min = 1
        if wait_time_hr == 1:
            hr = "hour"
        else:
            hr = "hours"
        if wait_time_min == 1:
            min = "minute"
        else:
            min = "minutes"
        if wait_time_sec == 1:
            sec = "second"
        else:
            sec = "seconds"
        wait_time_human = " ".join((str(wait_time_hr), hr, str(wait_time_min), min, str(wait_time_sec), sec))
        return templates.TemplateResponse("message.html", {"request": request, "username": request.session.get("username"), "avatar": request.session.get("avatar"), "message": "Vote Error", "context": "Please wait " + wait_time_human + " before voting for this bot"})
    else:
        return ret

@router.post("/{bot_id}/delete")
@csrf_protect
async def delete_bot(request: Request, bot_id: int, confirmer: str = FForm("1")):
    print(confirmer)
    guild = client.get_guild(reviewing_server)
    channel = client.get_channel(bot_logs)
    if "userid" in request.session.keys():
        check = await db.fetchrow("SELECT owner, extra_owners, banned FROM bots WHERE bot_id = $1", bot_id)
        if not check:
            return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database.", "username": request.session.get("username", False)})
        user = guild.get_member(int(request.session.get("userid")))
        if user is None:
            roles = []
        else:
            roles = user.roles
        if check["extra_owners"] is None:
            eo = []
        else:
            eo = check["extra_owners"]
        if check["owner"] == int(request.session["userid"]) or str(request.session["userid"]) in eo  or is_staff(staff_roles, roles, 4)[0]:
            pass
        else:
            return templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "context": "Only owners and admins can delete bots", "username": request.session.get("username", False)})
    else:
        return RedirectResponse("/", status_code = 303)
    if check["banned"] and not is_staff(staff_roles, user.roles, 4)[0]:
        return templates.TemplateResponse("message.html", {"request": request, "message": "Forbidden", "context": "Only Admins can delete banned bots", "username": request.session.get("username", False)})
    try:
        if time.time() - int(float(confirmer)) > 30:
            return templates.TemplateResponse("message.html", {"request": request, "username": request.session.get("username"), "avatar": request.session.get("avatar"), "message": "Forbidden", "context": "You have taken too long to click the Delete Bot button and for your security, you will need to go back, refresh the page and try again"})
    except:
        return templates.TemplateResponse("message.html", {"request": request, "username": request.session.get("username"), "avatar": request.session.get("avatar"), "message": "Forbidden", "context": "Invalid Confirm Code. Please go back and reload the page and if the problem still persists, please report it in the support server"})
    await add_event(bot_id, "delete_bot", f"user={str(request.session.get('userid'))}")
    owner = request.session.get("userid")
    await db.execute("DELETE FROM bots WHERE bot_id = $1", bot_id)
    await channel.send(f"<@{owner}> deleted the bot <@{str(bot_id)}>.\nWe are sad to see you go...::sad::")
    return RedirectResponse("/", status_code = 303)

@router.post("/ban/{bot_id}")
async def ban_bot(request: Request, bot_id: int, ban: int = FForm(1), reason: str = FForm('There was no reason specified')):
    guild = client.get_guild(reviewing_server)
    channel = client.get_channel(bot_logs)
    if ban not in [0, 1]:
        return RedirectResponse("/bot/" + str(bot_id), status_code = 303)
    if reason == "":
        reason = "There was no reason specified"

    if "userid" in request.session.keys():
        check = await db.fetchrow("SELECT owner, extra_owners, banned FROM bots WHERE bot_id = $1", bot_id)
        if not check:
            return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database.", "username": request.session.get("username", False)})
        user = guild.get_member(int(request.session.get("userid")))
        if is_staff(staff_roles, user.roles, 4)[0]:
            pass
        else:
            return templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "context": "Only admins can unban bots", "username": request.session.get("username", False)})
    if ban == 1:
        await channel.send("<@" + str(bot_id) + "> has been banned for reason: " + reason)
        try:
            await guild.kick((guild.get_member(bot_id)))
        except:
            pass
        await db.execute("UPDATE bots SET banned = true WHERE bot_id = $1", bot_id)
        await add_event(bot_id, "ban", f"user={str(request.session.get('userid'))}")
    else:
        await channel.send("<@" + str(bot_id) + "> has been unbanned")
        await db.execute("UPDATE bots SET banned = false WHERE bot_id = $1", bot_id)
        await add_event(bot_id, "unban", f"user={str(request.session.get('userid'))}")
    return RedirectResponse("/", status_code = 303)
