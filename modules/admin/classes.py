class BotListAdmin():
    """Class to control and handle bots"""

    # Some messages
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

    async def _get_owners(self):
        return await db.fetch("SELECT owner FROM bot_owner WHERE bot_id = $1", self.bot_id)

    async def _give_roles(self, role):
        """Internal function to give a role to all owners of a bot"""
        owners_raw = await self._get_owners()
        owners = [owner["owner"] for owner in owners_raw]
        for user in owners:
            try:
                member = self.guild.get_member(int(user))
                await member.add_roles(self.guild.get_role(role))
            except Exception:
                pass

    async def claim_bot(self):
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.under_review, self.bot_id) # Set it to under review in database
        claim_embed = discord.Embed(title="Bot Under Review", description = f"<@{self.bot_id}> is now under review by <@{self.mod}> and should be approved or denied soon!", color = self.good) # Create claim embed
        claim_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}") # Add link to bot page
        await bot_add_event(self.bot_id, enums.APIEvents.bot_claim, {"user": self.str_mod}) # Add the api event
        await self.channel.send(embed = claim_embed) # Send it to the channel
        try:
            owner = await self._get_main_owner()
            owner_dpy = self.guild.get_member(owner)
            await owner_dpy.send(embed = claim_embed)
        except Exception:
            pass

    async def unclaim_bot(self):
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.pending, self.bot_id) # Set it to pending in database
        unclaim_embed = discord.Embed(title="Bot No Longer Under Review", description = f"<@{self.bot_id}> is no longer under review by and should be approved or denied when another reviewer comes in! Don't worry, this is completely normal!", color = self.good) # Create unclaim embed
        unclaim_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}") # Add link to bot page
        await bot_add_event(self.bot_id, enums.APIEvents.bot_unclaim, {"user": self.str_mod}) # Add the api event
        await self.channel.send(embed = unclaim_embed) # Send it to the channel
        try:
            owner = await self._get_main_owner()
            owner_dpy = self.guild.get_member(owner)
            await owner_dpy.send(embed = unclaim_embed)
        except Exception:
            pass

    async def approve_bot(self, feedback):
        await db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.approved, self.mod, self.bot_id)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_approve, {"user": self.str_mod, "reason": feedback})
        owner = await self._get_main_owner()
        approve_embed = discord.Embed(title="Bot Approved!", description = f"<@{self.bot_id}> by <@{owner}> has been approved", color = self.good)
        approve_embed.add_field(name="Feedback", value=feedback)
        approve_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}")
        await self._give_roles(bot_dev_role)
        try:
            member = self.guild.get_member(int(owner))
            if member is not None:
                await member.send(embed = approve_embed)
        except Exception:
            pass
        await self.channel.send(embed = approve_embed)

    async def unverify_bot(self, reason):
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", enums.BotState.pending, self.bot_id)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_unverify, {"user": self.str_mod, "reason": reason})
        unverify_embed = discord.Embed(title="Bot Unverified!", description = f"<@{self.bot_id}> by <@{owner}> has been unverified", color=self.bad)
        unverify_embed.add_field(name="Reason", value=reason)
        await self.channel.send(embed = unverify_embed)

    async def deny_bot(self, reason):
        owner = await self._get_main_owner()
        await db.execute("UPDATE bots SET state = $1, verifier = $2 WHERE bot_id = $3", enums.BotState.denied, self.mod, self.bot_id)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_deny, {"user": self.str_mod, "reason": reason})
        deny_embed = discord.Embed(title="Bot Denied!", description = f"<@{self.bot_id}> by <@{owner}> has been denied", color=self.bad)
        deny_embed.add_field(name="Reason", value=reason)
        await self.channel.send(embed = deny_embed)
        try:
            member = self.guild.get_member(int(owner))
            if member is not None:
                await member.send(embed = deny_embed)
        except Exception:
            pass

    async def ban_bot(self, reason):
        ban_embed = discord.Embed(title="Bot Banned", description=f"<@{self.bot_id}> has been banned", color=self.bad)
        ban_embed.add_field(name="Reason", value = reason)
        await self.channel.send(embed = ban_embed)
        try:
            await self.guild.kick(self.guild.get_member(self.bot_id))
        except Exception:
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
        await db.execute("UPDATE bots SET state = 6 WHERE bot_id = $1", self.bot_id)
        certify_embed = discord.Embed(title = "Bot Certified", description = f"<@{self.mod}> certified the bot <@{self.bot_id}>", color = self.good)
        certify_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}")
        await self.channel.send(embed = certify_embed)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_certify, {"user": self.str_mod})
        await self._give_roles(certified_dev_role)

    async def uncertify_bot(self, reason):
        await db.execute("UPDATE bots SET state = 0 WHERE bot_id = $1", self.bot_id)
        uncertify_embed = discord.Embed(title = "Bot Uncertified", description = f"<@{self.mod}> uncertified the bot <@{self.bot_id}>", color = self.bad)
        embed.add_field(name="Reason", value = reason)
        uncertify_embed.add_field(name="Link", value=f"https://fateslist.xyz/bot/{self.bot_id}")
        await self.channel.send(embed = uncertify_embed)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_uncertify, {"user": self.str_mod, "reason": reason})

    async def transfer_bot(self, reason, new_owner):
        owner = await self._get_main_owner()
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

    async def delete_bot(self, reason):
        lock = await db.fetchval("SELECT lock FROM bots WHERE bot_id = $1", self.bot_id)
        lock = enums.BotLock(lock)
        if lock != enums.BotLock.unlocked:
            return api_error(
                f"This bot cannot be deleted as it has been locked with a code of {int(lock)}: ({lock.__doc__}). If this bot is not staff locked, join the support server and run +unlock <BOT> to unlock"
            )
        await add_rmq_task("bot_delete_queue", {"user_id": self.mod, "bot_id": self.bot_id})
        embed = discord.Embed(title="Staff Delete", description = f"<@{self.mod}> has has deleted <@{self.bot_id}>", color=self.bad)
        embed.add_field(name="Reason", value = reason)
        await self.channel.send(embed = embed)

    async def root_update(self, reason, old_state, new_state):
        await db.execute("UPDATE bots SET state = $1 WHERE bot_id = $2", new_state, self.bot_id)
        embed = discord.Embed(title="Root State Update", description = f"<@{self.mod}> has changed the state of <@{self.bot_id}> from {old_state.__doc__} ({old_state}) to {new_state.__doc__} ({new_state})", color=self.good)
        await self.channel.send(embed = embed)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_root_update, {"user": self.str_mod, "old_state": old_state, "new_state": new_state, "reason": reason})

    async def reset_votes(self, reason):
        """This function supports recursion (bot id of 0)"""
        if self.bot_id == 0: # Recursive, reset all votes
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
        else:
            await db.execute("UPDATE bots set votes = 0 WHERE bot_id = $1", self.bot_id)
            embed = discord.Embed(title="Reset Votes", description = f"<@{self.mod}> has reset votes for <@{self.bot_id}>")
            embed.add_field(name="Reason", value = reason)
            await self.channel.send(embed = embed)
            await bot_add_event(self.bot_id, enums.APIEvents.bot_vote_reset, {"user": self.str_mod, "reason": reason})

    async def lock_bot(self, lock, reason = "This bot was locked by staff, its owner or with its owners permission to protect against malicious or accidental editing!"):
        await db.execute("UPDATE bots SET lock = $1 WHERE bot_id = $2", lock, self.bot_id)
        embed = discord.Embed(title="Lock Bot", description = f"<@{self.mod}> has locked the bot <@{self.bot_id}>")
        embed.add_field(name="Reason", value = reason)
        await self.channel.send(embed = embed)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_lock, {"user": self.str_mod, "reason": reason, "lock": lock})

    async def unlock_bot(self, reason = "This bot was unlocked by staff, its owner or with its owners permission to make changes to the bot!"):
        await db.execute("UPDATE bots SET lock = $1 WHERE bot_id = $2", enums.BotLock.unlocked, self.bot_id)
        embed = discord.Embed(title="Unlock Bot", description = f"<@{self.mod}> has unlocked the bot <@{self.bot_id}>")
        embed.add_field(name="Reason", value = reason)
        await self.channel.send(embed = embed)
        await bot_add_event(self.bot_id, enums.APIEvents.bot_unlock, {"user": self.str_mod, "reason": reason})
