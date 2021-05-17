"""Functions to handle execution of arbitary code in admin commands"""
from termcolor import cprint
import orjson
import inspect
import asyncio
import nest_asyncio
nest_asyncio.apply()

def handle_await(code):
    if "await " not in code:
        return code.replace("return ", "ret = ")
    code = "".join(["    " + txt + "\n" for txt in code.lstrip().split('\n')])
    return f"""
async def task_runner():
{code}

ret = asyncio.run(task_runner())
"""

def serialized(obj):
    try:
        orjson.dumps({"rc": obj})
        return True
    except:
        return False

def exec_op(op):
    try:
        op = handle_await(op)
        loc = {}
        exec(op.lstrip(), globals() | locals(), loc)
        _ret = loc["ret"] if loc.get("ret") is not None else loc # Get return stuff
        if not loc:
            _ret = None # No return or anything
        _err = False
    except Exception as exc:
        _ret = f"{type(exc).__name__}: {exc}"
        cprint(_ret, "red")
        _err = True
    return _ret if serialized(_ret) else str(_ret), _err
