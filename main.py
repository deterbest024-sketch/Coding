import os
import discord
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
import threading

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Database setup
DB_FILE = "moderation.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS moderation_logs (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        user_name TEXT,
        action TEXT,
        reason TEXT,
        moderator_id INTEGER,
        moderator_name TEXT,
        timestamp TEXT,
        guild_id INTEGER
    )''')
    conn.commit()
    conn.close()

def log_action(user_id, user_name, action, reason, moderator_id, moderator_name, guild_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''INSERT INTO moderation_logs 
                 (user_id, user_name, action, reason, moderator_id, moderator_name, timestamp, guild_id)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (user_id, user_name, action, reason, moderator_id, moderator_name, datetime.now().isoformat(), guild_id))
    conn.commit()
    conn.close()

def get_logs(guild_id=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if guild_id:
        c.execute('SELECT * FROM moderation_logs WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 100', (guild_id,))
    else:
        c.execute('SELECT * FROM moderation_logs ORDER BY timestamp DESC LIMIT 100')
    logs = c.fetchall()
    conn.close()
    return logs

# Flask dashboard
app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/logs')
def api_logs():
    logs = get_logs()
    return jsonify([{
        'id': log[0],
        'user_id': log[1],
        'user_name': log[2],
        'action': log[3],
        'reason': log[4],
        'moderator_name': log[6],
        'timestamp': log[7]
    } for log in logs])

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=False)

# Discord bot commands
@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason="No reason provided"):
    try:
        await member.kick(reason=reason)
        log_action(member.id, str(member), "KICK", reason, ctx.author.id, str(ctx.author), ctx.guild.id)
        await ctx.send(f"✅ {member} has been kicked. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to kick this member.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason="No reason provided"):
    try:
        await member.ban(reason=reason)
        log_action(member.id, str(member), "BAN", reason, ctx.author.id, str(ctx.author), ctx.guild.id)
        await ctx.send(f"✅ {member} has been banned. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban this member.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member, duration: int, *, reason="No reason provided"):
    try:
        await member.timeout(timedelta(seconds=duration), reason=reason)
        log_action(member.id, str(member), "MUTE", f"{reason} (Duration: {duration}s)", ctx.author.id, str(ctx.author), ctx.guild.id)
        await ctx.send(f"✅ {member} has been muted for {duration} seconds. Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to mute this member.")

@bot.command()
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member):
    try:
        await member.timeout(None)
        log_action(member.id, str(member), "UNMUTE", "Unmuted", ctx.author.id, str(ctx.author), ctx.guild.id)
        await ctx.send(f"✅ {member} has been unmuted.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to unmute this member.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def warn(ctx, member: discord.Member, *, reason="No reason provided"):
    log_action(member.id, str(member), "WARN", reason, ctx.author.id, str(ctx.author), ctx.guild.id)
    await ctx.send(f"⚠️ {member} has been warned. Reason: {reason}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def modlogs(ctx, member: discord.Member = None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    if member:
        c.execute('SELECT action, reason, timestamp FROM moderation_logs WHERE user_id = ? AND guild_id = ? ORDER BY timestamp DESC LIMIT 10',
                  (member.id, ctx.guild.id))
    else:
        c.execute('SELECT user_name, action, reason, timestamp FROM moderation_logs WHERE guild_id = ? ORDER BY timestamp DESC LIMIT 10',
                  (ctx.guild.id,))
    logs = c.fetchall()
    conn.close()
    
    if not logs:
        await ctx.send("No moderation logs found.")
        return
    
    embed = discord.Embed(title="Moderation Logs", color=discord.Color.red())
    for log in logs:
        if member:
            embed.add_field(name=f"{log[0]} - {log[2]}", value=log[1], inline=False)
        else:
            embed.add_field(name=f"{log[0]} - {log[1]}", value=log[2], inline=False)
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: {error.param}")
    else:
        await ctx.send(f"❌ Error: {error}")

init_db()

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

bot.run(os.getenv("DISCORD_TOKEN"))
