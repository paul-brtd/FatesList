import asyncio
import json
import time
import uuid
import sys
sys.path.append(".")
sys.path.append("../../../")


import websockets

from modules.models import enums

async def render_events(event):
    for m in event.split("\x00"):
        print(json.loads(m))


# Not yet done
async def run():
    async with websockets.connect("ws://localhost:10293") as websocket:
        while True:
            event = await websocket.recv()
            try:
                event = json.loads(event)
            except:
                asyncio.create_task(render_events(event))
                event = {}
            print(f"DEBUG: Got {event}")
            if event.get("code") == "identity":
                print("Got IDENTITY payload")
                bot_id = input("Enter Bot ID: ")
                try:
                    bot_id = int(bot_id)
                except ValueError:
                    bot_id = 811073947382579200
                
                if bot_id == 811073947382579200:
                    api_token = "55gCmZ7zr12upTnQcvnrXcJv1IfN15ddk9WLlxG0h54uCGKFi2TBPlOFh8RYhbCMaSDQPCju2k0g2pykEmsD3AmEvUNPoc4Rxqjk6fpNqncjk8PVeh2ImolpaXE1cNEdCVEh"
                else:
                    api_token = input("Enter API Token: ")
                payload = {"id": str(bot_id), "token": api_token, "bot": True, "send_all": False, "send_none": True}
                await websocket.send(json.dumps(payload))
                print(f"Sending {json.dumps(payload)}")
            res = await websocket.recv()
            print(f"DEBUG: Got response {res}")
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(run())
