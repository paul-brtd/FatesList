from ..core import *

router = APIRouter(
    prefix = "/bot",
    tags = ["Actions"],
    include_in_schema = False
)

allowed_file_ext = [".gif", ".png", ".jpeg", ".jpg", ".webm", ".webp"]

@router.get("/admin/add")
async def add_bot(request: Request):
    if "user_id" in request.session.keys():
        return await templates.TemplateResponse("bot_add_edit.html", {"request": request, "tags_fixed": tags_fixed, "features": features, "mode": "add"})
    else:
        return RedirectResponse("/auth/login?redirect=/bot/admin/add&pretty=to add a bot")

@router.get("/{bot_id}/settings")
async def bot_settings_page(request: Request, bot_id: int):
    if "user_id" in request.session.keys():
        check = await is_bot_admin(int(bot_id), int(request.session.get("user_id")))
        if not check:
            return abort(403)
        try:
            fetch = dict(await db.fetchrow("SELECT bot_id, prefix, bot_library AS library, invite, website, banner, long_description, description, webhook, webhook_secret, webhook_type, discord AS support, api_token, banner, github, features, long_description_type, css, donate, privacy_policy, nsfw FROM bots WHERE bot_id = $1", bot_id))
        except:
            return abort(404)
        tags = await db.fetch("SELECT tag FROM bot_tags WHERE bot_id = $1", bot_id)
        fetch = fetch | {"tags": [tag["tag"] for tag in tags]}
        owners = await db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", bot_id)
        logger.trace(owners)
        if owners is None:
            return "This bot has no found owners.\nPlease contact Fates List support"
        fetch = fetch | {"extra_owners": [obj["owner"] for obj in owners if obj["main"] is False]}
        if fetch["extra_owners"]:
            fetch["extra_owners"] = ",".join([str(eo) for eo in fetch["extra_owners"]])
        else:
            fetch["extra_owners"] = ""
        vanity = await db.fetchrow("SELECT vanity_url AS vanity FROM vanity WHERE redirect = $1", bot_id)
        if vanity is None:
            vanity = {"vanity": None}
        bot = fetch | dict(vanity)
        return await templates.TemplateResponse("bot_add_edit.html", {"request": request, "mode": "edit", "tags_fixed": tags_fixed, "username": request.session.get("username", False),"data": bot, "avatar": request.session.get("avatar"), "epoch": time.time(), "vanity": vanity["vanity"], "features": features})
    else:
        return RedirectResponse("/")

@router.post("/{bot_id}/reviews/new")
async def new_reviews(request: Request, bot_id: int, bt: BackgroundTasks, rating: float = FForm(5.1), review: str = FForm(...)):
    if "user_id" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to review this bot", status_code = 303)
    check = await db.fetchrow("SELECT bot_id FROM bot_reviews WHERE bot_id = $1 AND user_id = $2 AND reply = false", bot_id, int(request.session["user_id"]))
    if check is not None:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "You have already made a review for this bot, please edit that one instead of making a new one!"})
    id = uuid.uuid4()
    await db.execute("INSERT INTO bot_reviews (id, bot_id, user_id, star_rating, review_text, epoch) VALUES ($1, $2, $3, $4, $5, $6)", id, bot_id, int(request.session["user_id"]), rating, review, [time.time()])
    await bot_add_event(bot_id, enums.APIEvents.review_add, {"user": str(request.session["user_id"]), "reply": False, "id": str(id), "star_rating": rating, "review": review, "root": None})
    return await templates.TemplateResponse("message.html", {"request": request, "message": f"Successfully made a review for this bot!<script>window.location.replace('/bot/{bot_id}')</script>"}) 

