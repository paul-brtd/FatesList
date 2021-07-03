from .imports import *
from .templating import *
from .helpers import *

def etrace(ex):
     return "".join(tblib.format_exception(ex)) # COMPAT: Python 3.10 only

class WebError():
    @staticmethod
    async def log(request, exc, error_id, curr_time):
        traceback = exc.__traceback__ # Get traceback from exception
        site_errors = client.get_channel(site_errors_channel) # Get site errors channel

        try:
            fl_info = f"Error ID: {error_id}\n\n" # Initial header
            fl_info += etrace(exc)
        
        except Exception:
            pass
        
        url = str(request.url).replace('https://', '')
        msg = inspect.cleandoc(f"""500 (Internal Server Error) at {url}

        **Error**: {exc}

        **Error ID**: {error_id}

        **Time When Error Happened**: {curr_time}""") 
        
        try:
            await site_errors.send(msg)
        
        except Exception:
            raise exc # Reraise the error
        
        fl_file = discord.File(io.BytesIO(bytes(fl_info, 'utf-8')), f'{error_id}.txt') # Create a file on discord

        if fl_file is not None:
            await site_errors.send(file=fl_file) # Send it
        
        else:
            await site_errors.send("No extra information could be logged and/or sent right now") # Could not send it

    @staticmethod
    async def error_handler(request, exc, log: bool = True):
        error_id = request.scope["error_id"] 
        curr_time = request.scope["curr_time"] 

        try:
            # All status codes other than most 500 and 422s
            status_code = exc.status_code 
        
        except Exception: 
            # 500 and 422 do not have status code
            if isinstance(exc, RequestValidationError): 
                # 422 (Unprocessable Entity)
                status_code = 422
            
            else: 
                # 500 (Internal Server Error)
                status_code = 500
        
        path = str(request.url.path)
        
        try:
            code_str = HTTPStatus(code_str).phrase
            fixed_code = status_code

        except Exception:
            # Fallback
            code_str = "Unknown Error"
            fixed_code = 400

        if status_code == 500:
            if log:
                # Log the error
                asyncio.create_task(WebError.log(request, exc, error_id, curr_time)) 
            
            if str(request.url.path).startswith("/api"):
                return api_error(
                    "Internal Server Error", 
                    error_id = error_id, 
                    status_code = status_code
                )
            
            tb_full = "".join(tblib.format_exception(exc))

            errmsg = inspect.cleandoc(f"""
                Fates List had a slight issue and our developers and looking into what happened<br/><br/>
                
                Error ID: {error_id}<br/><br/>

                Please check our support server at <a href='{support_url}'>{support_url}</a> for more information<br/><br/>

                Please send the below traceback if asked:<br/><br/>

                <pre>{tb_full}</pre>

                Time When Error Happened: {curr_time}<br/>""")

            return HTMLResponse(errmsg, status_code = status_code)

        # Special error messages (some with custom-set status code)
        elif status_code == 404: 
            if path.startswith("/bot"):
                code_str = "Bot Not Found"
        
            elif path.startswith("/profile"): 
                code_str = "Profile Not Found"
            
        elif status_code == 422:
            if path.startswith("/bot"): 
                code_str = "Bot Not Found"
                fixed_code = 404
            
            elif path.startswith("/profile"): 
                code_str = "Profile Not Found"
                fixed_code = 404
        
        api = path.startswith("/api") 
        
        # API route handling
        if api: 
            if status_code != 422:
                # Normal handling
                return await http_exception_handler(request, exc) 
        
            else:
                # Special 422 handling
                return await request_validation_exception_handler(request, exc) 
       
        # Return error to user as jinja2 template
        return await templates.e(request, code_str, fixed_code)
