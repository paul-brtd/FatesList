from .imports import *
async def middleware(app, request: Request, call_next):
    """
        Simple middleware to:
            - Handle API version and internally redirect by changing ASGI scope at request.scope
            - Transparently redirect /bots to /bot and /servers to /servers/index by changing ASGI scope (no 303 since thats bad UX)
            - Set and record the process time for analytics
    """
    request.scope["error_id"] = str(uuid.uuid4()) # Create a error id for just in case
    request.scope["curr_time"] = str(datetime.datetime.now()) # Get time request was made
    logger.trace(request.headers.get("X-Forwarded-For"))
    if str(request.url.path).startswith("/bots/"):
        request.scope["path"] = str(request.url.path).replace("/bots", "/bot", 1)
    request.scope, api_ver = version_scope(request, 2) # Transparently redirect /api to /api/vX excluding docs and already /api/vX'd apis
    start_time = time.time() # Get process time start
    try:
        response = await asyncio.shield(call_next(request)) # Process request
    except Exception as exc: # Try request again
        try:
            request._is_disconnected = False
        except:
            logger.warn("User {request.headers.get('X-Forwarded-For')} disconnected")
        try:
            response = await asyncio.shield(call_next(request))
        except Exception as exc:
            logger.exception("Site Error Occurred")
            response = await fl_exception_handler(request, exc)

    process_time = time.time() - start_time # Get time taken
    response.headers["X-Process-Time"] = str(process_time) # Record time taken
    response.headers["FL-API-Version"] = api_ver # Record currently used api version for debug
    # Fuck CORS
    response.headers["Access-Control-Allow-Origin"] = request.headers.get('Origin') if request.headers.get('Origin') else "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    asyncio.create_task(print_req(request, response))
    return response
