import sys

sys.path.append("../FatesList")
import datetime

from piccolo.columns.column_types import (UUID, Array, BigInt, Boolean, Float,
                                          ForeignKey, Integer, Secret, Text,
                                          Timestamptz, Varchar)
from piccolo.columns.readable import Readable
from piccolo.table import Table

import modules.models.enums as enums


class Vanity(Table, tablename="vanity"):
    type = Integer()
    vanity_url = Text(key = True, primary = True)
    redirect = BigInt()

class User(Table, tablename="users"):
    user_id = BigInt(primary = True, key = True)
    vote_epoch = Timestamptz(help_text = "When the user has last voted")
    description = Text(default = "This user prefers to be an enigma")
    badges = Array(base_column = Text(), help_text = "Custom User Badges. The ones currently on profiles are special and manually handled without using this column.")
    username = Text()
    css = Text(default = "")
    state = Integer(default = 0, choices = enums.UserState)
    coins = Integer(default = 0)
    js_allowed = Boolean(default = False, help_text = "Is the user allowed to use javascript")
    api_token = Text()

class Bot(Table, tablename="bots"):
    username_cached = Text()
    bot_id = BigInt(primary = True, key = True)
    state = Integer(choices = enums.BotState, default = 1)
    description = Varchar(length = 128)
    long_description_type = Integer(default = 0, choices = enums.LongDescType)
    long_description = Text()
    votes = BigInt(default = 0)
    guild_count = BigInt(default = 0)
    shard_count = BigInt(default = 0)
    shards = Array(base_column = Integer())
    user_count = BigInt(default = 0)
    last_stats_post = Timestamptz(default = datetime.datetime.now())
    created_at = Timestamptz(default = datetime.datetime.now())
    webhook_type = Integer(choices = enums.WebhookType)
    webhook = Text()
    bot_library = Text()
    css = Text(default = "")
    prefix = Varchar(length = 13)
    di_text = Text(help_text = "Discord Integration Text")
    website = Text()
    discord = Text()
    banner_card = Text()
    banner_page = Text()
    github = Text()
    donate = Text()
    privacy_policy = Text()
    nsfw = Boolean(default = False)
    verifier = BigInt()
    api_token = Text()
    js_allowed = Boolean(default = True)
    invite = Text()
    invite_amount = Integer(default = 0)
    features = Array(base_column = Text(), default = [])

class BotTag(Table, tablename="bot_tags"):
    bot_id = ForeignKey(references=Bot)
    tag = Text(null = False)

class BotReview(Table, tablename="bot_reviews"):
    id = UUID(primary = True)
    bot_id = ForeignKey(references=Bot)
    user_id = ForeignKey(references=User)
    star_rating = Float(help_text = "Amount of stars a bot has")

    @classmethod
    def get_readable(cls):
        return Readable(template="%s", columns=[cls.name])
