import requests

class Oauth(object):
    client_id = "758299848821964830"
    client_secret = "875UZiegr0NK70xEPL-09Z4kUvIiDDrs"
    scope = "guilds%20identify"
    redirect_uri = "https://distop.xyz/login/confirm"
    discord_login_url = "https://discord.com/api/oauth2/authorize?client_id=758299848821964830&redirect_uri=https%3A%2F%2Fdistop.xyz%2Flogin%2Fconfirm&response_type=code&scope=guilds%20identify&prompt=none"
    discord_token_url = "https://discord.com/api/oauth2/token"
    discord_api_url = "https://discordapp.com/api"
    @staticmethod
    def get_access_token(code):
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
        access_token = requests.post(url=Oauth.discord_token_url, data=payload,headers=headers)
        json = access_token.json()
        return json.get("access_token")

    @staticmethod
    def get_user_json(access_token):
        url = Oauth.discord_api_url+"/users/@me"

        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        user_json = requests.get(url=url, headers=headers)
        user_json = user_json.json()
        id = user_json.get("id")
        name = user_json.get("username")
        dash = user_json.get("discriminator")
        avatar = user_json.get("avatar")
        return {"id":id, "name":name, "dash":"", "avatar":avatar}

    @staticmethod
    def get_user_json(access_token):
        url = Oauth.discord_api_url+"/users/@me"

        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        user_json = requests.get(url=url, headers=headers)
        user_json = user_json.json()
        id = user_json.get("id")
        name = user_json.get("username")
        dash = user_json.get("discriminator")
        avatar = user_json.get("avatar")
        return {"id":id, "name":name, "dash":dash, "avatar":avatar}
    @staticmethod
    def check(access_token):
      url = Oauth.discord_api_url+"/users/@me/guilds"
      headers = {'Content-Type': 'application/x-www-form-urlencoded',
                          "Authorization": "Bearer " + access_token}
      r = requests.get(url,headers=headers)
      try:
        guilds = []
        for server in r.json():
            if int(server["id"]) == 758290404910301184:
                guilds = True
      except:
        guilds = None
      return guilds
    @staticmethod
    def check_mod(access_token):
      url = Oauth.discord_api_url+"/users/@me/guilds"
      headers = {'Content-Type': 'application/x-www-form-urlencoded',
                          "Authorization": "Bearer " + access_token}
      r = requests.get(url,headers=headers)
      try:
        guilds = []
        for server in r.json():
            if int(server["id"]) == 758290401915830304:
                guilds = True
      except:
        guilds = None
      return guilds
