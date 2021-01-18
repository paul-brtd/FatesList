from fastapi import APIRouter

router = APIRouter()

@router.patch("/")
async def fates_hook_webhook():
    print(router.fh_func)
