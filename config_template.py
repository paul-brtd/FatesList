# Copy this to config.py when deploying
import builtins
builtins.bot_logs=789946587203764224
builtins.reviewing_server=789934742128558080 # Bit of a misnomer, but this is the actual main server
builtins.test_server = 794834630942654546 # And THIS is the test server for reviewing bots
# Confusing right? Sorry, i already did 50% using reviewing server so meow ig
builtins.staff_roles = {
    "guild": {
        "id": 00000000000000000,
        "perm": 1
    },
    "bot_review": {
        "id": 789941907563216897,
        "perm": 2
    },
    "mod": {
        "id": 789935016690843708,
        "perm": 3
    },
    "admin": {
        "id": 789935015131742228,
        "perm": 4,
    },
    "owner": {
        "id": 789935014275317780,
        "perm": 5,
    }
}

builtins.site = "fateslist.xyz" # Replace this with your main site

# This value below dont need to be changed
builtins.site_url = "https://" + site

builtins.support_url = "https://discord.gg/PA5vjCRc5H"
builtins.TOKEN = "TOKEN HERE"
builtins.TAGS = ["music", "moderation", "economy", "fun", "anime", "games",
        "web_dashboard", "logging", "streams", "game_stats", "leveling", "roleplay", "utility", "social"]
builtins.pg_user = "postgres" # Postgres Database Username
builtins.pg_pwd = "" # Postgres Database Password
builtins.csrf_secret = ""
builtins.session_key = ""
class OauthConfig:
    client_id = "CLIENT ID HERE"
    client_secret = "CLIENT SECRET HERE"
    scope = ["identify"]
    redirect_uri = "https://" + site + "/auth/login/confirm"

builtins.hubspot_track_code = ''
