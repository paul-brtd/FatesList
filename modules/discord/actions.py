from ..deps import *

router = APIRouter(
    prefix = "/bot",
    tags = ["Actions"],
    include_in_schema = False
)

allowed_file_ext = [".gif", ".png", ".jpeg", ".jpg", ".webm", ".webp"]

@router.get("/admin/add")
@csrf_protect
async def add_bot(request: Request):
    if "userid" in request.session.keys():
        form = await Form.from_formdata(request)
        return await templates.TemplateResponse("bot_add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": {"form": form}, "error": None, "mode": "add"})
    else:
        return RedirectResponse("/auth/login?redirect=/bot/admin/add&pretty=to add a bot")


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
        css: str = FForm(""),
        custom_prefix: str = FForm("off"),
        open_source: str = FForm("off"),
        html_long_description: str = FForm("false"),
        donate: str = FForm("")
    ):
    if "userid" not in request.session.keys():
        return RedirectResponse("/auth/login?redirect=/bot/admin/add&pretty=to add a bot", status_code = 303)
    banner = banner.replace("http://", "https://").replace("(", "").replace(")", "")
    html_long_description = html_long_description == "true"
    guild = client.get_guild(main_server)
    bot_dict = locals()
    bot_dict["form"] = await Form.from_formdata(request)
    features = [f for f in bot_dict.keys() if bot_dict[f] == "on" and f in ["custom_prefix", "open_source"]]
    bot_dict["features"] = features
    bot_dict["user_id"] = request.session.get("userid")
    bot_adder = BotActions(**bot_dict)
    rc = await bot_adder.add_bot()
    if rc is None:
        return RedirectResponse("/bot/" + str(bot_id), status_code = 303)
    bot_dict["tags"] = bot_dict["tags"].split(",")
    return await templates.TemplateResponse("bot_add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": rc, "mode": "add"})
 

@router.get("/{bid}/edit")
@csrf_protect
async def bot_edit(request: Request, bid: int):
    if "userid" in request.session.keys():
        check = await is_bot_admin(int(bid), int(request.session.get("userid")))
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database.", "username": request.session.get("username", False)})
        elif check == False:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "username": request.session.get("username", False), "avatar": request.session.get("avatar")})
        form = await Form.from_formdata(request)
        fetch = dict(await db.fetchrow("SELECT bot_id, prefix, bot_library AS library, invite, website, banner, long_description, description, tags, owner, extra_owners, webhook, webhook_type, discord AS support, api_token, banner, banned, github, features, html_long_description, css, donate FROM bots WHERE bot_id = $1", bid))
        if fetch["extra_owners"]:
            fetch["extra_owners"] = ",".join([str(eo) for eo in fetch["extra_owners"]])
        else:
            fetch["extra_owners"] = ""
        vanity = await db.fetchrow("SELECT vanity_url AS vanity FROM vanity WHERE redirect = $1", bid)
        if vanity is None:
            vanity = {"vanity": None}
        bot = fetch | dict(vanity)
        bot["form"] = form
        return await templates.TemplateResponse("bot_add_edit.html", {"request": request, "mode": "edit", "tags_fixed": tags_fixed, "username": request.session.get("username", False),"data": bot, "avatar": request.session.get("avatar"), "epoch": time.time(), "vanity": vanity["vanity"]})
    else:
        return RedirectResponse("/")

