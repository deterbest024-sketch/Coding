import os
import discord
from discord.ext import commands
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
import threading
import json

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Database setup
DB_FILE = "moderation.db"
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_guild_config(guild_id):
    config = load_config()
    return config.get(str(guild_id), {
        "prefix": "!",
        "logs_channel": None,
        "admin_role": None
    })

def set_guild_config(guild_id, key, value):
    config = load_config()
    guild_id_str = str(guild_id)
    if guild_id_str not in config:
        config[guild_id_str] = {
            "prefix": "!",
            "logs_channel": None,
            "admin_role": None
        }
    config[guild_id_str][key] = value
    save_config(config)

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
async def help(ctx):
    embed = discord.Embed(
        title="📚 Bot Commands",
        description="Here are all available commands:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎮 General",
        value="`!ping` - Check if bot is alive\n`!help` - Show this message",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Setup",
        value="`!setup` - Configure bot settings (prefix, logs channel, admin role)",
        inline=False
    )
    
    embed.add_field(
        name="⚖️ Moderation",
        value="`!kick <member> [reason]` - Kick a member from server\n"
              "`!ban <member> [reason]` - Ban a member from server\n"
              "`!mute <member> <duration> [reason]` - Mute member for X seconds\n"
              "`!unmute <member>` - Remove mute from member\n"
              "`!warn <member> [reason]` - Warn a member",
        inline=False
    )
    
    embed.add_field(
        name="📋 Logs",
        value="`!modlogs [member]` - View moderation logs\n"
              "  • No args: Show last 10 server actions\n"
              "  • With member: Show last 10 actions on that member",
        inline=False
    )
    
    embed.add_field(
        name="🌐 Dashboard",
        value="View live moderation logs at: `http://your-domain:5000`\n"
              "Auto-refreshes every 5 seconds",
        inline=False
    )
    
    embed.add_field(
        name="📝 Permissions",
        value="• `kick` - Requires Kick Members\n"
              "• `ban` - Requires Ban Members\n"
              "• `mute/unmute` - Requires Moderate Members\n"
              "• `warn` - Requires Ban Members\n"
              "• `modlogs` - Requires Ban Members\n"
              "• `setup` - Requires Administrator",
        inline=False
    )
    
    embed.set_footer(text="Use !command --help for more info on specific commands")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    config = get_guild_config(ctx.guild.id)
    
    embed = discord.Embed(
        title="⚙️ Bot Setup",
        description="React to configure bot settings",
        color=discord.Color.green()
    )
    
    prefix = config.get("prefix", "!")
    logs_channel_id = config.get("logs_channel")
    admin_role_id = config.get("admin_role")
    
    logs_channel_name = "Not set"
    if logs_channel_id:
        channel = ctx.guild.get_channel(logs_channel_id)
        if channel:
            logs_channel_name = f"#{channel.name}"
    
    admin_role_name = "Not set"
    if admin_role_id:
        role = ctx.guild.get_role(admin_role_id)
        if role:
            admin_role_name = f"@{role.name}"
    
    embed.add_field(name="Current Prefix", value=f"`{prefix}`", inline=False)
    embed.add_field(name="Logs Channel", value=logs_channel_name, inline=False)
    embed.add_field(name="Admin Role", value=admin_role_name, inline=False)
    
    embed.add_field(
        name="Setup Options",
        value="1️⃣ - Change prefix\n"
              "2️⃣ - Set logs channel\n"
              "3️⃣ - Set admin role\n"
              "❌ - Cancel",
        inline=False
    )
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction("1️⃣")
    await msg.add_reaction("2️⃣")
    await msg.add_reaction("3️⃣")
    await msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and reaction.message.id == msg.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        
        if reaction.emoji == "1️⃣":
            await ctx.send("What should the new prefix be? (reply with a single character)")
            
            def check_msg(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            try:
                msg_prefix = await bot.wait_for('message', timeout=30.0, check=check_msg)
                new_prefix = msg_prefix.content.strip()
                if len(new_prefix) > 1:
                    await ctx.send("❌ Prefix must be a single character!")
                    return
                set_guild_config(ctx.guild.id, "prefix", new_prefix)
                await ctx.send(f"✅ Prefix changed to `{new_prefix}`")
            except:
                await ctx.send("❌ Setup cancelled (timeout)")
        
        elif reaction.emoji == "2️⃣":
            await ctx.send("Mention the channel for moderation logs (e.g., #logs)")
            
            def check_msg(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            try:
                msg_channel = await bot.wait_for('message', timeout=30.0, check=check_msg)
                if msg_channel.channel_mentions:
                    channel = msg_channel.channel_mentions[0]
                    set_guild_config(ctx.guild.id, "logs_channel", channel.id)
                    await ctx.send(f"✅ Logs channel set to {channel.mention}")
                else:
                    await ctx.send("❌ Please mention a valid channel!")
            except:
                await ctx.send("❌ Setup cancelled (timeout)")
        
        elif reaction.emoji == "3️⃣":
            await ctx.send("Mention the admin role (e.g., @Moderator)")
            
            def check_msg(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            try:
                msg_role = await bot.wait_for('message', timeout=30.0, check=check_msg)
                if msg_role.role_mentions:
                    role = msg_role.role_mentions[0]
                    set_guild_config(ctx.guild.id, "admin_role", role.id)
                    await ctx.send(f"✅ Admin role set to {role.mention}")
                else:
                    await ctx.send("❌ Please mention a valid role!")
            except:
                await ctx.send("❌ Setup cancelled (timeout)")
        
        elif reaction.emoji == "❌":
            await ctx.send("❌ Setup cancelled")
    
    except:
        await ctx.send("❌ Setup cancelled (timeout)")

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