@router.post("/{bot_id}/reviews/{rid}/edit")
async def edit_review(request: Request, bot_id: int, rid: uuid.UUID, bt: BackgroundTasks, rating: float = FForm(5.1), review: str = FForm(...)):
    if "user_id" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to edit reviews", status_code = 303)
    guild = client.get_guild(main_server)
    user = guild.get_member(int(request.session["user_id"]))
    s = is_staff(staff_roles, user.roles, 2)
    if s[0]:
        check = await db.fetchrow("SELECT epoch, reply FROM bot_reviews WHERE id = $1", rid)
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to edit this review (doesn't actually exist)"})
    else:
        check = await db.fetchrow("SELECT epoch, reply FROM bot_reviews WHERE id = $1 AND bot_id = $2 AND user_id = $3", rid, bot_id, int(request.session["user_id"]))
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to edit this review"})
    if check["epoch"] is not None:
        check["epoch"].append(time.time())
        epoch = check["epoch"]
    else:
        epoch = [time.time()]
    await db.execute("UPDATE bot_reviews SET star_rating = $1, review_text = $2, epoch = $3 WHERE id = $4", rating, review, epoch, rid)
    await bot_add_event(bot_id, enums.APIEvents.review_edit, {"user": str(request.session["user_id"]), "id": str(rid), "star_rating": rating, "review": review, "reply": check["reply"]})
    return await templates.TemplateResponse("message.html", {"request": request, "message": f"Successfully editted your/this review for this bot!<script>window.location.replace('/bot/{bot_id}')</script>"})

@router.post("/{bot_id}/reviews/{rid}/reply")
async def edit_review(request: Request, bot_id: int, rid: uuid.UUID, bt: BackgroundTasks, rating: float = FForm(5.1), review: str = FForm(...)):
    if "user_id" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to reply to reviews", status_code = 303)
    check = await db.fetchrow("SELECT replies FROM bot_reviews WHERE id = $1", rid)
    if check is None:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to reply to this review (doesn't actually exist)"})
    reply_id = uuid.uuid4()
    await db.execute("INSERT INTO bot_reviews (id, bot_id, user_id, star_rating, review_text, epoch, reply) VALUES ($1, $2, $3, $4, $5, $6, $7)", reply_id, bot_id, int(request.session["user_id"]), rating, review, [time.time()], True)
    replies = check["replies"]
    replies.append(reply_id)
    await db.execute("UPDATE bot_reviews SET replies = $1 WHERE id = $2", replies, rid)
    await bot_add_event(bot_id, enums.APIEvents.review_add, {"user": str(request.session["user_id"]), "reply": True, "id": str(reply_id), "star_rating": rating, "review": review, "root": str(rid)})
    return await templates.TemplateResponse("message.html", {"request": request, "message": f"Successfully replied to your/this review for this bot!<script>window.location.replace('/bot/{bot_id}')</script>"})

@router.get("/{bot_id}/resubmit")
async def resubmit_bot(request: Request, bot_id: int):
    if "user_id" in request.session.keys():
        check = await is_bot_admin(bot_id, int(request.session.get("user_id")))
        if not check:
            return abort(403)
    else:
        return RedirectResponse("/")
    bot = await get_bot(bot_id)
    if not bot:
        return abort(404)
    return await templates.TemplateResponse("resubmit.html", {"request": request, "bot": bot, "bot_id": bot_id})

@router.post("/{bot_id}/resubmit")
async def resubmit_bot(request: Request, bot_id: int, appeal: str = FForm(...), qtype: str = FForm("off")):
    if "user_id" in request.session.keys():
        check = await is_bot_admin(bot_id, int(request.session.get("user_id")))
        if not check:
            return abort(403)
    else:
        return RedirectResponse("/")
    bot = await get_bot(bot_id)
    if bot is None:
        return abort(404)
    resubmit = qtype == "on"
    reschannel = client.get_channel(appeals_channel)
    if resubmit:
        title = "Bot Resubmission"
        type = "Context"
    else:
        title = "Ban Appeal"
        type = "Appeal"
    resubmit_embed = discord.Embed(title=title, color=0x00ff00)
    resubmit_embed.add_field(name="Username", value = bot['username'])
    resubmit_embed.add_field(name="Bot ID", value = str(bot_id))
    resubmit_embed.add_field(name="Resubmission", value = str(resubmit))
    resubmit_embed.add_field(name=type, value = appeal)
    await reschannel.send(embed = resubmit_embed)
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Appeal sent successfully!."})

