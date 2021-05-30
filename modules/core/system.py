from .imports import *

def setup_discord()
    intent_main = discord.Intents.default()
    intent_main.typing = False
    intent_main.bans = False
    intent_main.emojis = False
    intent_main.integrations = False
    intent_main.webhooks = False
    intent_main.invites = False
    intent_main.voice_states = False
    intent_main.messages = False
    intent_main.members = True
    intent_main.presences = True
    client = discord.Client(intents=intent_main)
    intent_server = deepcopy(intent_main)
    intent_server.presences = False
    client_server = discord.Client(intents=intent_server)
    return client, client_server

# Include all the modules by looping through and using importlib to import them and then including them in fastapi
def include_routers(fname, rootpath):
    for root, dirs, files in os.walk(rootpath):
        if not root.startswith("_") and not root.startswith("."):
            rrep = root.replace("/", ".")
            for f in files:
                if not f.startswith("_") and not f.startswith(".") and not f.endswith("pyc"):
                    path = f"{rrep}.{f.replace('.py', '')}"
                    logger.debug(f"{fname}: {root}: Loading {f} with path {path}")
                    route = importlib.import_module(path)
                    app.include_router(route.router)
