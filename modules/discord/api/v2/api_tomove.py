"""Modules to move"""
from typing import Dict, List
from uuid import UUID

from fastapi.responses import HTMLResponse

from modules.core import *
import markdown
from modules.discord.api.v2.modelstomove import *  # TODO

API_VERSION = 2 # This is the API version

router = APIRouter(
    prefix = f"/api/v{API_VERSION}",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - To Move"]
)

@router.patch(
    "/bots/{bot_id}/reviews/{rid}/votes", 
    response_model = APIResponse,
    dependencies = [
        Depends(user_auth_check)
    ]
)
async def vote_review_api(request: Request, bot_id: int, rid: uuid.UUID, vote: BotReviewVote):
    vote.user_id = int(vote.user_id)
    bot_rev = await db.fetchrow("SELECT review_upvotes, review_downvotes, star_rating, reply, review_text FROM bot_reviews WHERE id = $1", rid)
    if bot_rev is None:
        return api_error("You are not allowed to up/downvote this review (doesn't actually exist)", 3836)
    bot_rev = dict(bot_rev)
    if vote.upvote:
        main_key = "review_upvotes"
        remove_key = "review_downvotes"
    else:
        main_key = "review_downvotes"
        remove_key = "review_upvotes"
    if vote.user_id in bot_rev[main_key]:
        return api_error("The user has already voted for this review", 5858)
    if vote.user_id in bot_rev[remove_key]:
        while True:
            try:
                bot_rev[remove_key].remove(vote.user_id)
            except:
                break
    bot_rev[main_key].append(vote.user_id)
    await db.execute("UPDATE bot_reviews SET review_upvotes = $1, review_downvotes = $2 WHERE id = $3", bot_rev["review_upvotes"], bot_rev["review_downvotes"], rid)
    await bot_add_event(bot_id, enums.APIEvents.review_vote, {"user": str(vote.user_id), "id": str(rid), "star_rating": bot_rev["star_rating"], "reply": bot_rev["reply"], "review": bot_rev["review_text"], "upvotes": len(bot_rev["review_upvotes"]), "downvotes": len(bot_rev["review_downvotes"]), "upvote": vote.upvote})
    return api_success()

@router.get(
    "/features/{name}", 
    response_model = FLFeature
)
async def get_feature_api(request: Request, name: str):
    """Gets a feature given its internal name (custom_prefix, open_source etc)"""
    if name not in features.keys():
        return abort(404)
    return features[name]

@router.get(
    "/tags/{name}", 
    response_model = FLTag
)
async def get_tags_api(request: Request, name: str):
    """Gets a tag given its internal name (custom_prefix, open_source etc)"""
    if name not in TAGS.keys():
        return abort(404)
    return {"name": name.replace("_", " ").title(), "iconify_data": TAGS[name], "id": name}

@router.get(
    "/code/{vanity}", 
    response_model = BotVanity
)
async def get_vanity_api(request: Request, vanity: str):
    vb = await vanity_bot(vanity)
    logger.trace(f"Vanity is {vanity} and vb is {vb}")
    if vb is None:
        return abort(404)
    return {"type": vb[1], "redirect": str(vb[0])}

@router.get(
    "/index/bots",
    response_model=BotIndex
)
async def bots_index_page(request: Request):
    """For any potential Android/iOS app, crawlers etc."""
    return await render_index(request = request, api = True)

@router.get(
    "/search/bots", 
    response_model = BotSearch
)
async def bots_search_page(request: Request, q: str):
    """For any potential Android/iOS app, crawlers etc. Q is the query to search for"""
    return await render_search(request = request, q = q, api = True)

@router.get(
    "/search/profiles", 
    response_model = ProfileSearch,
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        )
    ]
)
async def profiles_search_page(request: Request, q: str):
    """For any potential Android/iOS app, crawlers etc. Q is the query to search for"""
    return await render_profile_search(request = request, q = q, api = True)

@router.post(
    "/preview", 
    response_model = PrevResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        )
    ]
)
async def preview_api(request: Request, data: PrevRequest, lang: str = "default"):
    if not data.html_long_description:
        html = emd(markdown.markdown(intl_text(data.data, lang), extensions=["extra", "abbr", "attr_list", "def_list", "fenced_code", "footnotes", "tables", "admonition", "codehilite", "meta", "nl2br", "sane_lists", "toc", "wikilinks", "smarty", "md_in_html"]))
    else:
        html = intl_text(data.data, lang)
    # Take the h1...h5 anad drop it one lower
    html = html.replace("<h1", "<h2 style='text-align: center'").replace("<h2", "<h3").replace("<h4", "<h5").replace("<h6", "<p").replace("<a", "<a class='long-desc-link'").replace("ajax", "").replace("http://", "https://").replace(".alert", "")
    return {"html": html}

# guilds = await discord_o.get_guilds(access_token["access_token"], permissions = [0x8, 0x20]) # Check for admin/manage server in future
