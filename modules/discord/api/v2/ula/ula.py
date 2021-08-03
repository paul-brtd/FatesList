from modules.core import *
from ..base import API_VERSION
from .models import APIResponse, Lists, Stats, BList, Endpoint

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/ula",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - ULA"]
)

class Supported:
    stat_posts = ("server_count", "shard_count", "shards", "shard_id")
    get_user_voted = ('user_id', 'res_voted') # Get User Votes
# Base Models

class Lists(BaseModel):
    lists: dict

class Stats(Lists):
    server_count: int
    shard_count: int

class BList(BaseModel):
    url: str
    icon: Optional[str] = None
    api_url: str
    api_docs: str
    discord: Optional[str] = None
    description: Optional[str] = "No Description Yet :("
    supported_features: List[int]
    owners: List[str]

class Endpoint(BaseModel):
    method: enums.ULAMethod
    feature: enums.ULAFeature
    api_path: str
    supported_fields: dict

@router.get("/list/{url}")
async def get_list(request: Request, url: str):
    lst = await db.fetchrow(
        "SELECT icon, url, api_url, api_docs, discord, description, supported_features, owners, queue FROM ula_bot_list WHERE url = $3",
        url
    )

    if not lst:
        return abort(404)
    return lst

@router.get("/lists")
async def get_all_lists(request: Request):
    lists = await db.fetch("SELECT icon, url, api_url, api_docs, discord, description, supported_features, owners FROM bot_list WHERE state = $1", enums.ULAState.approved)
    if not lists:
        return api_error("No lists found")
    lists = dict({"lists": lists})
    ret = {"lists": []}
    for l in lists["lists"]:
        l = dict(l)
        if l["api_docs"]:
            pass
        else:
            l["api_docs"] = None # Make sure "" = None
        api = await db.fetch("SELECT method, feature AS api_type, supported_fields, api_path FROM bot_list_api WHERE url = $1", l["url"])
        api = [dict(obj) for obj in api]
        for api_ep in api:
            api_ep["supported_fields"] = orjson.loads(api_ep["supported_fields"])
            if not api_ep["supported_fields"]:
                api_ep["supported_fields"] = {}
        ret["lists"].append({l["url"]: {"list": l, "api": api}})
    return ret

async def list_check(blist: BList, user_id: Optional[int] = None):
    if blist.url.startswith("https://") or blist.api_url.startswith("https://"):
        pass
    else:
        return ORJSONResponse({"message": "List must use HTTPS and not HTTP", "code": 1000}, status_code = 400)
    blist.url = blist.url.replace("https://", "")
    blist.api_url = blist.api_url.replace("https://", "")
    try:
        blist.owners = [int(owner) for owner in blist.owners if owner.replace(" ", "") != ""]
    except:
        return api_error("Invalid owner found")
    invalid_owners = [id for id in blist.owners if (await get_user(id)) is None]
    if invalid_owners:
        return api_error("Invalid owner found")
    if not user_id and user_id not in blist.owners:
        return api_error("You must be a owner to add the list")
    if len(blist.url.split(".")) < 2 or len(blist.api_url.split(".")) < 2:
        return api_error("url and api_url keys must be proper URLs")
    if len(blist.supported_features) > 20:
        return api_error("Too many features have been set. To prevent abuse, you may only set 20 features")
    if len(blist.description) > 60:
        return api_error("Short description is too long and can only be a maximum of 60 characters long")
    return None

@router.put("/{user_id}/lists", dependencies=[Depends(user_auth_check)])
async def new_list(request: Request, user_id: int, blist: BList):
    """
        Adds a new list if it exists. Your user id associated with your api token must be in owners array
    """
    rc = await list_check(blist, user_id)
    if rc:
        return rc
    try:
        await db.execute(
            "INSERT INTO bot_list (url, icon, api_url, api_docs, discord, description, supported_features, state, owners) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)", 
            blist.url, 
            blist.icon, 
            blist.api_url, 
            blist.api_docs, 
            blist.discord, 
            blist.description, 
            blist.supported_features, 
            enums.ULAState.pending, 
            blist.owners
        )
    except asyncpg.exceptions.UniqueViolationError:
        return api_error("Botlist already exists!")
    return api_success(api_token=api_token)

@router.patch("/{user_id}/list/{url}", dependencies=[Depends(user_auth_check)])
async def edit_list(request: Request, url: str, user_id: int, blist: BList):
    rc = await list_check(blist, user_id)
    if rc:
        return rc

    await db.execute("UPDATE bot_list SET url = $1, icon = $2, api_url = $3, discord = $4, description = $5, supported_features = $6, owners = $7, api_docs = $8 WHERE url = $9", blist.url, blist.icon, blist.api_url, blist.discord, blist.description, blist.supported_features, blist.owners, blist.api_docs, url)
    return api_success()

