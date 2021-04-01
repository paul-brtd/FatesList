from modules.deps import *
def form_body(cls):
    cls.__signature__ = cls.__signature__.replace(
        parameters=[
            arg.replace(default=FForm(""))
            for arg in cls.__signature__.parameters.values()
        ]
    )
    return cls

class BotMeta(BaseModel):
    prefix: str
    library: Optional[str] = None
    invite: str
    website: Optional[str] = None
    description: str
    tags: list
    banner: str
    extra_owners: list
    support: Optional[str]
    long_description: str
    css: str
    custom_prefix: Optional[bool] = False
    open_source: Optional[bool] = False
    html_long_description: bool
    donate: str
    github: Optional[str]
    webhook_type: Optional[str] = ""
    webhook: Optional[str] = ""
    vanity: Optional[str] = ""

class BaseForm(BotMeta):
    custom_prefix: str = FForm("on")
    open_source: str = FForm("on")
    tags: str = FForm("")
    extra_owners: str = FForm("")

@form_body
class BotAddForm(BaseForm):
    bot_id: int

@form_body
class BotEditForm(BaseForm):
    pass

class BotAdd(BotMeta):
    pass

class BotEdit(BotMeta):
    pass
