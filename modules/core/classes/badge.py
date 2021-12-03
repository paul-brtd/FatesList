from typing import List, Optional

import orjson
from discord import Member
from pydantic import BaseModel

from config import special_badges, staff_roles
from config._logger import logger
from modules.core.permissions import is_staff
from modules.models import enums


class Badge(BaseModel):
    """Handle badges"""

    id: str
    name: str
    description: str
    image: str
    staff: bool | None = False
    cert_dev: bool | None = False
    bot_dev: bool | None = False
    support_server_member: bool | None = False
    everyone: bool | None = False

    @staticmethod
    async def from_user(
        id,
        roles,
        badges: list[str] | None = [],
        bot_dev: bool | None = False,
        cert_dev: bool | None = False,
    ):
        """Make badges from a user given the member, badges and bots"""
        user_flags = {}

        user_flags["cert_dev"] = cert_dev
        user_flags["bot_dev"] = bot_dev
        user_flags["everyone"] = True

        badges = badges if badges else []

        # A discord.Member is part of the support server
        user_flags["staff"] = (await is_staff(staff_roles, id, 2))[0]
        if [role for role in roles if role]:
            user_flags["discord_member"] = True

        all_badges = []
        for badge in badges:  # Add in user created badges from blist
            try:
                badge_data = orjson.loads(badge)
            except:
                logger.warning("Failed to open user badge")
                continue

            all_badges.append(badge_data)

        # Special staff + certified badges (if present)
        for badge in special_badges:
            # Check if user is allowed to get badge and if so, give it
            check = len([key for key in badge["req"] if user_flags.get(key)])
            if check:
                all_badges.append(badge)

        return all_badges
