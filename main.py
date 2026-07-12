import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os
import asyncio

# --- 1. FLASK WEB SERVER (To keep Render alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- 2. DISCORD BOT SETUP ---
intents = discord.Intents.default()
intents.members = True          # Required to track role updates and scan members
intents.message_content = True  # Required to read the !bgrefresh command

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration: Replace these placeholder numbers with your actual Discord Role IDs
ROLE_MAPPING = {
    1457418827028500661: "youtube",
    1461009316424318997: "tiktok",
    1461009416597012562: "other socials",
    1461009481713582323: "from friends"
}

TARGET_CHANNEL_NAME = "📝┃join-log"

def get_join_log_channel(guild):
    """Helper function to find the channel by name."""
    return discord.utils.get(guild.text_channels, name=TARGET_CHANNEL_NAME)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

# Event: Triggers automatically when a member's roles change
@bot.event
async def on_member_update(before, after):
    # Check if a role was added
    if len(before.roles) < len(after.roles):
        # Find the newly added role(s)
        added_roles = [role for role in after.roles if role not in before.roles]
        
        for role in added_roles:
            if role.id in ROLE_MAPPING:
                channel = get_join_log_channel(after.guild)
                if channel:
                    source = ROLE_MAPPING[role.id]
                    await channel.send(f"{after.mention} joined from {source}")
                break # Only process the first matching role found

# Command: Clears the channel and re-checks everyone's roles
@bot.command()
@commands.has_permissions(manage_messages=True) # Limits command to staff/admins
async def bgrefresh(ctx):
    channel = get_join_log_channel(ctx.guild)
    if not channel:
        await ctx.send(f"Error: Could not find a channel named '{TARGET_CHANNEL_NAME}'.")
        return

    await ctx.send("Refreshing logs... Purging channel and scanning members.")

    # 1. Delete all existing messages in the target channel
    try:
        await channel.purge(limit=None)
    except discord.Forbidden:
        await ctx.send("Error: I do not have permission to delete messages in that channel.")
        return

    # 2. Loop through every member in the server and check their roles
    count = 0
    async for member in ctx.guild.fetch_members(limit=None):
        if member.bot:
            continue
            
        for role in member.roles:
            if role.id in ROLE_MAPPING:
                source = ROLE_MAPPING[role.id]
                await channel.send(f"{member.mention} joined from {source}")
                count += 1
                await asyncio.sleep(0.5) # Slight delay to avoid hitting Discord's rate limits too fast
                break # Move to the next member once a valid role is found

    await ctx.send(f"Refresh complete! Logged {count} members to {channel.mention}.")

# --- 3. START BOT ---
keep_alive()

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: No DISCORD_TOKEN found in environment variables!")