@router.post("/{bot_id}/edit")
@csrf_protect
async def bot_edit_api(
        request: Request,
        bt: BackgroundTasks,
        bot_id: int,
        prefix: str = FForm(""),
        library: Optional[str] = FForm(""),
        invite: str = FForm(""),
        website: Optional[str] = FForm(""),
        description: str = FForm(""),
        tags: str = FForm(""),
        banner: str = FForm(""),
        extra_owners: str = FForm(""),
        css: str = FForm(""),
        support: Optional[str] = FForm(""),
        long_description: str = FForm(""),
        webhook: str = FForm(""),
        webhook_type: str = FForm(""),
        vanity: str = FForm(""),
        github: str = FForm(""),
        custom_prefix: str = FForm("off"),
        open_source: str = FForm("off"),
        html_long_description: str = FForm("false"),
        donate: str = FForm("")
    ):
    if "userid" not in request.session.keys():
        return RedirectResponse("/")
    banner = banner.replace("http://", "https://").replace("(", "").replace(")", "")
    html_long_description = html_long_description == "true"
    guild = client.get_guild(main_server)
    bot_dict = locals()
    bot_dict["form"] = await Form.from_formdata(request)
    features = [f for f in bot_dict.keys() if bot_dict[f] == "on" and f in ["custom_prefix", "open_source"]]
    bot_dict["features"] = features
    bot_dict["user_id"] = request.session.get("userid")
    bot_editor = BotActions(**bot_dict)
    rc = await bot_editor.edit_bot()
    if rc is None:
        return RedirectResponse("/bot/" + str(bot_id), status_code = 303)
    bot_dict["tags"] = bot_dict["tags"].split(",")
    return await templates.TemplateResponse("bot_add_edit.html", {"request": request, "tags_fixed": tags_fixed, "data": bot_dict, "error": rc, "mode": "edit"})

class RC(BaseModel):
    g_recaptcha_response: str = FForm(None)

@router.post("/{bot_id}/vote")
@csrf_protect
async def vote_for_bot_or_die(
        request: Request,
        bot_id: int,
    ):
    if request.session.get("userid") is None:
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to vote for this bot", status_code = 303)
    uid = request.session.get("userid")
    ret = await vote_bot(uid = uid, username = request.session.get("username"), bot_id = bot_id, autovote = False)
    print(ret)
    if ret == []:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully voted for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>", "username": request.session.get("username", False), "avatar": request.session.get('avatar')})
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
        return await templates.TemplateResponse("message.html", {"request": request, "username": request.session.get("username"), "avatar": request.session.get("avatar"), "message": "Vote Error", "context": "Please wait " + wait_time_human + " before voting for this bot"})
    else:
        return ret

@router.post("/{bot_id}/delete")
@csrf_protect
async def delete_bot(request: Request, bot_id: int, confirmer: str = FForm("1")):
    print(confirmer)
    guild = client.get_guild(main_server)
    channel = client.get_channel(bot_logs)
    if "userid" in request.session.keys():
        check = await is_bot_admin(int(bot_id), int(request.session.get("userid")))
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database."})
        elif check == False:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "context": "Only owners and admins can delete bots", "username": request.session.get("username", False)})
    else:
        return RedirectResponse("/", status_code = 303)
    try:
        if time.time() - int(float(confirmer)) > 30:
            return await templates.TemplateResponse("message.html", {"request": request, "username": request.session.get("username"), "avatar": request.session.get("avatar"), "message": "Forbidden", "context": "You have taken too long to click the Delete Bot button and for your security, you will need to go back, refresh the page and try again"})
    except:
        return await templates.TemplateResponse("message.html", {"request": request, "username": request.session.get("username"), "avatar": request.session.get("avatar"), "message": "Forbidden", "context": "Invalid Confirm Code. Please go back and reload the page and if the problem still persists, please report it in the support server"})
    await add_event(bot_id, "delete_bot", {"user": request.session.get('userid')})
    owner = request.session.get("userid")
    for table in "bots", "bot_voters", "bot_promotions", "bot_reviews", "api_event", "bot_maint", "bot_commands":
        await db.execute(f"DELETE FROM {table} WHERE bot_id = $1", bot_id)
    await db.execute("DELETE FROM vanity WHERE redirect = $1", bot_id)
    delete_embed = discord.Embed(title="Bot Deleted :(", description=f"<@{owner}> has deleted the bot <@{bot_id}>!", color=discord.Color.red())
    await channel.send(embed = delete_embed)
    return RedirectResponse("/", status_code = 303)

