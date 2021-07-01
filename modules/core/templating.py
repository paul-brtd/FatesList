"""
Fates List Templating System
"""

from .imports import *
from .permissions import *

_templates = Jinja2Templates(directory="templates") # Setup templates folder
discord_o = Oauth(OauthConfig)

def intl_text(text: str, lang: str, link: bool = False, linked_langs: dict = {}, dbg = False):
    logger.trace(f"Called intl_text with text of {text}, lang of {lang}, link of {link} and linked_langs of {linked_langs}")
    lang = lang if lang.replace(" ", "") else "default" # If lang is empty/none, set it to default, otherwise keep the lang
    ltext = text.split(f"[[lang {lang.lower()}") # Split text into sections
    if len(ltext) == 1: # We didnt get any sections
        # Only one language or specified language is not found
        if link:
            return "" # Return nothing if link was not found
        kwargs = {"link": link, "linked_langs": linked_langs | {lang: None}} # Common keyword arguments for returning
        if lang == "default" and "[[lang en" in text: # If lang is default, there are no translations for it and en translations have been seen/potentially there, use them
            return intl_text(text, "en", **kwargs) 
        if lang != "default": # Fallback to default translations if this language has not been found
            return intl_text(text, "default", **kwargs)
        return text # Otherwise, if all fails, return the full text
    strlst = [] # List of all sections with this language is in strlst
    i = 0 # Counter

    # Some math:
    # For a<b>c<b>d<b>e<b>ffg
    # Split by <b> is a, c, d, e, ffg
    # a, d, ffg are between or not in <b>. These are index 0, 2 and 4
    # So, odd is in between and even is not
    # So to get in between, do i % 2 as below

    for text_block in ltext:
        if i % 2 == 0:
            i+=1
            continue # Meaning before or between a lang tag, see "Some math..."
        i+=1
        txt_split = text_block.split("]]", 1) # The split in the beginning got us "link=foo label=baz]] My text here", inthis the metadata if link=foo label=baz is before the ]] and the text is after, so split by ]] once to get metadata and inside text
        if len(txt_split) == 1: # This happens when a user forgets to close their tag, ignore the full tag and contents
            i+=1
            continue # Illegal lang attribute
        
        txt_add = txt_split[1] # Text add is after ]]
        
        # Get meta as string of a=1 b=2 and make it {"a": 1, "b": 2}
        meta_str = txt_split[0] # Metadata string is before ]]

        meta = {} # Metadata dict to dump proccessed metadata into
        
        # List of metadata attributes about our section to forward handle (abc=def abcx fgh=a will give {"abc" def abcx, "fgh": a} where abcx is forward handled)
        forward_handling = None # Whether we are currently processing something that needs to be handled
        for split in meta_str.split(" "): # Split it into [a=b, c=d] where original was a=b c=d
            
            split_list = split.replace(" ", "").split("=") # Then make the a=b into [a, b]
            
            if len(split_list) != 1: # We have a equal to sign!!!
                
                if split_list[1].startswith('"') or split_list[1].startswith("'"):
                    forward_handling = split_list[0] # Start forward handle at begin quotes
                    
                elif split_list[1].endswith('"') or split_list[1].endswith("'"):
                    forward_handling = None # Stop forward handle at quotes
                    
                meta |= {split_list[0]: split_list[1]} # Add to meta
                
            elif forward_handling: # Handle forward handling
                meta[forward_handling] += " " + split_list[0] # Add on split stuff
                
        pre = None # Default no pre (inheritance)
        
        link_opt = meta.get("link")
        if link_opt:
            lang_link = link_opt
            if lang_link.replace(" ", "") == lang.replace(" ", "") or lang_link in linked_langs.keys():
                pre = linked_langs.get(lang_link)
            else:
                pre = intl_text(text, lang_link, link = True, linked_langs = linked_langs | {lang_link: txt_add})
        if pre:
            if not txt_add.replace(" ", ""):
                txt_add = pre # Handle cases of default aliasing to en and viceversa
            else:
                txt_add = pre + "\n" + txt_add
        strlst.append(txt_add)
        if dbg:
            return "\n".join(strlst), strlst, meta
    return "\n".join(strlst)

# Template class renderer
class templates():
    @staticmethod
    async def TemplateResponse(f, arg_dict: dict, *, context: dict = {}, not_error: bool = True):
        guild = client.get_guild(main_server)
        try:
            request = arg_dict["request"]
        except:
            raise KeyError
        status = arg_dict.get("status_code")
        if "user_id" in request.session.keys():
            arg_dict["css"] = request.session.get("user_css")
            try:
                user = guild.get_member(int(request.session["user_id"]))
            except:
                user = None
            state = await db.fetchval("SELECT state FROM users WHERE user_id = $1", int(request.session["user_id"]))
            if (state == enums.UserState.global_ban or state == enums.UserState.ddr_ban) and not_error:
                ban_type = enums.UserState(state).__doc__
                return await templates.e(request, f"You have been {ban_type} banned from Fates List<br/>", status_code = 403)
            if user is not None:
                staff = is_staff(staff_roles, user.roles, 2)
                request.session["staff"] = staff[0], staff[1], staff[2].dict()
            else:
                pass
            arg_dict["staff"] = request.session.get("staff")
            arg_dict["avatar"] = request.session.get("avatar")
            arg_dict["username"] = request.session.get("username")
            arg_dict["user_id"] = int(request.session.get("user_id"))
            if request.session.get("user_id"):
                arg_dict["user_token"] = await db.fetchval("SELECT api_token FROM users WHERE user_id = $1", arg_dict["user_id"]) 
            arg_dict["intl_text"] = intl_text
            arg_dict["site_lang"] = request.session.get("site_lang", "default")
            try:
                request.session["access_token"] = await discord_o.access_token_check(request.session.get("scopes"), request.session.get("access_token"))
                arg_dict["access_token"] = orjson.dumps(request.session.get("access_token")).decode("utf-8")
            except:
                pass
            arg_dict["scopes"] = request.session.get("scopes")
        else:
            arg_dict["staff"] = [False]
        arg_dict["site_url"] = site_url
        arg_dict["data"] = arg_dict.get("data")
        arg_dict["path"] = request.url.path
        arg_dict["enums"] = enums
        arg_dict["len"] = len
        arg_dict["ireplace"] = ireplace
        arg_dict["ireplacem"] = ireplacem
        
        base_context = {
            "user_id": str(arg_dict["user_id"]) if "user_id" in arg_dict.keys() else None,
            "user_token": arg_dict.get("user_token"),
            "site_lang": arg_dict.get("site_lang"),
            "logged_in": True if "user_id" in arg_dict.keys() else False
        }
        
        arg_dict["context"] = base_context | context

        if status is None:
            ret = _templates.TemplateResponse(f, arg_dict)
            
        else:
            ret = _templates.TemplateResponse(f, arg_dict, status_code = status)
            
        return ret

    @staticmethod
    async def error(f, arg_dict, status_code):
        arg_dict["status_code"] = status_code
        return await templates.TemplateResponse(f, arg_dict, not_error = False)

    @staticmethod
    async def e(request, reason: str, status_code: int = 404, *, main: Optional[str] = ""):
        return await templates.error("message.html", {"request": request, "message": main, "reason": reason, "retmain": True}, status_code)
