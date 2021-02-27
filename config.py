from config_secrets import TOKEN_MAIN, TOKEN_SERVER, pg_pwd, csrf_secret, session_key, oauth_client_secret, ratelimit_bypass_key
bot_logs = 789946587203764224 # #bot-logs in support server
appeals_channel = 813422505900376095 # #resubmissions-and-appeals in support server
site_errors_channel = 815055552857243699 # Where to log site errors
bots_role = 789934898408194059 # BOTS role in support server
bot_dev_role = 789935019531304991 # BOT Developer in support server
certified_dev_role = 792204630922100797 # Certified Developer in support server
reviewing_server=789934742128558080 # Bit of a misnomer, but this is the actual main server
test_server = 794834630942654546 # And THIS is the test server for reviewing bots
# Confusing right? Sorry, i already did 50% using reviewing server so meow ig
staff_roles = {
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
# TODO: Add Timed Badges
special_badges = {
    "STAFF": {
        "name": "Staff",
        "description": "This is a Fates List Staff Member",
        "image": "/static/assets/img/staff.png",
        "staff": True, # Is this badge only for staff?
        "certified": False # Certified
    },
    "CERTIFIED": {
        "name": "Certified Bot Dev.",
        "description": "This is a certified bot developer",
        "image": "/static/assets/img/certified.png",
        "staff": False, # Is this badge only for staff?
        "certified": True # Certified
    }
}

features = {
    "custom_prefix": {
        "type": "positive",
        "description": "A bot with Custom Prefix supports changing of the bot's prefix and is hence considered positive by Fates List"
    },
    "open_source": {
        "type": "positive",
        "description": "These bots are open source meaning they can easily be audited and/or potentially self hosted."
    }
} 

site = "fateslist.xyz" # Replace this with your domain
server_site = "serverbot.fateslist.xyz" # Same as above

server_bot_invite = "https://discord.com/api/oauth2/authorize?client_id=811073947382579200&permissions=67649&scope=bot" # Ensure that it uses 67649 for perms

# This value below dont need to be changed
site_url = "https://" + site

support_url = "https://discord.gg/PA5vjCRc5H"
TAGS = {"music": "fa-solid:music", "moderation": "fa-solid:hammer", "economy": "fa-solid:coins", "fun": "fa-solid:heart", "anime": "fa-solid:camera", "games": "fa-solid:smile", "web_dashboard": "fa-solid:chart-bar", "logging": "fa-solid:chart-line", "game_stats": "fa-solid:chart-pie", "leveling": "fa-solid:arrow-up", "roleplay": "fa-solid:cat", "utility": "fa-solid:desktop", "social": "fa-solid:users"}
pg_user = "postgres" # Postgres Database Username
class OauthConfig:
    client_id = "798951566634778641"
    client_secret = oauth_client_secret
    scope = ["identify"]
    redirect_uri = "https://" + site + "/auth/login/confirm"

