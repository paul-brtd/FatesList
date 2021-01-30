import fastapi, orjson
app = fastapi.FastAPI()
@app.get("/")
async def index():
    return orjson.loads(open("status.json").read())
