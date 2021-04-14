from .imports import *
from .permissions import *
from .events import *
from .cache import *

class BotActions():
    class GeneratedObject():
        """
        Instead of crappily changing self, just use a generated object which is at least cleaner
        """
        extra_owners = []
        tags = []
        invite = None

    def __init__(self, bot):
        self.__dict__.update(bot) # Add all kwargs to function
        if "bt" not in self.__dict__ or "user_id" not in self.__dict__:
            raise SyntaxError("Background Task and User ID must be in dict")

        self.generated = self.GeneratedObject() # To keep things clean, make sure we always put changed properties in generated

    async def base_check(self) -> Optional[str]:
        """Perform basic checks for adding/editting bots. A check returning None means success, otherwise error should be returned to client"""
        if self.bot_id == "" or self.prefix == "" or self.description == "" or self.long_description == "" or len(self.prefix) > 9: # Check base fields
            return "Please ensure you have filled out all the required fields and that your prefix is less than 9 characters.", 1

        if self.tags == "":
            return "You must select tags for your bot", 2 # Check tags

        if not self.banner.startswith("https://") and self.banner not in ["", "none"]:
            return "Your banner does not use https://. Please change it", 3 # Check banner and ensure HTTPS
        
        if self.invite:
            if not self.invite.startswith("https://discord.com") or "oauth" not in self.invite:
                return "Invalid Bot Invite: Your bot invite must be in the format of https://discord.com/api/oauth2... or https://discord.com/oauth2...", 4 # Invalid Invite
            self.generated.invite = self.invite # By default, this is None but if explicitly set, use that

        if len(self.description) > 110:
            return "Your short description must be shorter than 110 characters", 5 # Short Description Check

        try:
            bot_object = await get_bot(self.bot_id) # Check if bot exists
        except ValueError: # Just in case someone tries to send a string and not a integer
            return "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours.", 6

        if not bot_object:
            return "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours.", 7
        
        if type(self.tags) != list:
            self.generated.tags = self.tags.split(",")
        else:
            self.generated.tags = self.tags # Generate tags either directly or made to list and then added to generated

        flag = False
        for test in self.generated.tags:
            if test not in TAGS:
                return "One of your tags doesn't exist internally. Please check your tags again", 8 # Check tags internally
            flag = True

        if not flag:
            return "You must select tags for your bot", 9 # No tags found

        if self.banner != "none" and self.banner != "":
            try:
                img = await requests.get(self.banner) # Check content type of banner
            except:
                img = None
            if img is None or img.headers.get("Content-Type") is None or img.headers.get("Content-Type").split("/")[0] != "image":
                return "Banner URL is not an image. Please make sure it is setting the proper Content-Type", 10

        if self.donate != "" and not (self.donate.startswith("https://patreon.com") or self.donate.startswith("https://paypal.me")):
            return "Only Patreon and Paypal.me are allowed for donation links as of right now.", 11 # Check donation link for approved source (paypal.me and patreon

        if self.extra_owners == "": # Generate extra owners list by either adding directly if list or splitting to list, removing extra ones
            self.generated.extra_owners = []
        else:
            if type(self.extra_owners) != list:
                self.generated.extra_owners = self.extra_owners.split(",")
            else:
                self.generated.extra_owners = self.extra_owners

        try:
            self.generated.extra_owners = [int(id.replace(" ", "")) for id in self.generated.extra_owners if int(id.replace(" ", "")) not in self.generated.extra_owners] # Remove extra ones and make all ints
        except:
            return "One of your extra owners doesn't exist or you haven't comma-seperated them.", 12

        if self.github != "" and not self.github.startswith("https://www.github.com"): # Check github for github.com if not empty string
            return "Your github link must start with https://www.github.com", 13

        self.privacy_policy = self.privacy_policy.replace("http://", "https://") # Force https on privacy policy
        if self.privacy_policy != "" and not self.privacy_policy.startswith("https://"): # Make sure we actually have a HTTPS privacy policy
            return "Your privacy policy must be a proper URL starting with https://. URLs which start with http:// will be automatically converted to HTTPS", 14

        if self.vanity == "": # Check if vanity is already being used or is reserved
            pass
        else:
            vanity_check = await db.fetchrow("SELECT DISTINCT vanity_url FROM vanity WHERE lower(vanity_url) = $1 AND redirect != $2", self.vanity.replace(" ", "").lower(), self.bot_id) # Get distinct vanitiss
            if vanity_check is not None or self.vanity.replace("", "").lower() in ["bot", "docs", "redoc", "doc", "profile", "server", "bots", "servers", "search", "invite", "discord", "login", "logout", "register", "admin"] or self.vanity.replace("", "").lower().__contains__("/"): # Check if reserved or in use
                return "Your custom vanity URL is already in use or is reserved", 15

    async def edit_check(self):
        """Perform extended checks for editting bots"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check

        check = await is_bot_admin(int(self.bot_id), int(self.user_id)) # Check for owner
        if not check:
            return "You aren't the owner of this bot.", 17

        check = await get_user(self.user_id)
        if check is None: # Check if owner exists
            return "You do not exist on the Discord API. Please wait for a few hours and try again", 18

    async def add_check(self):
        """Perform extended checks for adding bots"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check # Base check erroring means return base check without continuing as string return means error

        if (await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1", self.bot_id)) is not None:
            return "This bot already exists on Fates List", 19 # Dont add bots which already exist

    async def add_bot(self):
        """Add a bot"""
        check = await self.add_check() # Perform add bot checks
        if check is not None:
            return check # Returning a strung and not None means error to be returned to consumer

        creation = time.time() # Creation Time

        self.bt.add_task(self.add_bot_bt, int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.generated.tags, self.generated.extra_owners, creation, self.generated.invite, self.features, self.html_long_description, self.css, self.donate, self.github, self.webhook, self.webhook_type, self.vanity, self.privacy_policy, self.nsfw) # Add bot to queue as background task

    async def edit_bot(self):
        """Edit a bot"""
        check = await self.edit_check() # Perform edit bot checks
        if check is not None:
            return check

        creation = time.time() # Creation Time
        self.bt.add_task(self.edit_bot_bt, int(self.user_id), self.bot_id, self.prefix, self.library, self.website, self.banner, self.support, self.long_description, self.description, self.generated.tags, self.generated.extra_owners, creation, self.generated.invite, self.webhook, self.vanity, self.github, self.features, self.html_long_description, self.webhook_type, self.css, self.donate, self.privacy_policy, self.nsfw) # Add edit bot to queue as background task

    @staticmethod
    async def add_bot_bt(user_id, bot_id, prefix, library, website, banner, support, long_description, description, tags, extra_owners, creation, invite, features, html_long_description, css, donate, github, webhook, webhook_type, vanity, privacy_policy, nsfw):
        await db.execute("""INSERT INTO bots (
                bot_id, prefix, bot_library,
                invite, website, banner, 
                discord, long_description, description,
                tags, votes, servers, shard_count,
                created_at, api_token, features, 
                html_long_description, css, donate,
                github, webhook, webhook_type, 
                privacy_policy, nsfw) VALUES(
                $1, $2, $3,
                $4, $5, $6,
                $7, $8, $9,
                $10, $11, $12,
                $13, $14, $15,
                $16, $17, $18,
                $19, $20, $21,
                $22, $23, $24)""", bot_id, prefix, library, invite, website, banner, support, long_description, description, tags, 0, 0, 0, int(creation), get_token(132), features, html_long_description, css, donate, github, webhook, webhook_type, privacy_policy, nsfw) # Add new bot info
        if vanity.replace(" ", "") != '':
            await db.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, vanity, bot_id) # Add new vanity if not empty string


        async with db.acquire() as connection: # Acquire a connection
            async with connection.transaction() as tr: # Use a transaction to prevent data loss
                await connection.execute("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", bot_id, user_id, True) # Add new main bot owner
                extra_owners_add = [(bot_id, owner, False) for owner in extra_owners] # Create list of extra owner tuples for executemany executemany
                await connection.executemany("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", extra_owners_add) # Add in one step

        await add_event(bot_id, "add_bot", {}) # Send a add_bot event to be succint and complete 
        owner = int(user_id)
        channel = client.get_channel(bot_logs)
        bot_name = (await get_bot(bot_id))["username"]
        add_embed = discord.Embed(title="New Bot!", description=f"<@{owner}> added the bot <@{bot_id}>({bot_name}) to queue!", color=0x00ff00)
        add_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{bot_id}")
        try:
            member = channel.guild.get_member(owner)
            if member is not None:
                await member.send(embed = add_embed) # Send user DM if possible

        except:
            pass
        await channel.send(f"<@&{staff_ping_add_role}>", embed = add_embed) # Send message with add bot ping

    @staticmethod
    async def edit_bot_bt(user_id, bot_id, prefix, library, website, banner, support, long_description, description, tags, extra_owners, creation, invite, webhook, vanity, github, features, html_long_description, webhook_type, css, donate, privacy_policy, nsfw):
        await db.execute("UPDATE bots SET bot_library=$2, webhook=$3, description=$4, long_description=$5, prefix=$6, website=$7, discord=$8, tags=$9, banner=$10, invite=$11, github = $12, features = $13, html_long_description = $14, webhook_type = $15, css = $16, donate = $17, privacy_policy = $18, nsfw = $19 WHERE bot_id = $1", bot_id, library, webhook, description, long_description, prefix, website, support, tags, banner, invite, github, features, html_long_description, webhook_type, css, donate, privacy_policy, nsfw) # Update bot with new info

        async with db.acquire() as connection: # Acquire a connection
            async with connection.transaction() as tr: # Make a transaction to afoid data loss
                owners = await connection.fetch("SELECT owner FROM bot_owner where bot_id = $1 AND main = false", bot_id)
                extra_owners_ignore = [] # Extra Owners to ignore because they have already been counted in the database (already extra owners)
                extra_owners_delete = [] # Extra Owners to delete
                extra_owners_add = [] # Extra Owners to add
                for owner in owners: # Loop through owners and add to delete list if not in new extra owners
                    if owner["owner"] not in extra_owners:
                        extra_owners_delete.append((bot_id, owner["owner"]))
                    else:
                        extra_owners_ignore.append(owner["owner"]) # Ignore this user when adding users
                await connection.executemany("DELETE FROM bot_owner WHERE bot_id = $1 AND owner = $2 AND main = false", extra_owners_delete) # Delete in one step
                for owner in extra_owners:
                    if owner not in extra_owners_ignore:
                        extra_owners_add.append((bot_id, owner, False)) # If not in ignore list, add to add list
                await connection.executemany("INSERT INTO bot_owner (bot_id, owner, main) VALUES ($1, $2, $3)", extra_owners_add) # Add in one step

        async with db.acquire() as connection:
            async with connection.transaction():
                check = await connection.fetchrow("SELECT vanity FROM vanity WHERE redirect = $1", bot_id) # Check vanity existance
                if check is None:
                    if vanity.replace(" ", "") != '': # If not there for this bot, insert new one
                        await connection.execute("INSERT INTO vanity (type, vanity_url, redirect) VALUES ($1, $2, $3)", 1, vanity, bot_id)
                else:
                    if vanity == '':
                        vanity = None # If vanity is expty string, there is no vanity

                    await connection.execute("UPDATE vanity SET vanity_url = $1 WHERE redirect = $2", vanity, bot_id) # Update the vanity since bot already use it
        await add_event(bot_id, "edit_bot", {"user": str(user_id)}) # Send event
        channel = client.get_channel(bot_logs)
        owner = int(user_id)
        edit_embed = discord.Embed(title="Bot Edit!", description=f"<@{owner}> has edited the bot <@{bot_id}>!", color=0x00ff00)
        edit_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{bot_id}")
        await channel.send(embed = edit_embed) # Send message to channel

