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

# Current API Version
API_VERSION = 2

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
            "We reserve the right to make changes to our privacy policy at any time with an announcement on our support server. "
            "We also reserve the right to edit bot pages at any time to protect our site"
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
        ),
        "access": (
            "Fates List needs to access your username, avatar, status and user id in order to identify who you are on Discord "
            "so you can use the site. Fates List also needs to know which servers you are in for server listing if you "
            "choose to enable it. Fates List also needs the ability to join servers for you if you choose to be automatically "
            "added to the support server on login."
        )
    },
    "extras": {
        "security": (
            "Our site is secure and we try to ensure that only you and Fates List Staff can edit your bot and that all "
            "actions require proper permission and clearance to be used."
        ),
        "contact": (
            "You can contact our staff by joining the Fates List support server. Note that our support server is the only "
            "official way of contacting the Fates List staff team and we may not respond elsewhere."
        ),
        "privacy": (
            "Your privacy matters to us. By continuing, you agree to your data being processed and/or stored for analytical "
            "purpose as per our privacy policy. The data we collect is your IP address, username, user id, avatar and current "
            "discord status and any info you submit to us. We may also use IPs for access logs and due to technical reasons and "
            "these cannot be deleted from our servers either so use a VPN if you do not want your IP to be exposed. We also "
            "store timestamps of when you vote for a bot and these timestamps are exposed to bots and may be used by bot "
            "owners for their own purposes such as determining whether you can vote for a bot or not."
        ),
        "updates": (
            "We update constantly, and changes are made often. By joining the support server, you may be notified of changes "
            "we make, including privacy policy changes. This page may be changed at any time in the future."
        ),
        "contributing": (
            "Fates List was made possible thanks to the help of our staff team. In particular, Fates List would like to give "
            "a shoutout to Skylarr#0001 for giving us a Digital Ocean droplet to host Fates List on. You can find the source "
            "code for Fates List at https://github.com/Fates-List"
        ),
        "important_note": (
            "We are not affiliated with Discord Inc. or any of its partners or affiliates."
        ),
    }
}

rules = {
    "botreq": {
        "basics": [
            (
                "Your bot may not be a fork or instance of another bot without substantial modifications and prior "
                "permission from the owner of the bot you have forked/made an instance of."
            ),
            (
                "Your bot should handle errors in a user friendly way. A way of reporting errors is a nice extra "
                "tidbit to have though not strictly required. Giving tracebacks is allowed if it does not leak "
                "sensitive information such as bot tokens or private information on a user."
            ),
            (
                "Your bot must respect the Discord API and ratelimits. This also means that your bot should not "
                "spam messages or be a 'rainbow role' bot."
            ),
            (
                "Custom bots based of/dependant on/running an instance of another bot such as bot" 
                "makers not allowed by discord, BotGhost, MEE6 Premium, Wick VIP is prohibited "
                "unless it has unique features that you have added to it and can be configured on other "
                "servers by users."
            ),
            (
                "For frameworks such as redbot, you must have at least 3 custom made cogs "
                "(or the equivalent for other frameworks). You must give credits to any framework "
                "you are using. **BDFD/BDScript/other bot makers are not allowed on Fates List "
                "unless it is also allowed by Discord and your bot is high-quality and has "
                "features**"
            )
        ],
        "commands": [
            (
                "Your bot must have a working help command"
            ),
            (
                "If your bot has level messages or welcome messages, it must be optional and disableable"
            ),
            (
                "Your bot should not DM users when it join unless it needs to DM the *owner* "
                "important or sensitive information (such as Wick's rescue key) "
            ),
            (
                "Your bot should not DM users when they join a server unless a server manager chooses to "
                "enable such a feature. Bots that do need to DM users such as verification bots may be exempt "
                "from this rule on a case by case basis"
            ),
            (
                "All commands of a bot should check user and their own permissions before doing any "
                "action. For example, your bot should not kick users unless the user and the bot has the "
                "Kick Members permission. **Commands may not be admin locked and NSFW commands must be "
                "locked to NSFW channels"
            ),
            (
                "Commands must have a purpose (no filler commands). Filler commands are ignored and will "
                "make your bot low-quality. An example of filler commands/commands with no purpose is a bot "
                "with 20 purge commands or commands which are repeated in different ways or serve the same "
                "purpose"
            ),
            (
                "Bots *should* have at least 5 working commands and at least 80% of commands shown in "
                "its help command working. If your bot has a really unique feature however, this rule may "
                "be reconsidered for your bot."
            ),
            (
                "Sensitive commands (such as eval) should be locked to bot owners only. Fates List is not "
                "responsible for the code you run or for any arbitary code execution/privilege escalation on "
                "your bot."
            )
        ],
        "prefixes": [
            (
                "Bots with common prefixes (`!`, `?`, `.`, `;`, etc) should have configurable prefix systems "
                "or they may be muted on the support server. You may change the prefix for just Fates List "
                "if you want to."
            ),
            (
                "You should use the Customizable Prefix feature in your bots settings to denote whather custom "
                "prefixes are supported. This is to make it easier for users to know this"
            )
        ],
        "safety": [
            (
                "Bots should not mass DM or be malicious in any way such as mass nuke, scam bots, "
                "free nitro bots. This also applies to servers as well when server listing is done."
            ),
            (
                "DMing staff to ask for your bot to be approved/reviewed is strictly prohibited. "
                "Your bot will be denied or banned if you do so."
            ),
            (
                "Your bot must not have a copyrighted avatar or username."
            ),           
            (
                "Abusing Discord (mass creating or deleting channels, mass DM/spam/nuke bots) is strictly "
                "prohibited and doing so will get you and/or your bot banned from the list and server."
            ),
            (
                "Your bot may not be hosted on Glitch/Repl Free Plan and use a software to ping your "
                "project. This is also against Repl/Glitch ToS."
            ),
            (
                "Your bot must be online during testing"
            )
        ], 
        "notes": [
            (
                "You can always repeal a ban or resubmit your bot. To do so, just login, click your username "
                "> My Profile > your bot > View and then click resubmit"
            )
        ]
    }
}
