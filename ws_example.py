import websockets
import asyncio
from modules.models import enums
import json
import uuid
import time

async def run():
    async with websockets.connect("wss://fateslist.xyz/apiws/bot/rtstats") as websocket:
        event = await websocket.recv()
        event = json.loads(event)
        print(f"DEBUG: Got {event}")
        if enums.APIEvents(event["m"]["e"]) == enums.APIEvents.ws_identity:
                print("Got IDENTITY payload")
                token = input("Enter API Tokens seperated by a space if multiple: ")
                token = token.split(" ")
                payload = {"m": {"e": enums.APIEvents.ws_identity_res, "t": enums.APIEventTypes.auth_token, "eid": str(uuid.uuid4()), "ts": time.time()}, "ctx": {"token": token}}
                await websocket.send(json.dumps(payload))
                print(f"Sending {json.dumps(payload)}")
                res = await websocket.recv()
                print(f"DEBUG: Got response {res}")
                event = json.loads(res)
                if enums.APIEvents(event["m"]["e"]) == enums.APIEvents.ws_kill:
                    print(f"Got error, likely invalid payload or no valid auth provided")
                elif enums.APIEvents(event["m"]["e"]) == enums.APIEvents.ws_status:
                    print("Connected to Websocket API")
                    flag = True
                    while flag:
                        try:
                            res = await websocket.recv()
                            print(f"DEBUG: Got payload {json.loads(res)}")
                        except:
                            flag = False
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(run())
