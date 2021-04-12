from tortoise.models import Model
from tortoise import fields

class User(Model):
    """Represents a user"""
    id = fields.BigIntField(pk=True)
    level = fields.IntField()

    def __str__(self):
        return str(self.id)

class Reaction(Model):
    channel_id = fields.BigIntField()
    message_id = fields.BigIntField()
    role_id = fields.BigIntField()
    emoji_id = fields.BigIntField()

class Tag(Model):
    name = fields.TextField()
    content = fields.TextField()
