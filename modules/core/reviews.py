from .cache import *
from .events import *
from .imports import *


async def parse_reviews(worker_session, bot_id: int, rev_id: uuid.uuid4 = None, page: int = None) -> List[dict]:
    db = worker_session.postgres

    per_page = 9
    if not rev_id:
        reply = False    
        rev_check = "" # Extra string to check review
        rev_args = () # Any extra arguments?
    else:
        reply = True
        rev_check = "AND id = $3" # Extra string to check for review id
        rev_args = (rev_id,) # Extra argument of review id

    if page is None:
        end = ""
    else:
        end = f"OFFSET {per_page*(page-1)} LIMIT {per_page}"
    reviews = await db.fetch(f"SELECT id, reply, user_id, star_rating, review_text AS review, review_upvotes, review_downvotes, flagged, epoch, replies AS _replies FROM bot_reviews WHERE bot_id = $1 AND reply = $2 {rev_check} ORDER BY epoch, star_rating ASC {end}", bot_id, reply, *rev_args)
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
        reviews[i]["user"] = await get_user(reviews[i]["user_id"], worker_session = worker_session)
        reviews[i]["user_id"] = str(reviews[i]["user_id"])
        reviews[i]["star_rating"] = round(reviews[i]["star_rating"], 2)
        reviews[i]["replies"] = []
        reviews[i]["review_upvotes"] = [str(ru) for ru in reviews[i]["review_upvotes"]]
        reviews[i]["review_downvotes"] = [str(rd) for rd in reviews[i]["review_downvotes"]]
        if not rev_id:
            stars += reviews[i]["star_rating"]
        for review_id in reviews[i]["_replies"]:
            _parsed_reply = await parse_reviews(worker_session, bot_id, review_id)
            try:
                reviews[i]["replies"].append(_parsed_reply[0][0])
            except:
                pass
        del reviews[i]["_replies"]
        i+=1
    total_rev = await db.fetchrow("SELECT COUNT(1) AS count, AVG(star_rating)::numeric(10, 2) AS avg FROM bot_reviews WHERE bot_id = $1 AND reply = false", bot_id)

    if i == 0:
        return reviews, 10.0, 0, 0, per_page
    logger.trace(f"Total reviews per page is {total_rev['count']/per_page}")
    return reviews, total_rev["avg"], total_rev["count"], int(math.ceil(total_rev["count"]/per_page)), per_page

