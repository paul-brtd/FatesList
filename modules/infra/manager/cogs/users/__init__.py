from .users import Users

def setup(bot):
    bot.add_cog(Users(bot))
