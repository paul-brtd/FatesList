import aiohttp


class OauthConfig:
    client_id = "798951566634778641"
    client_secret = "lGXEWjGcuoom0KCCkPjFg6nPFvudwSTd"
    scope = ["identify", "guilds.join"]
    redirect_uri = "https://fateslist.xyz/login/confirm"

class Oauth():
    def __init__(self):
        self.client_id = OauthConfig.client_id
        self.client_secret = OauthConfig.client_secret
        self.scope = "%20".join(OauthConfig.scope)
        self.redirect_uri = OauthConfig.redirect_uri
        self.discord_login_url = "https://discord.com/api/oauth2/authorize?client_id=" + self.client_id + "&redirect_uri=" + self.redirect_uri + "&response_type=code&scope=" + self.scope
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
        async with aiohttp.ClientSession() as sess:
            async with sess.post(self.discord_token_url, data=payload, headers=headers) as response:
                json = await response.json()
        return json.get("access_token")

    async def get_user_json(self, access_token):
        url = self.discord_api_url+"/users/@me"

        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.get(url, headers=headers) as response:
                user_json = await response.json()
        id = user_json.get("id")
        name = user_json.get("username")
        dash = user_json.get("discriminator")
        avatar = user_json.get("avatar")
        return {"id":id, "name":name, "dash":dash, "avatar":avatar, "real": user_json}
    
    async def check(self, access_token):
      url = self.discord_api_url+"/users/@me/guilds"
      headers = {'Content-Type': 'application/x-www-form-urlencoded',
                          "Authorization": "Bearer " + access_token}
      async with aiohttp.ClientSession() as sess:
          async with sess.get(url, headers=headers) as response:
              r = await response.json()

      try:
        guilds = []
        for server in r:
            if int(server["id"]) == 758290404910301184:
                guilds = True
      except:
        guilds = None
      return guilds

