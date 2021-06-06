from .imports import *
from .permissions import *
from .events import *
from .cache import *
from .rabbitmq import *
from .helpers import *

class BotActions():
    class GeneratedObject():
        """Instead of crappily changing self, just use a generated object which is at least cleaner"""
        extra_owners = []
        tags = []
        invite = None
        webhook_secret = None

    def __init__(self, bot):
        self.__dict__.update(bot) # Add all kwargs to class
        logger.debug("Request Acknowledged")
        self.generated = self.GeneratedObject() # To keep things clean, make sure we always put changed properties in generated

    def gen_rabbit_dict(self):
        rmq_dict = self.__dict__.copy()
        del rmq_dict["generated"]
        del rmq_dict["custom_prefix"]
        del rmq_dict["open_source"]
        for key in self.generated.__dict__.keys():
            rmq_dict[key] = self.generated.__dict__[key]
        logger.trace(f"RabbitMQ dict is {rmq_dict}")
        return rmq_dict

    async def base_check(self) -> Optional[str]:
        """Perform basic checks for adding/editting bots. A check returning None means success, otherwise error should be returned to client"""
        if self.bot_id == "" or self.prefix == "" or self.description == "" or self.long_description == "" or len(self.prefix) > 9: # Check base fields
            return "Please ensure you have filled out all the required fields and that your prefix is less than 9 characters.", 1

        if self.tags == "":
            return "You must select tags for your bot", 2 # Check tags

        if not self.banner.startswith("https://") and self.banner not in ["", "none"]:
            return "Your banner does not use https://. Please change it", 3 # Check banner and ensure HTTPS
        
        if self.invite:
            if self.invite.startswith("P:"): # Check if perm auto is specified
                perm_num = self.invite.split(":")[1].split("|")[0]
                try:
                    perm_num = int(perm_num)
                except ValueError:
                    return "Invalid Bot Invite: Your permission number must be a integer", 4 # Invalid Invite
            elif not self.invite.startswith("https://discord.com") or "oauth" not in self.invite:
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
        check = await vanity_check(self.bot_id, self.vanity) # Check if vanity is already being used or is reserved
        if check:
            return "Your custom vanity URL is already in use or is reserved", 15
        if self.webhook_secret:
            if len(self.webhook_secret) < 8:
                return "Your webhook secret must be at least 8 characters long", 16
            self.generated.webhook_secret = self.webhook_secret

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

        await add_rmq_task("bot_add_queue", self.gen_rabbit_dict()) # Add to add bot RabbitMQ

    async def edit_bot(self):
        """Edit a bot"""
        check = await self.edit_check() # Perform edit bot checks
        if check is not None:
            return check

        await add_rmq_task("bot_edit_queue", self.gen_rabbit_dict()) # Add to edit bot RabbitMQ