class BotListAdmin():

    # Some messages
    bot_not_found = "Bot could not be found"
    must_claim = "You must claim this bot using +claim on the testing server before approving or denying it. If you have claimed it, make sure it is not already verified"
    good = 0x00ff00 # "Good" color for positive things
    bad = discord.Color.red()

    def __init__(self, bot_id, mod):
        self.bot_id = bot_id
        self.mod = mod # Mod is the moderator who performed the request
        self.str_mod = str(mod)
        self.channel = client.get_channel(bot_logs)
        self.guild = self.channel.guild

    async def _get_main_owner(self):
        return await db.fetchrow("SELECT owner FROM bot_owner WHERE bot_id = $1 AND main = true", self.bot_id)

    async def _give_roles(self, role, users):
        for user in users:
            try:
                member = self.guild.get_member(int(user))
                await member.add_roles(self.guild.get_role(role))
            except:
                pass

    async def claim_bot(self):
        check = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $2 AND state = $1", enums.BotState.pending, self.bot_id)
        if not check:
            return self.bot_not_found
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.under_review, self.bot_id)
        claim_embed = discord.Embed(title="Bot Under Review", description = f"<@{self.bot_id}> is now under review by <@{self.mod}> and should be approved or denied soon!", color = self.good)
        claim_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}")
        await add_event(self.bot_id, "claim_bot", {"user": self.str_mod})
        await self.channel.send(embed = claim_embed)

    async def approve_bot(self, feedback):
        owners = await db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", self.bot_id)
        if not owners:
            return self.bot_not_found
        check = await db.fetchrow("SELECT state FROM bots WHERE bot_id = $1", self.bot_id)
        if check["state"] != enums.BotState.under_review:
            return self.must_claim 
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.approved, self.bot_id)
        await add_event(self.bot_id, "approve_bot", {"user": self.str_mod})
        owner = [obj["owner"] for obj in owners if obj["main"]][0]
        approve_embed = discord.Embed(title="Bot Approved!", description = f"<@{self.bot_id}> by <@{owner}> has been approved", color = self.good)
        approve_embed.add_field(name="Feedback", value=feedback)
        approve_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}")
        await self._give_roles(bot_dev_role, [owner["owner"] for owner in owners])
        try:
            member = self.guild.get_member(int(owner))
            if member is not None:
                await member.send(embed = approve_embed)
        except:
            pass
        await self.channel.send(embed = approve_embed)

    async def unverify_bot(self, reason):
        owner = await self._get_main_owner()
        if owner is None:
            return False # No bot found
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $1", enums.BotState.pending, self.bot_id)
        await add_event(self.bot_id, "unverify_bot", {"user": self.str_mod})
        unverify_embed = discord.Embed(title="Bot Unverified!", description = f"<@{self.bot_id}> by <@{owner['owner']}> has been unverified", color=self.bad)
        unverify_embed.add_field(name="Reason", value=reason)
        await self.channel.send(embed = unverify_embed)

    async def deny_bot(self, reason):
        owner = await self._get_main_owner()
        if owner is None:
            return self.bot_not_found
        check = await db.fetchrow("SELECT state FROM bots WHERE bot_id = $1", self.bot_id)
        if check["state"] != enums.BotState.under_review:
            return self.must_claim
        await db.execute("UPDATE bots SET state = 2 WHERE bot_id = $1", self.bot_id)
        await add_event(self.bot_id, "deny_bot", {"user": self.str_mod, "reason": reason})
        deny_embed = discord.Embed(title="Bot Denied!", description = f"<@{self.bot_id}> by <@{owner['owner']}> has been denied", color=self.bad)
        deny_embed.add_field(name="Reason", value=reason)
        await self.channel.send(embed = deny_embed)
        try:
            member = self.guild.get_member(int(owner["owner"]))
            if member is not None:
                await member.send(embed = deny_embed)
        except:
            pass

    async def ban_bot(self, reason):
        ban_embed = discord.Embed(title="Bot Banned", description=f"<@{self.bot_id}> has been banned", color=self.bad)
        ban_embed.add_field(name="Reason", value = reason)
        await self.channel.send(embed = ban_embed)
        try:
            await self.guild.kick(self.guild.get_member(self.bot_id))
        except:
            pass
        await db.execute("UPDATE bots SET state = 4 WHERE bot_id = $1", self.bot_id)
        await add_event(self.bot_id, "ban_bot", {"user": self.str_mod, "reason": reason})

    # Unban or requeue a bot
    async def unban_bot(self, state):
        if state == 2:
            word = "removed from the deny list"
            title = "Bot requeued"
        else:
            word = "unbanned"
            title = "Bot unbanned"
        unban_embed = discord.Embed(title=title, description=f"<@{self.bot_id}> has been {word}", color=self.good)
        await self.channel.send(embed = unban_embed)
        if state == 2:
            await db.execute("UPDATE bots SET state = 1 WHERE bot_id = $1", self.bot_id)
            await add_event(self.bot_id, "requeue_bot", {"user": self.str_mod})
        else:
            await db.execute("UPDATE bots SET state = 0 WHERE bot_id = $1", self.bot_id)
            await add_event(self.bot_id, "unban_bot", {"user": self.str_mod})

    async def certify_bot(self):
        owners = await db.fetch("SELECT owner FROM bot_owner WHERE bot_id = $1", self.bot_id)
        if not owners:
            return "Bot Not Found"
        await db.execute("UPDATE bots SET state = 6 WHERE bot_id = $1", self.bot_id)
        certify_embed = discord.Embed(title = "Bot Certified", description = f"<@{self.mod}> certified the bot <@{self.bot_id}>", color = self.good)
        certify_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}")
        await self.channel.send(embed = certify_embed)
        await add_event(self.bot_id, "certify_bot", {"user": self.str_mod})
        await self._give_roles(certified_dev_role, [owner["owner"] for owner in owners])
