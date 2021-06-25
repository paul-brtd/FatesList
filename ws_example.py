import asyncio
import json
import time
import uuid

import websockets

from modules.models import enums


async def run():
    async with websockets.connect("wss://fateslist.xyz/api/v2/ws/rtstats") as websocket:
        while True:
            event = await websocket.recv()
            event = json.loads(event)
            print(f"DEBUG: Got {event}")
            if enums.APIEvents(event["m"]["e"]) == enums.APIEvents.ws_identity:
                print("Got IDENTITY payload")
                bots = input("Enter Bot ID:API Token seperated by a comma if multiple: ")
                bots = bots.split(",")
                auth = []
                for bot in bots:
                    bot_id, token = bot.replace(" ", "").split(":")
                    auth.append({"id": bot_id, "token": token})
                payload = {"m": {"e": enums.APIEvents.ws_identity_res, "t": enums.APIEventTypes.auth_token, "eid": str(uuid.uuid4()), "ts": time.time()}, "ctx": {"auth": auth, "filter": None}}
                await websocket.send(json.dumps(payload))
                print(f"Sending {json.dumps(payload)}")
                res = await websocket.recv()
                print(f"DEBUG: Got response {res}")
                event = json.loads(res)
                if enums.APIEvents(event["m"]["e"]) == enums.APIEvents.ws_kill:
                    print(f"Got error, likely invalid payload or no valid auth provided")
                elif enums.APIEvents(event["m"]["e"]) == enums.APIEvents.ws_status:
                    print("Connected to Websocket API")
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(run())
