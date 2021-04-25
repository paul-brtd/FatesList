from piccolo.table import Table
from piccolo.columns.column_types import Integer, Varchar, BigInt, Text, Secret

class Vanity(Table, tablename="vanity"):
    type = Integer()
    vanity_url = Text(key = True, primary = True)
    redirect = BigInt()

class User(Table, tablename="users"):
    user_id = BigInt(primary = True, key = True)
    api_token = Secret()
    vote_epoch = BigInt(help_et = "When the user has last voted")
    description = Text()