class BotListAdmin():
    """Class to control and handle bots"""

    # Some messages
    bot_not_found = "Bot could not be found"
    must_claim = "You must claim this bot using +claim on the testing server before approving or denying it. If you have claimed it, make sure it is not already verified"
    good = 0x00ff00 # "Good" color for positive things
    bad = discord.Color.red()

    def __init__(self, bot_id, mod, force = False):
        self.bot_id = bot_id # The bot id to handle
        self.mod = int(mod) # Mod is the moderator who performed the request
        self.str_mod = str(mod) # Rhe moderator in string form for quicker and easier access
        self.channel = client.get_channel(bot_logs) # Bot log channel cached so we don't need to ask Discord
        self.guild = self.channel.guild # Alias to make guild sending easier
        self.force = force 

    async def _get_main_owner(self):
        """Internal function to get the main owner"""
        return await db.fetchval("SELECT owner FROM bot_owner WHERE bot_id = $1 AND main = true", self.bot_id) # Return main owner from database

    async def _give_roles(self, role, users):
        """Internal function to give a role to a list of users"""
        for user in users:
            try:
                member = self.guild.get_member(int(user))
                await member.add_roles(self.guild.get_role(role))
            except:
                pass

    async def claim_bot(self):
        check = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $2 AND state = $1", enums.BotState.pending, self.bot_id) # Before claiming, make sure it is pending and exists first
        if not check:
            return self.bot_not_found
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.under_review, self.bot_id) # Set it to under review in database
        claim_embed = discord.Embed(title="Bot Under Review", description = f"<@{self.bot_id}> is now under review by <@{self.mod}> and should be approved or denied soon!", color = self.good) # Create claim embed
        claim_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}") # Add link to bot page
        await bot_add_event(self.bot_id, enums.APIEvents.bot_claim, {"user": self.str_mod}) # Add the api event
        await self.channel.send(embed = claim_embed) # Send it to the channel
        try:
            owner = await self._get_main_owner()
            owner_dpy = self.guild.get_member(owner)
            await owner_dpy.send(embed = claim_embed)
        except:
            pass

    async def unclaim_bot(self):
        check = await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $2 AND state = $1", enums.BotState.under_review, self.bot_id) # Before claiming, make sure it is under review and exists first
        if not check:
            return self.bot_not_found
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.pending, self.bot_id) # Set it to pending in database
        unclaim_embed = discord.Embed(title="Bot No Longer Under Review", description = f"<@{self.bot_id}> is no longer under review by and should be approved or denied when another reviewer comes in! Don't worry, this is completely normal!", color = self.good) # Create unclaim embed
        unclaim_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}") # Add link to bot page
        await bot_add_event(self.bot_id, enums.APIEvents.bot_unclaim, {"user": self.str_mod}) # Add the api event
        await self.channel.send(embed = unclaim_embed) # Send it to the channel
        try:
            owner = await self._get_main_owner()
            owner_dpy = self.guild.get_member(owner)
            await owner_dpy.send(embed = unclaim_embed)
        except:
            pass

    async def approve_bot(self, feedback):
        owners = await db.fetch("SELECT owner, main FROM bot_owner WHERE bot_id = $1", self.bot_id)
        if not owners:
            return self.bot_not_found
        check = await db.fetchrow("SELECT state FROM bots WHERE bot_id = $1", self.bot_id)
        if check["state"] != enums.BotState.under_review and not self.force:
            return self.must_claim 
        await db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.approved, self.mod, self.bot_id)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_approve, {"user": self.str_mod, "reason": feedback})
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
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.pending, self.bot_id)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_unverify, {"user": self.str_mod, "reason": reason})
        unverify_embed = discord.Embed(title="Bot Unverified!", description = f"<@{self.bot_id}> by <@{owner}> has been unverified", color=self.bad)
        unverify_embed.add_field(name="Reason", value=reason)
        await self.channel.send(embed = unverify_embed)

    async def deny_bot(self, reason):
        owner = await self._get_main_owner()
        if owner is None:
            return self.bot_not_found
        check = await db.fetchrow("SELECT state FROM bots WHERE bot_id = $1", self.bot_id)
        if check["state"] != enums.BotState.under_review and not self.force:
            return self.must_claim
        await db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.denied, self.mod, self.bot_id)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_deny, {"user": self.str_mod, "reason": reason})
        deny_embed = discord.Embed(title="Bot Denied!", description = f"<@{self.bot_id}> by <@{owner}> has been denied", color=self.bad)
        deny_embed.add_field(name="Reason", value=reason)
        await self.channel.send(embed = deny_embed)
        try:
            member = self.guild.get_member(int(owner))
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
        await bot_add_event(self.bot_id, enums.APIEvents.bot_ban, {"user": self.str_mod, "reason": reason})

    async def requeue_bot(self, reason):
        embed = discord.Embed(title="Bot Requeued", description=f"<@{self.bot_id}> has been requeued (removed from the deny list)!", color=self.good)
        embed.add_field(name="Reason", value = reason)
        await self.channel.send(embed = embed)
        await db.execute("UPDATE bots SET state = 1 WHERE bot_id = $1", self.bot_id)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_requeue, {"user": self.str_mod, "reason": reason})

    async def unban_bot(self, reason):
        embed = discord.Embed(title="Bot Unbanned", description=f"<@{self.bot_id}> has been unbanned", color=self.good)
        embed.add_field(name="Reason", value = reason)
        await self.channel.send(embed = embed)
        await db.execute("UPDATE bots SET state = 0 WHERE bot_id = $1", self.bot_id)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_unban, {"user": self.str_mod, "reason": reason})

    async def certify_bot(self):
        owners = await db.fetch("SELECT owner FROM bot_owner WHERE bot_id = $1", self.bot_id)
        if not owners:
            return self.bot_not_found
        await db.execute("UPDATE bots SET state = 6 WHERE bot_id = $1", self.bot_id)
        certify_embed = discord.Embed(title = "Bot Certified", description = f"<@{self.mod}> certified the bot <@{self.bot_id}>", color = self.good)
        certify_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}")
        await self.channel.send(embed = certify_embed)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_certify, {"user": self.str_mod})
        await self._give_roles(certified_dev_role, [owner["owner"] for owner in owners])

    async def uncertify_bot(self, reason):
        owners = await db.fetch("SELECT owner FROM bot_owner WHERE bot_id = $1", self.bot_id)
        if not owners:
            return self.bot_not_found
        await db.execute("UPDATE bots SET state = 0 WHERE bot_id = $1", self.bot_id)
        uncertify_embed = discord.Embed(title = "Bot Uncertified", description = f"<@{self.mod}> uncertified the bot <@{self.bot_id}>", color = self.bad)
        embed.add_field(name="Reason", value = reason)
        uncertify_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}")
        await self.channel.send(embed = uncertify_embed)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_uncertify, {"user": self.str_mod, "reason": reason})

    async def transfer_bot(self, reason, new_owner):
        owner = await self._get_main_owner()
        if owner is None:
            return self.bot_not_found
        await db.execute("UPDATE bot_owner SET owner = $1 WHERE bot_id = $2 AND main = true", new_owner, self.bot_id) 
        # Remove bot developer role
        member = self.guild.get_member(owner)
        if member is not None:
            await member.remove_roles(self.guild.get_role(bot_dev_role))
        
        new_member = self.guild.get_member(new_owner)
        if new_member is not None:
            await new_member.add_roles(self.guild.get_role(bot_dev_role))

        embed = discord.Embed(title="Ownership Transfer", description = f"<@{self.mod}> has transferred ownership of the bot <@{self.bot_id}> from <@{owner}> to <@{new_owner}>", color=self.good)
        embed.add_field(name="Reason", value = reason)
        embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}")
        await self.channel.send(embed = embed)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_transfer, {"user": self.str_mod, "old_owner": str(owner), "new_owner": str(new_owner), "reason": reason})

    async def root_update(self, reason, old_state, new_state):
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", new_state, bot_id)
        embed = discord.Embed(title="Root State Update", description = f"<@{self.mod}> has changed the state of <@{self.bot_id}> from {old_state.__doc__} ({old_state}) to {new_state.__doc__} ({new_state})", color=self.good)
        await self.channel.send(embed = embed)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_root_update, {"user": self.str_mod, "old_state": old_state, "new_state": new_state, "reason": reason})

    async def reset_votes_all(self, reason):
        """This function supports recursion (bot id of 0)"""
        bots = await db.fetch("SELECT bot_id, votes FROM bots")
        epoch = time.time()
        for bot in bots:
            await db.execute("INSERT INTO bot_stats_votes_pm (bot_id, epoch, votes) VALUES ($1, $2, $3)", bot["bot_id"], epoch, bot["votes"])
        await db.execute("UPDATE bots SET votes = 0")
        await db.execute("UPDATE users SET vote_epoch = NULL")
        embed = discord.Embed(title="Reset Votes", description = f"<@{self.mod}> has reset all votes on Fates List")
        embed.add_field(name="Reason", value = reason)
        await self.channel.send(embed = embed)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_vote_reset_all, {"user": self.str_mod, "reason": reason})

