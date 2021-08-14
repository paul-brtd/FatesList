from .cache import *
from .events import *
from .helpers import *
from .imports import *
from .permissions import *

class BotActions():
    def __init__(self, bot):
        self.__dict__.update(bot) # Add all kwargs to class
        logger.debug("Request Acknowledged")

    async def base_check(self) -> Optional[str]:
        """Perform basic checks for adding/editting bots. A check returning None means success, otherwise error should be returned to client"""
        if len(self.prefix) > 9:
            return "Prefix must be less than 9 characters long"

        if not self.vanity:
            return "You must have a vanity for your bot. This can be your username. You can prefix it with _ (underscore) if you don't want the extra growth from it. For example _mewbot would disable the mewbot vanity"

        if self.tags == "":
            return "You must select tags for your bot" #Check tags

        if self.invite:
            if self.invite.startswith("P:"): # Check if perm auto is specified
                perm_num = self.invite.split(":")[1].split("|")[0]
                try:
                    perm_num = int(perm_num)
                except ValueError:
                    return "Invalid Bot Invite: Your permission number must be a integer", 4 # Invalid Invite
            elif not self.invite.startswith("https://discord.com") or "oauth" not in self.invite:
                return "Invalid Bot Invite: Your bot invite must be in the format of https://discord.com/api/oauth2... or https://discord.com/oauth2..." # Invalid Invite

        if len(self.description) > 110:
            return "Your short description must be shorter than 110 characters" # Short Description Check

        if len(self.long_description) < 300:
            return "Your long description must be at least 300 characters long"

        bot_obj = await get_bot(self.bot_id) # Check if bot exists

        if not bot_obj:
            return "According to Discord's API and our cache, your bot does not exist. Please try again after 2 hours."
        
        for tag in self.tags:
            if tag not in TAGS:
                return "One of your tags doesn't exist internally. Please check your tags again" # Check tags internally

        if not self.tags:
            return "You must select tags for your bot" # No tags found

        imgres = None
        
        for banner_key in ("banner_page", "banner_card"):
            banner = self.__dict__[banner_key]
            banner_name = banner_key.replace("_", " ")
            if banner:
                banner = ireplacem((("(", ""), (")", ""), ("http://", "https://")), banner)
                if not banner.startswith("https://"):
                    return f"Your {banner_name} does not use https://. Please change it" # Check banner and ensure HTTPS
                try:
                    async with aiohttp.ClientSession() as sess:
                        async with sess.head(banner, timeout=30) as res:
                            if res.status != 200:
                                # Banner URL does not support head, try get
                                async with sess.get(self.banner, timeout=30) as res_fallback:
                                    if res_fallback.status != 200:
                                        return f"Could not download {banner_name} using either GET or HEAD! Is your URL correct"
                                    imgres = res_fallback
                            else:
                                imgres = res
                except Exception as exc:
                    return f"Something happened when trying to get the url for {banner_name}: {exc}"
            
                ct = imgres.headers.get("Content-Type", "").replace(" ", "")
                if ct.split("/")[0] != "image":
                    return f"A banner has an issue: {banner_name} is not an image. Please make sure it is setting the proper Content-Type. Got status code {imgres.status} and content type of {ct}."

        if self.donate and not self.donate.startswith(("https://patreon.com", "https://paypal.me", "https://www.buymeacoffee.com")):
            return "Only Patreon, PayPal.me and Buymeacoffee are supported for donations at this time} You can request for more on our support server!" 
        
        for eo in self.extra_owners:
            tmp = await get_user(eo)
            if not tmp:
                return "One of your extra owners doesn't exist"

        if self.github and not self.github.startswith("https://www.github.com"): # Check github for github.com if not empty string
            return "Your github link must start with https://www.github.com"

        if self.privacy_policy:
            self.privacy_policy = self.privacy_policy.replace("http://", "https://") # Force https on privacy policy
            if not self.privacy_policy.startswith("https://"): # Make sure we actually have a HTTPS privacy policy
                return "Your privacy policy must be a proper URL starting with https://. URLs which start with http:// will be automatically converted to HTTPS while adding"
        check = await vanity_check(self.bot_id, self.vanity) # Check if vanity is already being used or is reserved
        if check:
            return "Your custom vanity URL is already in use or is reserved"
        if self.webhook_secret and len(self.webhook_secret) < 8:
            return "Your webhook secret must be at least 8 characters long"

    async def edit_check(self):
        """Perform extended checks for editting bots"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check
        
        lock = await db.fetchval("SELECT lock FROM bots WHERE bot_id = $1", int(self.bot_id))
        lock = enums.BotLock(lock)
        if lock != enums.BotLock.unlocked:
            return f"This bot cannot be edited as it has been locked with a code of {int(lock)}: ({lock.__doc__}). If this bot is not staff staff locked, join the support server and run +unlock <BOT> to unlock it."

        check = await is_bot_admin(int(self.bot_id), int(self.user_id)) # Check for owner
        if not check:
            return "You aren't the owner of this bot."

        check = await get_user(self.user_id)
        if check is None: # Check if owner exists
            return "You do not exist on the Discord API. Please wait for a few hours and try again"

    async def add_check(self):
        """Perform extended checks for adding bots"""
        check = await self.base_check() # Initial base checks
        if check is not None:
            return check # Base check erroring means return base check without continuing as string return means error

        if (await db.fetchrow("SELECT bot_id FROM bots WHERE bot_id = $1", self.bot_id)) is not None:
            return "This bot already exists on Fates List" # Dont add bots which already exist

    async def add_bot(self):
        """Add a bot"""
        check = await self.add_check() # Perform add bot checks
        if check:
            return check # Returning a string and not None means error to be returned to consumer

        await add_rmq_task("bot_add_queue", self.__dict__) # Add to add bot RabbitMQ

    async def edit_bot(self):
        """Edit a bot"""
        check = await self.edit_check() # Perform edit bot checks
        if check:
            return check

        await add_rmq_task("bot_edit_queue", self.__dict__) # Add to edit bot RabbitMQ
