from .imports import *
from .cache import *
from .events import *

async def parse_reviews(bot_id: int, reviews: List[asyncpg.Record] = None) -> List[dict]:
    if reviews is None:
        _rev = True
        reviews = await db.fetch("SELECT id, reply, user_id, star_rating, review_text AS review, review_upvotes, review_downvotes, flagged, epoch, replies AS _replies FROM bot_reviews WHERE bot_id = $1 AND reply = false ORDER BY epoch, star_rating ASC", bot_id)
    else:
        _rev = False
    i = 0
    stars = 0
    while i < len(reviews):
        reviews[i] = dict(reviews[i])
        if reviews[i]["epoch"] in ([], None):
            reviews[i]["epoch"] = [time.time()]
        else:
            reviews[i]["epoch"].sort(reverse = True)
        reviews[i]["time_past"] = str(time.time() - reviews[i]["epoch"][0])
        reviews[i]["epoch"] = [str(ep) for ep in reviews[i]["epoch"]]
        reviews[i]["id"] = str(reviews[i]["id"])
        reviews[i]["user"] = await get_user(reviews[i]["user_id"])
        reviews[i]["user_id"] = str(reviews[i]["user_id"])
        reviews[i]["star_rating"] = round(reviews[i]["star_rating"], 2)
        reviews[i]["replies"] = []
        reviews[i]["review_upvotes"] = [str(ru) for ru in reviews[i]["review_upvotes"]]
        reviews[i]["review_downvotes"] = [str(rd) for rd in reviews[i]["review_downvotes"]]
        if _rev:
            stars += reviews[i]["star_rating"]
        for review_id in reviews[i]["_replies"]:
            _reply = await db.fetch("SELECT id, reply, user_id, star_rating, review_text AS review, review_upvotes, review_downvotes, flagged, epoch, replies AS _replies FROM bot_reviews WHERE id = $1", review_id)
            _parsed_reply = await parse_reviews(bot_id, _reply)
            try:
                reviews[i]["replies"].append(_parsed_reply[0][0])
            except:
                pass
        del reviews[i]["_replies"]
        i+=1
    if i == 0:
        return reviews, 10.0
    return reviews, round(stars/i, 2)

async def base_rev_bt(bot_id, event, base_dict):
    reviews = await parse_reviews(bot_id)
    await add_event(bot_id, event, base_dict | {"reviews": reviews[0], "average_stars": reviews[1]})
