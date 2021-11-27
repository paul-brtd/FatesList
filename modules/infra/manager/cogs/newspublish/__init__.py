from .newspublish import NewsPublish

def setup(bot):
    bot.add_cog(NewsPublish(bot))
