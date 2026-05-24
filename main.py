import discord
from discord.ext import commands
import asyncio
import os
import threading
from utils.config import load_config

COGS = [
    "cogs.help",
    "cogs.setup",
    "cogs.moderation",
    "cogs.starboard",
    "cogs.sticky",
    "cogs.games",
    "cogs.tickets",
]

def get_prefix(bot: commands.Bot, message: discord.Message) -> str:
    return load_config().get("prefix", "!")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")

def start_web():
    from web.app import run
    run()

async def main():
    web_thread = threading.Thread(target=start_web, daemon=True)
    web_thread.start()
    print("Web dashboard started on port 5000")

    async with bot:
        for cog in COGS:
            await bot.load_extension(cog)
        token = os.environ.get("DISCORD_TOKEN")
        if not token:
            raise ValueError("DISCORD_TOKEN is not set. Add it as a secret.")
        await bot.start(token)

asyncio.run(main())
