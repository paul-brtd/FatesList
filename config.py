from config_secrets import TOKEN_MAIN, TOKEN_SERVER, TOKEN_ULA, pg_pwd, csrf_secret, session_key, oauth_ula_client_secret, oauth_client_secret, ratelimit_bypass_key, stripe_publishable_key, stripe_secret_key, stripe_webhook_secret, recaptcha_client, recaptcha_secret, ula_session_key, bb_add_key, bb_edit_key, test_server_manager_key
bot_logs = 789946587203764224 # #bot-logs in support server
appeals_channel = 813422505900376095 # #resubmissions-and-appeals in support server
site_errors_channel = 815055552857243699 # Where to log site errors
bots_role = 789934898408194059 # BOTS role in support server
staff_ping_add_role=815174404932894731
bot_dev_role = 789935019531304991 # BOT Developer in support server
certified_dev_role = 792204630922100797 # Certified Developer in support server
main_server=789934742128558080 # Main server
test_server = 794834630942654546 # The test server for reviewing bots
owner = 563808552288780322

# Messages
approve_feedback = "There was no feedback given for this bot. It was likely a good bot, but you can ask any staff member about feedback if you wish"
deny_feedback = "There was no reason specified. DM/Ping Mod Mail to learn why"

# Confusing right? Sorry, i already did 50% using reviewing server so meow ig
staff_roles = {
    "user": {
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

server_bot_invite = "https://discord.com/api/oauth2/authorize?client_id=811073947382579200&permissions=67649&scope=bot" # Ensure that it uses 67649 for perms

# This value below dont need to be changed
site_url = "https://" + site
support_url = "https://discord.gg/PA5vjCRc5H"
TAGS = {"music": "fa-solid:music", "moderation": "fa-solid:hammer", "economy": "fa-solid:coins", "fun": "fa-solid:heart", "anime": "fa-solid:camera", "games": "fa-solid:smile", "web_dashboard": "fa-solid:chart-bar", "logging": "fa-solid:chart-line", "game_stats": "fa-solid:chart-pie", "leveling": "fa-solid:arrow-up", "roleplay": "fa-solid:cat", "utility": "fa-solid:desktop", "social": "fa-solid:users"}
SERVER_TAGS = {"music": "fa-solid:music", "moderation": "fa-solid:hammer", "economy": "fa-solid:coins", "fun": "fa-solid:heart", "anime": "fa-solid:camera", "games": "fa-solid:smile", "web_dashboard": "fa-solid:chart-bar", "logging": "fa-solid:chart-line", "game_stats": "fa-solid:chart-pie", "leveling": "fa-solid:arrow-up", "roleplay": "fa-solid:cat", "utility": "fa-solid:desktop", "social": "fa-solid:users"}


pg_user = "postgres" # Postgres Database Username

bans_data = {
    "1": {
        "type": "global",
        "desc": "you cannot/will not be able to login or access the support server"
    },
    "2": {
        "type": "login",
        "desc": "you will not be able to login but should still be able to access the support server" 
    },
    "3": {
        "type": "profile edit",
        "desc": "you will not be able to edit your profile"
    },
    "4": {
        "type": "data deletion request",
        "desc": "Contact modmail to be unbanned"
    }
}

class OauthConfig:
    client_id = "798951566634778641"
    client_secret = oauth_client_secret
    redirect_uri = "https://" + site + "/auth/login/confirm"

class ULAOauthConfig:
    client_id = "733766762658529360"
    client_secret = oauth_ula_client_secret
    redirect_uri = "https://ula.fateslist.xyz/login/confirm"

# ULA 

ula_api_url = "https://ulapi.fateslist.xyz"
