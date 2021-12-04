from pydantic import BaseModel, validator

class a(BaseModel):
    a: int

    @validator("a")
    def b(*args, **kwargs):
        print("Test")

