import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

bot.run(os.getenv("MTUwODAyOTEzOTM0MzUwNzU0OA.GYCN6m.Q0LXWw_t9HqlcS0-G_kxd3pXMW48weDenZpW_I"))