@router.post("/{bot_id}/ban")
@csrf_protect
async def ban_bot(request: Request, bot_id: int, ban: int = FForm(1), reason: str = FForm('There was no reason specified')):
    guild = client.get_guild(main_server)
    channel = client.get_channel(bot_logs)
    if ban not in [0, 1]:
        return RedirectResponse(f"/bot/{bot_id}", status_code = 303)
    if reason == "":
        reason = "There was no reason specified"

    if "userid" in request.session.keys():
        check = await db.fetchrow("SELECT owner, extra_owners, banned FROM bots WHERE bot_id = $1", bot_id)
        if not check:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "This bot doesn't exist in our database.", "username": request.session.get("username", False)})
        user = guild.get_member(int(request.session.get("userid")))
        if is_staff(staff_roles, user.roles, 3)[0]:
            pass
        else:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot.", "context": "Only owners, admins and moderators can unban bots. Please contact them if you accidentally denied a bot.", "username": request.session.get("username", False)})
    if ban == 1:
        ban_embed = discord.Embed(title="Bot Banned", description=f"<@{bot_id}> has been banned", color=discord.Color.red())
        ban_embed.add_field(name="Reason", value = reason)
        await channel.send(embed = ban_embed)
        try:
            await guild.kick((guild.get_member(bot_id)))
        except:
            pass
        await db.execute("UPDATE bots SET banned = true WHERE bot_id = $1", bot_id)
        await add_event(bot_id, "ban", {"user": request.session.get('userid')})
    else:
        unban_embed = discord.Embed(title="Bot Unbanned", description=f"<@{bot_id}> has been unbanned", color=0x00ff00)
        await channel.send(embed = unban_embed)
        await db.execute("UPDATE bots SET banned = false WHERE bot_id = $1", bot_id)
        await add_event(bot_id, "unban", {"user": request.session.get('userid')})
    return RedirectResponse("/", status_code = 303)

# CREATE TABLE bot_reviews (
#   id uuid primary key DEFAULT uuid_generate_v4(),
#   bot_id bigint not null,
#   star_rating float4 default 0.0,
#   review_text text,
#   review_upvotes integer default 0,
#   review_downvotes integer default 0,
#   flagged boolean default false,
#   epoch bigint
#);

async def base_rev_bt(bot_id, event, base_dict):
    reviews = await parse_reviews(bot_id)
    await add_event(bot_id, event, base_dict | {"reviews": reviews[0], "average_stars": reviews[1]})

@router.post("/{bot_id}/reviews/new")
async def new_reviews(request: Request, bot_id: int, bt: BackgroundTasks, rating: float = FForm(5.1), review: str = FForm("This is a placeholder review as the user has not posted anything...")):
    if "userid" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to review this bot", status_code = 303)
    check = await db.fetchrow("SELECT bot_id FROM bot_reviews WHERE bot_id = $1 AND user_id = $2 AND reply = false", bot_id, int(request.session["userid"]))
    if check is not None:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "You have already made a review for this bot, please edit that one instead of making a new one!"})
    id = uuid.uuid4()
    await db.execute("INSERT INTO bot_reviews (id, bot_id, user_id, star_rating, review_text, epoch) VALUES ($1, $2, $3, $4, $5, $6)", id, bot_id, int(request.session["userid"]), rating, review, [time.time()])
    bt.add_task(base_rev_bt, bot_id, "new_review", {"user": request.session["userid"], "reply": False, "review_id": str(id), "rating": rating, "review": review, "root": None})
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully made a review for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>", "username": request.session.get("username", False), "avatar": request.session.get('avatar')}) 



