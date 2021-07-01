def version_scope(request, def_version):
    if str(request.url.path).startswith("/api/") and not str(request.url.path).startswith("/api/docs") and not str(request.url.path).startswith("/api/v") and not str(request.url.path).startswith("/api/ws"):
        if request.headers.get("FL-API-Version"):
            api_ver = request.headers.get("FL-API-Version")
        else:
            api_ver = str(def_version)
        new_scope = request.scope
        new_scope["path"] = new_scope["path"].replace("/api", f"/api/v{api_ver}")
    else:
        new_scope = request.scope
        if str(request.url.path).startswith("/api/v"):
            logger.trace("New API path is {request.url.path}")
            api_ver = str(request.url.path).split("/")[2][1:] # Split by / and get 2nd (vX part and then get just X)
            if api_ver == "":
                api_ver = str(def_version)
        else:
            api_ver = str(def_version)
    logger.trace(f"API version is {api_ver}")
    if request.headers.get("Method") and str(request.headers.get("Method")).upper() in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        new_scope["method"] = str(request.headers.get("FL-Method")).upper()
    return new_scope, api_ver

# Some replace tuples
js_rem_tuple = (("onclick", ""), ("onhover", ""), ("script", ""), ("onload", ""))
banner_replace_tuple = (("\"", ""), ("'", ""), ("http://", "https://"), ("(", ""), (")", ""), ("file://", ""))
ldesc_replace_tuple = (("window.location", ""), ("document.ge", ""))
