from modules.core import *

from ..base import API_VERSION
from .models import APIResponse, BotResourcesGet, BotResource, IDResponse, enums, BotResources, BotResourceDelete

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Custom Resources"],
)

@router.get(
    "/{bot_id}/resources", 
    response_model = List[dict],
    operation_id="get_resources"
)
async def get_resources(request:  Request, bot_id: int, filter: Optional[str] = None, lang: str = "default"):
    resources = await db.fetch("SELECT id, resource_title, resource_link, resource_description FROM bot_resources WHERE bot_id = $1", bot_id)
    if not resources:
        return abort(404)
    return resources

@router.post(
    "/{bot_id}/resources",
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        ),
        Depends(bot_auth_check)
    ],
    operation_id="add_resources"
)
async def add_resources(request: Request, bot_id: int, res: BotResources):
    """
    Adds a resource to your bot. If it already exists, this will delete and readd the resource so it can be used to edit already existing resources
    """
    ids = []
    for resource in res.resources:
        check = await db.fetchval("SELECT COUNT(1) FROM bot_resources WHERE (resource_title = $1 OR resource_link = $2) AND bot_id = $3", resource.resource_title, resource.resource_link, bot_id)
        if check:
            await db.execute("DELETE FROM bot_resources WHERE (resource_title = $1 OR resource_link = $2) AND bot_id = $3", resource.resource_title, resource.resource_link, bot_id)
        id = uuid.uuid4()
        await db.execute("INSERT INTO bot_resources (id, bot_id, resource_title, resource_description, resource_link) VALUES ($1, $2, $3, $4, $5)", id, bot_id, resource.resource_title, resource.resource_description, resource.resource_link)
        ids.append(str(id))
    await bot_add_event(bot_id, enums.APIEvents.resource_add, {"user": None, "id": ids})
    return api_success(id = ids)

@router.delete(
    "/{bot_id}/resources", 
    response_model = APIResponse, 
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        ), 
        Depends(bot_auth_check)
    ],
    operation_id="delete_resources"
)
async def delete_resources(request: Request, bot_id: int, resources: BotResourceDelete):
    """
    If ids/names is provided, all resources with said ids/names will be deleted (this can be used together). 
    If nuke is provided, then all resources will deleted. Ids/names and nuke cannot be used at the same time
    """
    if resources.nuke:
        await db.execute("DELETE FROM bot_resources WHERE bot_id = $1", bot_id)
        await bot_add_event(bot_id, enums.APIEvents.resource_delete, {"user": None, "ids": [], "names": [], "nuke": True})
        return api_success()

    for id in resources.ids:
        await db.execute("DELETE FROM bot_resources WHERE id = $1 AND bot_id = $2", id, bot_id)
    for name in resources.names:
        await db.execute("DELETE FROM bot_resources WHERE (resource_title = $1 OR resource_link = $1) AND bot_id = $2", name, bot_id)
    await bot_add_event(bot_id, enums.APIEvents.resource_delete, {"user": None, "ids": resources.ids, "names": resources.names, "nuke": False})
    return api_success()
