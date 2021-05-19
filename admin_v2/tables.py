from piccolo.table import Table
import datetime
from piccolo.columns.column_types import Integer, Varchar, BigInt, Text, Secret, Array, Timestamptz, Boolean

class Vanity(Table, tablename="vanity"):
    type = Integer()
    vanity_url = Text(key = True, primary = True)
    redirect = BigInt()

class User(Table, tablename="users"):
    user_id = BigInt(primary = True, key = True)
    vote_epoch = Timestamptz(help_text = "When the user has last voted")
    description = Text(default = "This user prefers to be an enigma")
    badges = Array(base_column = Text())
    username = Text()
    css = Text(default = "")
    state = Integer(default = 0)
    coins = Integer(default = 0)
    api_token = Secret()

class Bot(Table, tablename="bots"):
    username_cached = Text()
    bot_id = BigInt(primary = True, key = True)
    state = Integer(default = 1)
    description = Varchar(length = 128)
    long_description_type = Integer(default = 0)
    long_description = Text()
    votes = BigInt(default = 0)
    servers = BigInt(default = 0)
    shard_count = BigInt(default = 0)
    shards = Array(base_column = Integer())
    user_count = BigInt(default = 0)
    last_stats_post = Timestamptz(default = datetime.datetime.now())
    created_at = Timestamptz(default = datetime.datetime.now())
    webhook_type = Integer()
    webhook = Text()
    bot_library = Text()
    css = Text(default = "")
    prefix = Varchar(length = 13)
    website = Text()
    discord = Text()
    banner = Text()
    github = Text()
    donate = Text()
    privacy_policy = Text()
    nsfw = Boolean(default = False)
    verifier = BigInt()
    api_token = Secret()