class ServerActions():
    class GeneratedObject():
        """Instead of crappily changing self, just use a generated object which is at least cleaner"""
        tags = []

    def __init__(self, guild):
        self.__dict__.update(guild) # Add kwargs to class
        self.generated = self.GeneratedObject() # To keep things clean, make sure we always put changed properties in generated

    def gen_rabbit_dict(self):
        rmq_dict = self.__dict__.copy()
        del rmq_dict["generated"]
        rmq_dict["tags"] = self.generated.tags
        return rmq_dict

    async def base_check(self) -> Optional[str]:
        self.generated.tags = []
        for tag in self.tags:
            if tag not in self.generated.tags:
                self.generated.tags.append(tag.lower().replace(" ", "_"))
        if len(self.generated.tags) < 3:
            return "You must select at least three tags for your server", 1
        if len(self.description) > 101 or len(self.description) < 20:
            return "Your short description must be between 20 and 101 characters long", 2
        if len(self.long_description) < 50:
            return "Your long description must be at least 50 characters long", 3

        check = await vanity_check(self.guild_id, self.vanity) # Check if vanity is already being used or is reserved
        if check:
            return "Your custom vanity URL is already in use or is reserved", 4

    async def add_check(self):
        """Perform extended checks for adding servers"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check # Base check erroring means return base check without continuing as string return means error
        if (await db.fetchrow("SELECT guild_id FROM servers WHERE guild_id = $1", self.guild_id)) is not None:
            return "This server already exists on Fates List", 5 # Dont add servers which already exist

    async def add_server(self):
        """Add a server"""
        check = await self.add_check() # Perform add bot checks
        if check is not None:
            return check # Returning a strung and not None means error to be returned to consumer

        await add_rmq_task("server_add_queue", self.gen_rabbit_dict()) # Add to add bot RabbitMQ
