class BaseUser(BaseModel):
    """
    Represents a base user class on Fates List.
    """
    id: str
    username: str
    avatar: str
    disc: str
    status: enums.Status
    bot: bool

    def __str__(self):
        """
        :return: Returns the username
        :rtype: str
        """
        return self.username

    def get_status(self):
        """
        :return: Returns a status object for the bot
        :rtype: Status
        """
        return Status(status = self.status)
