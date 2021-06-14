import aiohttp
from aiohttp_requests import requests
from config import *
from typing import Union, Optional, List
import secrets
import string
import time

def get_token(length: str) -> str:
    secure_str = "".join((secrets.choice(string.ascii_letters + string.digits) for i in range(length)))
    return secure_str


class Oauth():
    def __init__(self, oc: OauthConfig):
        self.client_id = oc.client_id
        self.client_secret = oc.client_secret
        self.redirect_uri = oc.redirect_uri
        self.discord_login_url = "https://discord.com/api/oauth2/authorize?client_id=" + self.client_id + "&redirect_uri=" + self.redirect_uri
        self.discord_token_url = "https://discord.com/api/oauth2/token"
        self.discord_api_url = "https://discord.com/api"
    
    def get_scopes(self, scopes_lst: list) -> str:
        return "%20".join(scopes_lst)

    def get_discord_oauth(self, scopes: Union[str, list], redirect: str):
        if type(scopes) == list:
            scopes = self.get_scopes(scopes)
        state = "|".join((scopes, redirect))
        return {"state": scopes, "url": f"{self.discord_login_url}&state={state}&response_type=code&scope={scopes}"}

    async def get_access_token(self, code, scope, redirect_uri: str = None) -> dict:
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri if not redirect_uri else redirect_uri,
            "scope": scope
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        res = await requests.post(self.discord_token_url, data=payload, headers=headers)
        json = await res.json()
        return {"access_token": json.get("access_token"), "refresh_token": json.get("refresh_token"), "expires_in": json.get("expires_in"), "current_time": time.time(), "real": json}

    async def access_token_check(self, scope: str, access_token_dict: dict) -> str:
        if float(access_token_dict["current_time"]) + float(access_token_dict["expires_in"]) > time.time():
            logger.debug("Using old access token without making any changes")
            return access_token_dict
        # Refresh
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": access_token_dict["refresh_token"],
            "redirect_uri": self.redirect_uri,
            "scope": scope
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        res = await requests.post(self.discord_token_url, data=payload, headers=headers)
        json = await res.json()
        logger.debug("Got json of {json}")
        return {"access_token": json.get("access_token"), "refresh_token": json.get("refresh_token"), "expires_in": json.get("expires_in"), "current_time": time.time()}

    async def get_user_json(self, access_token):
        url = self.discord_api_url + "/users/@me"

        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        res = await requests.get(url, headers=headers)
        user_json = await res.json()
        id = user_json.get("id")
        name = user_json.get("username")
        dash = user_json.get("discriminator")
        avatar = user_json.get("avatar")
        return user_json

    async def get_guilds(self, access_token: str, permissions: Optional[hex] = None):
        url = self.discord_api_url + "/users/@me/guilds"
        headers = {'Content-Type': 'application/x-www-form-urlencoded', "Authorization": "Bearer " + access_token}
        res = await requests.get(url, headers=headers)
        guild_json = await res.json()
        try:
            guilds = []
            for guild in guild_json:
                if permissions is None:
                    guilds.append(str(guild["id"]))
                else:
                    flag = False
                    for perm in permissions:
                        if flag:
                            continue
                        elif (guild["permissions"] & perm) == perm:
                            flag = True
                        else:
                            pass
                    if flag:
                        guilds.append(str(guild["id"]))
        except:
            guilds = []
        logger.debug(f"Got guilds {guilds}")
        return guilds

    async def join_user(self, access_token, user_id):
        url = self.discord_api_url+f"/guilds/{main_server}/members/{user_id}"

        headers = {
            "Authorization": f"Bot {TOKEN_MAIN}"
        }
        rc = await requests.put(url, headers=headers,json={"access_token":access_token})

