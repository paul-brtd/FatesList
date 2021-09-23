from modules.core import *

from ..base import API_VERSION
from .models import APIResponse, BotCommandsGet, BotCommand, IDResponse, enums,BotCommands

router = APIRouter(
    prefix = f"/api/v{API_VERSION}/bots",
    include_in_schema = True,
    tags = [f"API v{API_VERSION} - Commands"],
)

@router.get(
    "/{bot_id}/commands", 
    response_model = BotCommandsGet,
    operation_id="get_commands"
)
async def get_commands(request:  Request, bot_id: int, filter: Optional[str] = None, lang: str = "default"):
    cmd = await get_bot_commands(bot_id, lang, filter)
    if cmd == {}:
        return abort(404)
    return cmd

@router.post(
    "/{bot_id}/commands",
    dependencies=[
        Depends(
            Ratelimiter(
                global_limit = Limit(times=20, minutes=1),
                sub_limits = [Limit(times=5, seconds=15)]
            )
        ),
        Depends(bot_auth_check)
    ],
    operation_id="add_commands"
)
async def add_commands(request: Request, bot_id: int, commands: BotCommands):
    """
    Adds a command to your bot. If it already exists, this will delete and readd the command so it can be used to edit already existing commands
    """
    ids = []
    for command in commands.commands:
        check = await db.fetchval("SELECT COUNT(1) FROM bot_commands WHERE cmd_name = $1 AND bot_id = $2", command.cmd_name, bot_id)
        if check:
            await db.execute("DELETE FROM bot_commands WHERE cmd_name = $1 AND bot_id = $2", command.cmd_name, bot_id)
        id = uuid.uuid4()
        await db.execute("INSERT INTO bot_commands (id, bot_id, cmd_groups, cmd_type, cmd_name, description, args, examples, premium_only, notes, doc_link, vote_locked) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)", id, bot_id, command.cmd_groups, command.cmd_type, command.cmd_name, command.description, command.args, command.examples, command.premium_only, command.notes, command.doc_link, command.vote_locked)
        ids.append(str(id))
    await bot_add_event(bot_id, enums.APIEvents.command_add, {"user": None, "id": ids})
    return api_success(id = ids)

@router.delete(
    "/{bot_id}/commands/{id}", 
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
    operation_id="delete_command"
)
async def delete_command(request: Request, bot_id: int, id: uuid.UUID):
    cmd = await db.fetchval("SELECT id FROM bot_commands WHERE id = $1 AND bot_id = $2", id, bot_id)
    if not cmd:
        return abort(404)
    await db.execute("DELETE FROM bot_commands WHERE id = $1 AND bot_id = $2", id, bot_id)
    await bot_add_event(bot_id, enums.APIEvents.command_delete, {"user": None, "id": id})
    return api_success()