@router.post("/{bot_id}/reviews/{rid}/edit")
async def edit_review(request: Request, bot_id: int, rid: uuid.UUID, bt: BackgroundTasks, rating: float = FForm(5.1), review: str = FForm("This is a placeholder review as the user has not posted anything...")):
    if "userid" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to edit reviews", status_code = 303)
    guild = client.get_guild(main_server)
    user = guild.get_member(int(request.session["userid"]))
    s = is_staff(staff_roles, user.roles, 2)
    if s[0]:
        check = await db.fetchrow("SELECT epoch FROM bot_reviews WHERE id = $1", rid)
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to edit this review (doesn't actually exist)"})
    else:
        check = await db.fetchrow("SELECT epoch FROM bot_reviews WHERE id = $1 AND bot_id = $2 AND user_id = $3", rid, bot_id, int(request.session["userid"]))
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to edit this review"})
    if check["epoch"] is not None:
        check["epoch"].append(time.time())
        epoch = check["epoch"]
    else:
        epoch = [time.time()]
    await db.execute("UPDATE bot_reviews SET star_rating = $1, review_text = $2, epoch = $3 WHERE id = $4", rating, review, epoch, rid)
    bt.add_task(base_rev_bt, bot_id, "edit_review", {"user": request.session["userid"], "review_id": str(rid), "rating": rating, "review": review})
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully editted your/this review for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>"})

@router.post("/{bot_id}/reviews/{rid}/reply")
async def edit_review(request: Request, bot_id: int, rid: uuid.UUID, bt: BackgroundTasks, rating: float = FForm(5.1), review: str = FForm("This is a placeholder review as the user has not posted anything...")):
    if "userid" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to edit reviews", status_code = 303)
    check = await db.fetchrow("SELECT replies FROM bot_reviews WHERE id = $1", rid)
    if check is None:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to reply to this review (doesn't actually exist)"})
    reply_id = uuid.uuid4()
    await db.execute("INSERT INTO bot_reviews (id, bot_id, user_id, star_rating, review_text, epoch, reply) VALUES ($1, $2, $3, $4, $5, $6, $7)", reply_id, bot_id, int(request.session["userid"]), rating, review, [time.time()], True)
    replies = check["replies"]
    replies.append(reply_id)
    await db.execute("UPDATE bot_reviews SET replies = $1 WHERE id = $2", replies, rid)
    bt.add_task(base_rev_bt, bot_id, "new_review", {"user": request.session["userid"], "reply": True, "review_id": str(reply_id), "rating": rating, "review": review, "root": str(rid)})
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully replied to your/this review for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>"})

@router.post("/{bot_id}/reviews/{rid}/delete")
async def delete_review(request: Request, bot_id: int, rid: uuid.UUID, bt: BackgroundTasks):
    if "userid" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to delete reviews", status_code = 303)
    guild = client.get_guild(main_server)

    user = guild.get_member(int(request.session["userid"]))
    if user is None:
        s = [False]
    else:
        s = is_staff(staff_roles, user.roles, 2)
    if s[0]:
        check = await db.fetchrow("SELECT replies FROM bot_reviews WHERE id = $1", rid)
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to delete this review (doesn't actually exist)"})
    else:
        check = await db.fetchrow("SELECT replies FROM bot_reviews WHERE id = $1 AND bot_id = $2 AND user_id = $3", rid, bot_id, int(request.session["userid"]))
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You are not allowed to delete this review"})
    await db.execute("DELETE FROM bot_reviews WHERE id = $1", rid)
    bt.add_task(base_rev_bt, bot_id, "delete_review", {"user": request.session["userid"], "reply": False, "review_id": str(rid)})
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully deleted your/this review for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>"})

@router.post("/{bot_id}/reviews/{rid}/upvote")
async def upvote_review(request: Request, bot_id: int, rid: uuid.UUID):
    if "userid" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to upvote reviews", status_code = 303)
    bot_rev = await db.fetchrow("SELECT review_upvotes, review_downvotes FROM bot_reviews WHERE id = $1", rid)
    if bot_rev is None:
        return await templates.e("message.html", {"request": request, "message": "You are not allowed to upvote this review (doesn't actually exist)"})
    bot_rev = dict(bot_rev)
    user = int(request.session.get("userid"))
    if user in bot_rev["review_upvotes"]:
        return abort(429)
    if user in bot_rev["review_downvotes"]:
        while True:
            try:
                bot_rev["review_downvotes"].remove(user)
            except:
                break
    bot_rev["review_upvotes"].append(int(user))
    await db.execute("UPDATE bot_reviews SET review_upvotes = $1, review_downvotes = $2 WHERE id = $3", bot_rev["review_upvotes"], bot_rev["review_downvotes"], rid)
    await add_event(bot_id, "upvote_review", {"user": request.session["userid"], "review_id": str(rid), "upvotes": len(bot_rev["review_upvotes"]), "downvotes": len(bot_rev["review_downvotes"])})
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully upvoted this review for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>"})

@router.post("/{bot_id}/reviews/{rid}/downvote")
async def downvote_review(request: Request, bot_id: int, rid: uuid.UUID):
    if "userid" not in request.session.keys():
        return RedirectResponse(f"/auth/login?redirect=/bot/{bot_id}&pretty=to upvote reviews", status_code = 303)
    bot_rev = await db.fetchrow("SELECT review_upvotes, review_downvotes FROM bot_reviews WHERE id = $1", rid)
    if bot_rev is None:
        return await templates.e("message.html", {"request": request, "message": "You are not allowed to upvote this review (doesn't actually exist)"})
    bot_rev = dict(bot_rev)
    user = int(request.session.get("userid"))
    if user in bot_rev["review_downvotes"]:
        return abort(429)
    if user in bot_rev["review_upvotes"]:
        while True:
            try:
                bot_rev["review_upvotes"].remove(user)
            except:
                break
    bot_rev["review_downvotes"].append(int(user))
    await db.execute("UPDATE bot_reviews SET review_upvotes = $1, review_downvotes = $2 WHERE id = $3", bot_rev["review_upvotes"], bot_rev["review_downvotes"], rid)
    await add_event(bot_id, "downvote_review", {"user": request.session["userid"], "review_id": str(rid), "upvotes": len(bot_rev["review_upvotes"]), "downvotes": len(bot_rev["review_downvotes"])})
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Successfully downvoted this review for this bot!<script>window.location.replace('/bot/" + str(bot_id) + "')</script>"})


@router.get("/{bid}/resubmit")
async def resubmit_bot(request: Request, bid: int):
    if "userid" in request.session.keys():
        check = await is_bot_admin(int(bid), int(request.session.get("userid")))
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "This bot does not exist on our database."})
        elif check == False:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot."})
    else:
        return RedirectResponse("/")
    user = await get_bot(bid)
    if user is None:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "This bot does not exist on our database."})
    form = await Form.from_formdata(request)
    return await templates.TemplateResponse("resubmit.html", {"request": request, "user": user, "bot_id": bid, "form": form})