@router.delete("/{user_id}/list/{url}", dependencies=[Depends(user_auth_check)])
async def delete_list(request: Request, url: str, user_id: int):
    await db.execute("DELETE FROM bot_list WHERE url = $1", url)
    return api_success()

def ep_check(endpoint):
    if not endpoint.api_path.startswith("/"):
        return api_error("API Path must start with /")
    return None

@router.put("/{user_id}/list/{url}/endpoints", dependencies=[Depends(user_auth_check)])
async def new_endpoint(request: Request, url: str, user_id: int, endpoint: Endpoint):
    """Make a new endpoint"""
    rc = ep_check(endpoint)
    if rc:
        return rc
    check = await db.fetchrow("SELECT api_path FROM bot_list_api WHERE feature = $1 AND url = $2", endpoint.feature, url)
    if check:
        return api_error("Endpoint cannot be created as its feature type already exists for your list!")
    await db.execute("INSERT INTO bot_list_api (url, method, feature, supported_fields, api_path) VALUES ($1, $2, $3, $4, $5)", url, endpoint.method, endpoint.feature, orjson.dumps(endpoint.supported_fields).decode('utf-8'), endpoint.api_path)
    return api_success()

@router.patch("/{user_id}/list/{url}/endpoints", dependencies=[Depends(user_auth_check)])
async def edit_endpoint(request: Request, url: str, user_id: int, endpoint: Endpoint):
    rc = ep_check(endpoint)
    if rc:
        return rc
    check = await db.fetchrow("SELECT api_path FROM bot_list_api WHERE feature = $1 AND url = $2", endpoint.feature, url)
    if not check:
        return api_error("Endpoint cannot be editted as its feature type does not already exist")
    await db.execute("UPDATE bot_list_api SET method = $1, supported_fields = $2, api_path = $3 WHERE url = $4 AND feature = $5", endpoint.method, orjson.dumps(endpoint.supported_fields).decode('utf-8'), endpoint.api_path, url, endpoint.feature)
    return api_success()

@router.delete("/{user_id}/list/{url}/endpoint/{feature}", dependencies=[Depends(user_auth_check)])
async def delete_endpoint(request: Request, url: str, feature: enums.ULAFeature, user_id: int):
    """
        Deletes an existing enfpoint based on its feature
    """
    await db.execute("DELETE FROM bot_list_api WHERE url = $1 AND feature = $2", url, feature)
    return api_success()

@router.post("/bots/{bot_id}/stats")
async def post_stats(request: Request, bot_id: int, stats: Stats):
    """
        Post stats to all lists, takes a LIST_URL: LIST_API_TOKEN in the lists object in request body.
    """
    posted_lists = {}
    for blist in stats.lists.keys():

        api_url = await db.fetchrow("SELECT api_url, queue FROM bot_list WHERE url = $1", blist)
        if api_url is None:
            posted_lists[blist] = {"posted": False, "reason": "List does not exist", "response": None, "status_code": None, "api_url": None, "api_path": None, "sent_data": None, "success": False, "method": None}
            continue 
    
        if api_url["queue"]:
            posted_lists[blist] = {"posted": False, "reason": "List still in queue", "response": None, "status_code": None, "api_url": None, "api_path": None, "sent_data": None, "success": False, "method": None}

        api = await db.fetchrow(
            "SELECT supported_fields, api_path, method FROM bot_list_api WHERE url = $1 AND feature = $2", 
            blist,
            enums.ULAFeature.post_stats
        )
        if api is None:
            posted_lists[blist] = {"posted": False, "reason": "List doesn't support requested method", "response": None, "status_code": None, "api_url": None, "api_path": None, "sent_data": None, "success": False, "method": None}
            continue # List doesn't support requested method
        
        api_url = api_url['api_url']
        sf = api["supported_fields"]
        sf = orjson.loads(sf)
        # Get corresponding list values for server_count and shard_count
        send_json = {}
        for key in Supported.post_stats:
            field = sf.get(key)
            if field:
                send_json[field] = stats.__dict__[key]
            else:
                continue
        
        api_path = api['api_path'].replace("{id}", str(bot_id)).replace("{bot_id}", str(bot_id)) # Get the API path

        f = enums.ULAMethod(api["method"])
        try:
            async with aiohttp.ClientSession() as sess:
                f = getattr(sess, f.name)
                async with f("https://" + api_url + api_path, json = send_json, headers = {"Authorization": str(stats.lists[blist])}, timeout = 15) as res:
                    try:
                        response = await res.json()
                    except Exception:
                        response = await res.text()

                    posted_lists[blist] = {"posted": True, "reason": None, "response": response, "status_code": rc.status, "api_url": api_url, "api_path": api_path, "sent_data": send_json, "success": rc.status == 200, "method": api["method"]}

        except Exception as e:
            posted_lists[blist] = {"posted": False, "reason": f"Could not connect/find server: {e}", "response": None, "status_code": None, "api_url": api_url, "api_path": api_path, "sent_data": send_json, "success": False, "method": api["method"]}
        
    return posted_lists

