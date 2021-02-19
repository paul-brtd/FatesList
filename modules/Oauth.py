import aiohttp
from aiohttp_requests import requests
from config import *
class Oauth():
    def __init__(self):
        self.client_id = OauthConfig.client_id
        self.client_secret = OauthConfig.client_secret
        self.scope = "%20".join(OauthConfig.scope)
        self.scope_js = "%20".join(OauthConfig.scope + ["guilds.join"])
        self.redirect_uri = OauthConfig.redirect_uri
        self.discord_login_url = "https://discord.com/api/oauth2/authorize?client_id=" + self.client_id + "&redirect_uri=" + self.redirect_uri + "&response_type=code&scope="
        self.discord_token_url = "https://discord.com/api/oauth2/token"
        self.discord_api_url = "https://discordapp.com/api"
    
    async def get_access_token(self, code):
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        res = await requests.post(self.discord_token_url, data=payload, headers=headers)
        json = await res.json()
        return json.get("access_token")

    async def get_user_json(self, access_token):
        url = self.discord_api_url+"/users/@me"

        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        res = await requests.get(url, headers=headers)
        user_json = await res.json()
        id = user_json.get("id")
        name = user_json.get("username")
        dash = user_json.get("discriminator")
        avatar = user_json.get("avatar")
        return {"id":id, "name":name, "dash":dash, "avatar":avatar, "real": user_json}
    
    async def check(self, access_token):
      url = self.discord_api_url+"/users/@me/guilds"
      headers = {'Content-Type': 'application/x-www-form-urlencoded',
                          "Authorization": "Bearer " + access_token}
      res = await requests.get(url, headers=headers)
      guild_json = await res.json()

      try:
        guilds = []
        for guild in guild_json:
            if int(guild["id"]) == 758290404910301184:
                guilds = True
      except:
        guilds = None
      return guilds

    async def join_user(self, access_token, userid):
        guild_id= str(reviewing_server)
        url = self.discord_api_url+f"/guilds/{guild_id}/members/{userid}"

        headers = {
            "Authorization": f"Bot {TOKEN}"
        }
        rc = await requests.put(url, headers=headers,json={"access_token":access_token})
        print(rc)

