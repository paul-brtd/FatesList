from modules.deps import *
def form_body(cls):
    cls.__signature__ = cls.__signature__.replace(
        parameters=[
            arg.replace(default=FForm(""))
            for arg in cls.__signature__.parameters.values()
        ]
    )
    return cls

class FullBot(BaseModel):
    prefix: str
    library: Optional[str] = None
    invite: str
    website: Optional[str] = None
    description: str
    tags: str
    banner: str
    extra_owners: str
    support: Optional[str]
    long_description: str
    css: str
    custom_prefix: Optional[bool] = False
    open_source: Optional[bool] = False
    html_long_description: bool
    donate: str
    github: Optional[str]

class BotAdd(FullBot):
    bot_id: int

@form_body
class BotAddForm(BotAdd):
    custom_prefix: str = FForm("on")
    open_source: str = FForm("on")

class BotEdit(FullBot):
    webhook: str
    webhook_type: str
    vanity: str

@form_body
class BotEditForm(BotEdit):
    custom_prefix: str = FForm("on")
    open_source: str = FForm("on")

print(BotEditForm)