# TODO: Do List Processing
@router.get("/bots/{bot_id}")
async def get_bot(request: Request, bot_id: int):
    lists = await db.fetch("SELECT api_url, url FROM bot_list WHERE state = $1", enums.ULAState.approved)
    if not lists:
        return api_error("No lists found!")

    get_lists = {}
    for blist in lists:
        api = await db.fetchrow(
            "SELECT supported_fields, api_path, method FROM bot_list_api WHERE url = $1 AND feature = $2", 
            blist["url"],
            enums.ULAFeature.get_bot
        )
        if not api:
            get_lists[blist["url"]] = {"got": False, "reason": "List doesn't support requested method", "response": None, "status_code": None, "api_url": None, "api_path": None, "success": False, "method": None}
            continue
        api_path = api['api_path'].replace("{bot_id}", str(bot_id)) # Get the API path
        api_url = blist["api_url"]

        f = enums.ULAMethod(api["method"]) 
        try:
            async with aiohttp.ClientSession() as sess:
                f = getattr(sess, f.name)
                async with f("https://" + api_url + api_path, timeout = 15) as res:
                    try: 
                        response = await res.json()
                    except Exception:
                        response = await res.text()
                    get_lists[blist["url"]] = {"got": True, "reason": None, "response": response, "status_code": rc.status, "api_url": api_url, "api_path": api_path, "success": rc.status < 400, "method": api["method"]}
        except Exception as e:
            get_lists[blist["url"]] = {"got": False, "reason": f"Could not connect/find server: {e}", "response": None, "status_code": None, "api_url": api_url, "api_path": api_path, "success": False, "method": api["method"]}
    return get_lists

@router.post("/bots/{bot_id}/votes/check")
async def get_user_voted(request: Request, bot_id: int, user_id: int, lists: Lists):
    """Gets whether a user has voted for your bot"""
    guv_lists = {}
    for blist in lists.lists.keys():

        api_url = await db.fetchrow("SELECT api_url FROM bot_list WHERE url = $1 AND state = $2", blist, enums.ULAState.approved)
        if api_url is None:
            guv_lists[blist] = {"voted": False, "reason": "List does not exist", "response": None}
            continue

        api = await db.fetchrow("SELECT supported_fields, api_path, method FROM bot_list_api WHERE url = $1 AND feature = $2", blist, enums.ULAFeature.get_user_voted) # Feature 3 = Get User Voted
        if api is None:
            guv_lists[blist] = {"voted": False, "reason": "List doesn't support requested method", "response": None}
            continue # List doesn't support requested method

        api_url = api_url['api_url']
        sf = api["supported_fields"]
        sf = orjson.loads(sf)
        # Get corresponding list values for guv
        qkey = ""
        jsonkey = ""
        for key in Supported.get_user_voted:
            field = sf.get(key)
            if field and key == "res_voted":
                jsonkey = field
            elif field and key == "user_id":
                qkey = field
            else:
                continue
        
        if jsonkey == "":
            guv_lists[blist] = {"voted": False, "reason": "Required key jsonkey not defined on list", "response": None}
            continue

        api_path = api['api_path'].replace("{user_id}", str(user_id)).replace("{bot_id}", str(bot_id)) # Get the API path
        
        f = enums.ULAMethod(api["method"])
        try:
            url = f"https://{api_url}{api_path}"
            if qkey:
                url += f"?{qkey}={user_id}"
            async with aiohttp.ClientSession() as sess:
                f = getattr(sess, f.name)
                async with f(url, headers = {"Authorization": str(lists.lists[blist])}, timeout = 15) as res:
                    try:
                        response = await res.json()
                    except Exception:
                        guv_lists[blist] = {"voted": False, "reason": f"Malformed JSON response: {e}", "response": None}
                        continue

                    guv_lists[blist] = {"voted": response.get(jsonkey) in (True, 1), "reason": "Got response from list", "response": response}
        except Exception as e:
            guv_lists[blist] = {"voted": False, "reason": f"Could not connect/find server: {e}", "response": None}
            continue
    return guv_lists

        

@router.get("/feature/{id}/id")
async def get_feature_by_id(request: Request, id: int):
    return {"feature": (await db.fetchrow('SELECT name, iname as internal_name, description, positive, feature_id AS id FROM bot_list_feature WHERE feature_id = $1', id))}

@router.get("/feature/{iname}/iname")
async def get_feature_by_internal_name(request: Request, iname: str):
    return {"feature": (await db.fetchrow('SELECT name, iname as internal_name, description, positive, feature_id AS id FROM bot_list_feature WHERE iname = $1', iname))}

