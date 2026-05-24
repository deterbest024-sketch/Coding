from discord.ext import commands

class Sticky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(Sticky(bot))
