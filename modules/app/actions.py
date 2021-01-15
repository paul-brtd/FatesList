from ..deps import *

router = APIRouter(
    prefix = "/bot",
    tags = ["Actions"]
)

@router.get("/admin/add")
@csrf_protect
async def add_bot(request: Request):
    if "userid" in request.session.keys():
        if request.method == "GET":
            # TAGS
            tags_fixed = {}
            for tag in TAGS:
                new_tag = tag.replace("_", " ")
                tags_fixed.update({tag: new_tag.capitalize()})
            form = await Form.from_formdata(request)
            return templates.TemplateResponse("add.html", {"request": request, "tags_fixed": tags_fixed, "username": request.session.get("username", False),"form":form})
        else:
            owner_check = await get_user(request.session["userid"])
            if owner_check:
                pass
            else:
                return templates.TemplateResponse("message.html", {"request": request, "message": "You are not in the support server", "username": request.session.get("username", False), "avatar": request.session.get("avatar")})
    else:
        return RedirectResponse("/")

#     await db.execute("INSERT INTO bots(bot_id,prefix,bot_library,invite,website,banner,discord,long_description,description,tags,owner,extra_owners,votes,servers,shard_count,created_at,queue_username,queue_avatar) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$15,$16,$17)", int(form["bot_id"]), form["prefix"], form["library"], form["invite"], form["website"], banner, form["support"], form["long_description"], form.description, selected_tags, int(request.session["userid"]), form.extra_owners, 0, 0, int(creation),bot_object.name,str(bot_object.avatar_url))

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
        banner: str = FForm(""),
        extra_owners: str = FForm(""),
        support: Optional[str] = FForm(""),
        long_description: str = FForm("")
    ):
    if bot_id == "" or prefix == "" or invite == "" or description == "" or long_description == "":
        return {"error": "Invalid Arguments"}
    fetch = await db.fetch("SELECT bot_id FROM bots WHERE bot_id = $1", bot_id)
    if fetch:
        return templates.TemplateResponse("message.html", {"request": request, "message": "Bot already exists.", "username": request.session.get("username", False)})

    if invite.startswith("https://discord.com/api/oauth2"):
        pass
    else:
        return templates.TemplateResponse("message.html", {"request": request, "message": "Invalid Bot Invite", "username": request.session.get("username", False)})
    description = description.replace("\n", " ").replace("\t", " ")
    if len(description) > 101:
        return templates.TemplateResponse("message.html", {"request": request, "message": "Short description is too long.", "username": request.session.get("username", False)})
    try:
        bot_object = await get_bot(bot_id)
    except:
        return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist", "username": request.session.get("username", False)})
    if not bot_object:
        return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist", "username": request.session.get("username", False)})
    if tags == "":
        return templates.TemplateResponse("message.html", {"request": request, "message": "You need to select tags for your bot", "username": request.session.get("username", False)})
    selected_tags = tags.split(",")
    for test in selected_tags:
        if test in TAGS:
            pass
        else:
            return templates.TemplateResponse("message.html", {"request": request, "message": "One of your bot tags didn't exist internally", "username": request.session.get("username", False)})
    creation = time.time()
    bt.add_task(add_bot_bt, request, bot_id, prefix, library, website, banner, support, long_description, description, selected_tags, extra_owners, creation, bot_object, invite)
    return templates.TemplateResponse("message.html", {"request": request, "message": "Bot has been added.", "username": request.session.get("username", False)})


async def add_bot_bt(request, bot_id, prefix, library, website, banner, support, long_description, description, selected_tags, extra_owners, creation, bot_object, invite):
    await db.execute("INSERT INTO bots(bot_id,prefix,bot_library,invite,website,banner,discord,long_description,description,tags,owner,extra_owners,votes,servers,shard_count,created_at,api_token) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)", bot_id, prefix, library, invite, website, banner, support, long_description, description, selected_tags, int(request.session["userid"]), extra_owners, 0, 0, 0, int(creation), get_token(101))
    await add_event(bot_id, "add_bot", "NULL")
    channel = client.get_channel(bot_logs)
    owner=str(request.session["userid"])
    bot_name = bot_object["username"]
    await channel.send(f"<@{owner}> added the bot <@{bot_id}>({bot_name}) to queue")


@router.get("/edit/{bid}")
@csrf_protect
async def bot_edit(request: Request, bid: int):
    if "userid" in request.session.keys():
        check = await db.fetchrow("SELECT owner,extra_owners FROM bots WHERE bot_id = $1", bid)
        if not check:
            return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database.", "username": request.session.get("username", False)})
        if check["owner"] == int(request.session["userid"]) or str(request.session["userid"]) in check["extra_owners"]:
            pass
        else:
            return templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "username": request.session.get("username", False), "avatar": request.session.get("avatar")})
        tags_fixed = {}
        for tag in TAGS:
            new_tag = tag.replace("_", " ")
            tags_fixed.update({tag: new_tag.capitalize()})
        form = await Form.from_formdata(request)
        fetch = await db.fetchrow("SELECT bot_id, prefix, bot_library, invite, website, banner, discord, long_description, description, tags, owner, extra_owners, servers, created_at, webhook, discord, api_token, banner FROM bots WHERE bot_id = $1", bid)
        return templates.TemplateResponse("edit.html", {"request": request, "tags_fixed": tags_fixed, "username": request.session.get("username", False),"fetch":fetch,"form":form})
    else:
        return RedirectResponse("/")

@router.post("/edit/{bid}")
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
        webhook: str = FForm("")
    ):
    if "userid" in request.session.keys():
        check = await db.fetchrow("SELECT owner, extra_owners FROM bots WHERE bot_id = $1", bid)
        if not check:
            return templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database.", "username": request.session.get("username", False)})
        if check["owner"] == int(request.session["userid"]) or str(request.session["userid"]) in check["extra_owners"]:
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
    if invite.startswith("https://discord.com/api/oauth2"):
        pass
    else:
        return templates.TemplateResponse("message.html", {"request": request, "message": "Invalid Bot Invite", "username": request.session.get("username", False)})

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
    creation = time.time()
    bt.add_task(edit_bot_bt, request, bid, prefix, library, website, banner, support, long_description, description, selected_tags, extra_owners, creation, invite, webhook)
    return templates.TemplateResponse("message.html", {"request": request, "message": "Bot has been edited.", "username": request.session.get("username", False), "avatar": request.session.get('avatar')}) 

async def edit_bot_bt(request, botid, prefix, library, website, banner, support, long_description, description, selected_tags, extra_owners, creation, invite, webhook):
    await db.execute("UPDATE bots SET bot_library=$2, webhook=$3, description=$4, long_description=$5, prefix=$6, website=$7, discord=$8, tags=$9, banner=$10, owner=$11, extra_owners=$12, invite=$13 WHERE bot_id = $1", botid, library, webhook, description, long_description, prefix, website, support, selected_tags, banner, int(request.session["userid"]), extra_owners, invite)
    await add_event(botid, "edit_bot", f"user:{str(request.session['userid'])}")
    channel = client.get_channel(bot_logs)
    owner=str(request.session["userid"])
    await channel.send(f"<@{owner}> edited the bot <@{botid}>")

@router.post("/{bot_id}/vote")
async def vote_bot(
        request: Request,
        bot_id: int
    ):
    pass
