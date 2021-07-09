import builtins
import os

from config_secrets import *

bot_logs = 836326348326043648 # #bot-logs in support server
server_logs = 837048691965034496 # Server logs in support server
appeals_channel = 836326351387623454 # #resubmissions-and-appeals in support server
site_errors_channel = 836326323281592330 # Where to log site errors
bots_role = 836326315946672158 # BOTS role in support server
staff_ping_add_role=836326316188893275
bot_dev_role = 836326314344185876 # BOT Developer in support server
certified_dev_role = 836326313283026995 # Certified Developer in support server
main_server = 789934742128558080 # Main server
staff_server = 816130947274899487 # The staff server
staff_ag = 845931695387181066 # Access Granted role in staff server
test_botsrole = 845940351339987004 # Bots role on test server
test_staffrole = 846028433985503232 # Staff role on test server
test_server = 845928429357367316 # Test Server
owner = 563808552288780322
instance_name = "main"

# Messages
approve_feedback = "There was no feedback given for this bot. It was likely a good bot, but you can ask any staff member about feedback if you wish"
deny_feedback = "There was no reason specified. DM/Ping Mod Mail to learn why"

# Banned in vanity

reserved_vanity = [
    "bot", 
    "docs",
    "redoc",
    "doc", 
    "apidocs",
    "profile",
    "server",
    "bots", 
    "servers", 
    "search",
    "invite", 
    "discord", 
    "login", 
    "logout", 
    "register",
    "admin",
    "signup",
    "fuck"
]

md_extensions = [
    "extra",
    "abbr",
    "attr_list",
    "def_list", 
    "fenced_code",
    "footnotes",
    "tables",
    "admonition", 
    "codehilite", 
    "meta", 
    "nl2br",
    "sane_lists",
    "toc",
    "wikilinks", 
    "smarty", 
    "md_in_html"
]

staff_roles = {
    "user": {
        "id": 00000000000000000,
        "staff_id": 0000000000000000,
        "perm": 0
    },
    "auditor": {
        "id": 000000000000000000,
        "staff_id": 0000000000000000,
        "perm": 1
    }, # Unused
    "bot_reviewer": {
        "id": 836326311147864104,
        "staff_id": 845931373520748545,
        "perm": 2
    },
    "mod": {
        "id": 836326309528600627,
        "staff_id": 845931545076432931,
        "perm": 3
    },
    "admin": {
        "id": 836326305666039848,
        "staff_id": 845930903883874336,
        "perm": 4,
    },
    "developer": {
        "id": 836326304860078160,
        "staff_id": 848745475494641694,
        "perm": 5
    },
    "head_admin": {
        "id": 836349482340843572,
        "staff_id": 845930541018513428,
        "perm": 6
    },
    "owner": {
        "id": 836326299223195738,
        "staff_id": 830540676952227863,
        "perm": 7,
    }
} 

# TODO: Add Timed Badges
special_badges = (
    {
        "id": "STAFF",
        "name": "Staff",
        "description": "This is a Fates List Staff Member",
        "image": "/static/assets/img/staff.png",
        "req": ("staff",) # Is this badge only for staff?
    },
    {
        "id": "CERTDEV",
        "name": "Certified Bot Developer",
        "description": "This is a certified bot developer",
        "image": "/static/assets/img/certified.png",
        "req": ("cert_dev",) # Certified
    },
    {
        "id": "BOTDEV",
        "name": "Bot Developer",
        "description": "This is a bot developer",
        "image": "/static/assets/img/botdev.png",
        "req": ("bot_dev",)
    },
    {
        "id": "DISCORD_MEMBER",
        "name": "Discord Member",
        "description": "This user is on our support server",
        "image": "/static/assets/img/dmember.png",
        "req": ("discord_member",)
    }
)

features = {
    "custom_prefix": {
        "name": "Customizable Prefix",
        "type": "positive",
        "description": "A bot with Custom Prefix supports changing of the bots prefix and is considered positive by Fates List"
    },
    "open_source": {
        "name": "Open Source",
        "type": "positive",
        "description": "These bots are open source meaning they can easily be audited and/or potentially self hosted."
    },
    "slash_command": {
        "name": "Slash Commands",
        "type": "positive",
        "description": "Slash commands are a brand new way to interact with bots to deliver a better experience!"
    }
} 

site = "fateslist.xyz" 

server_bot_invite = "https://discord.com/api/oauth2/authorize?client_id=811073947382579200&permissions=67649&scope=bot" # Ensure that it uses 67649 for perms

# This value below dont need to be changed
site_url = "https://" + site
support_url = "https://discord.gg/cMAnfu8AJB"

pg_user = "postgres" # Postgres Database Username

bans_data = {
    "1": {
        "type": "global",
        "desc": "you cannot/will not be able to login or access the support server"
    },
    "2": {
        "type": "profile edit",
        "desc": "you will not be able to edit your profile"
    },
    "3": {
        "type": "data deletion request",
        "desc": "you can contact modmail to be unbanned"
    }
}

langs = {
    "default": "Default",
    "en": "English",
    "es": "Spanish/Español",
    "it": "Italian"
}

privacy_policy = {
    "tos": [
        (
            "We reserve the right to make changes to our privacy policy at any time "
            "with or without any announcements. We also reserve the right to edit "
            "bot pages at any time to protect our site"
        ),
        (
            "We may store cookies on your browser in order to keep you signed in and to "
            "potentially improve the site experience"
        ),
        (
            "You must be at least 13 years old in order to use this service"
        ),
        (
            "You may not DDOS, attempt to exploit or otherwise harm the service without "
            "permission from the owner(s) of Fates List"
        ),
        (
            "You may not leak private information on another user's bots, such as API tokens, without permission "
            "from the bot owner or from a Head Admin or higher. This is legally binding and will be enforced "
            "to the fullest degree permitted by law"
        ),
        (
            "May log you IP address which may be used by Fates List to protect against abuse of our service "
            "or by approved third parties, such as Digital Ocean and local law enforcement. "
            "Most sites log IP addresses and they are usually changed periodically by your Internet Service Provider"
        ),
        (
            "You agree that we are not responsible for any possible accidents that may happen such as "
            "leaked IP addresses or leaked API tokens. We aim to never have this happen but accidents can "
            "and do happen at times"
        ),
        (
            "You must follow Discord's Terms Of Service"
        )
    ],
    "data": {
        "collection": (
            "We cache user information from Discord as well as handling ratelimits using Redis to significantly improve "
            "site performance and your experience using the site. We store data on bots using PostgreSQL. Information you "
            "give us, such as bots information, badges you or your bots earn in the future, and your profile information "
            "is all stored on our servers. We also use RabbitMQ to store actions like bot adding, editing and deleting "
            "for further processing by our RabbitMQ workers."
        ),
        "deletion": (
            "You can easily have your data deleted at any time. You may delete your account by opening a Data Deletion Request "
            "on our support server. You can delete your bots from Bot Settings. Data Deletion Requests may take up to 24 hours "
            "to process and the time of when you last vote will still be stored to prevent against abuse. All of your bots will "
            "also be deleted permanently and this is irreversible"
        )
    },
    "security": (
        "Our site is secure and we try to ensure that only you and Fates List Staff can edit your bot and that all "
        "actions require proper permission and clearance to be used."
    ),
    "contact": (
        "You can contact our staff by joining the Fates List support server"
    ),
    "updates": (
        "We update constantly, and changes are made often. By joining the support server, you may be notified of changes "
        "we make. This page may be changed at any time without notice, prior, during or afterwards"
    )
}
