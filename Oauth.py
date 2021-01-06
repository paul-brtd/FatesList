import aiohttp

class Oauth(object):
    client_id = "791398044037152778"
    client_secret = "dcZgnBbjwhSSJawUXx4aX5MYS9xGO3oA"
    scope = "identify%20guilds.join"
    redirect_uri = "https://3bbcb246b7da.ngrok.io/login/confirm"
    discord_login_url = "https://discord.com/api/oauth2/authorize?client_id=791398044037152778&redirect_uri=https%3A%2F%2F3bbcb246b7da.ngrok.io%2Flogin%2Fconfirm&response_type=code&scope=identify%20guilds.join"
    discord_token_url = "https://discord.com/api/oauth2/token"
    discord_api_url = "https://discordapp.com/api"
    @staticmethod
    async def get_access_token(code):
        payload = {
            "client_id": Oauth.client_id,
            "client_secret": Oauth.client_secret,
            "grant_type": "authorization_code",
            "code":code,
            "redirect_uri":Oauth.redirect_uri,
            "scope":Oauth.scope
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.post(Oauth.discord_token_url, data=payload, headers=headers) as response:
                json = await response.json()
        return json.get("access_token")

    @staticmethod
    async def get_user_json(access_token):
        url = Oauth.discord_api_url+"/users/@me"

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
        return {"id":id, "name":name, "dash":dash, "avatar":avatar}
    @staticmethod
    async def join_user(access_token,userid):
        guild_id="789934742128558080"
        url = Oauth.discord_api_url+f"/guilds/{guild_id}/members/{userid}"

        headers = {
            "Authorization": f"Bot NzkxMzk4MDQ0MDM3MTUyNzc4.X-Ok3Q.6uc4aIzt_HW2ZsW9uNe5C9uAXC8"
        }
        async with aiohttp.ClientSession() as sess:
            async with sess.put(url, headers=headers,json={"access_token":access_token}) as response:
                pass


    @staticmethod
    async def check(access_token):
      url = Oauth.discord_api_url+"/users/@me/guilds"
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

