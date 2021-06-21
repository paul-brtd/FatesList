from modules.core import *
from .models import APIResponse, BotMeta, enums
from ..base import API_VERSION
from lxml.html.clean import Cleaner

cleaner = Cleaner(remove_unknown_tags=False)

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/users",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Bots"]
)

@router.post(
    "/{user_id}/bots/{bot_id}", 
    response_model = APIResponse, 
    dependencies=[
        Depends(RateLimiter(times=5, minutes=3)),
        Depends(user_auth_check)
    ]
)
async def add_bot(request: Request, user_id: int, bot_id: int, bot: BotMeta):
    """
    Adds a bot to fates list. 
    
    Due to how Fates List adds and edits bots using RabbitMQ, this will return a 202 and not a 200 on success
    """
    bot.banner = bot.banner.replace("http://", "https://").replace("(", "").replace(")", "")
    bot_dict = bot.dict()
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = user_id
    bot_adder = BotActions(bot_dict)
    rc = await bot_adder.add_bot()
    if rc is None:
        return api_success(f"{site_url}/bot/{bot_id}", status_code = 202)
    return api_error(rc)

@router.patch(
    "/{user_id}/bots/{bot_id}", 
    response_model = APIResponse, 
    dependencies=[
        Depends(RateLimiter(times=5, minutes=3)),
        Depends(user_auth_check)
    ]
)
async def edit_bot(request: Request, user_id: int, bot_id: int, bot: BotMeta):
    """
    Edits a bot, the owner here should be the owner editing the bot.
    Due to how Fates List edits bota using RabbitMQ, this will return a 202 and not a 200 on success
    """
    bot.banner = bot.banner.replace("http://", "https://").replace("(", "").replace(")", "")
    bot_dict = bot.dict()
    bot_dict["bot_id"] = bot_id
    bot_dict["user_id"] = user_id
    bot_editor = BotActions(bot_dict)
    rc = await bot_editor.edit_bot()
    if rc is None:
        return api_success(f"{site_url}/bot/{bot_id}", status_code = 202)
    return api_error(rc)
