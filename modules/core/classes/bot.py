from .base import DiscordUser

class Bot(DiscordUser):
    async def fetch(self):
        """Fetch a user object from our cache"""
        return await get_bot(self.id)
    
    async def invite_url(self):
        """Fetch the discord invite URL without any side effects"""
        invite = await self.db.fetchval("SELECT invite FROM bots WHERE bot_id = $1", self.id)
        
        if not invite or invite.startswith("P:"):
            perm = invite.split(":")[1].split("|")[0] if invite and invite.startswith("P:") else 0
            return f"https://discord.com/api/oauth2/authorize?client_id={self.id}&permissions={perm}&scope=bot%20applications.commands"
        
        return bot["invite"]
    
    async def invite(self, user_id: Optional[int] = None):
        """Invites a user to a bot updating invite amount"""
        await self.db.execute("UPDATE bots SET invite_amount = invite_amount + 1 WHERE bot_id = $2", self.id)
        await add_ws_event(self.id, {"m": {"e": enums.APIEvents.bot_invite}, "ctx": {"user": str(user_id)}})
        return await self.invite_url()