@router.post("/{bid}/resubmit")
async def resubmit_bot(request: Request, bid: int, appeal: str = FForm("No appeal provided"), qtype: str = FForm("off")):
    if "userid" in request.session.keys():
        check = await is_bot_admin(int(bid), int(request.session.get("userid")))
        if check is None:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "This bot does not exist on our database."})
        elif check == False:
            return await templates.TemplateResponse("message.html", {"request": request, "message": "You aren't the owner of this bot."})
    else:
        return RedirectResponse("/")
    user = await get_bot(bid)
    if user is None:
        return await templates.TemplateResponse("message.html", {"request": request, "message": "This bot does not exist on our database."})
    resubmit = qtype == "on"
    reschannel = client.get_channel(appeals_channel)
    if resubmit:
        title = "Bot Resubmission"
        type = "Context"
    else:
        title = "Ban Appeal"
        type = "Appeal"
    resubmit_embed = discord.Embed(title=title, color=0x00ff00)
    resubmit_embed.add_field(name="Username", value = user['username'])
    resubmit_embed.add_field(name="Bot ID", value = str(bid))
    resubmit_embed.add_field(name="Resubmission", value = str(resubmit))
    resubmit_embed.add_field(name=type, value = appeal)
    await reschannel.send(embed = resubmit_embed)
    return await templates.TemplateResponse("message.html", {"request": request, "message": "Appeal sent successfully!."})

