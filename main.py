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
intents.message_content = True  # Required to read the commands

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration: Your actual Discord Role IDs
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

# Command 1: Clears the channel and re-checks everyone's roles
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

# Command 2: Displays real-time server referral statistics
@bot.command()
async def bgstats(ctx):
    # Initialize counts for each role name
    stats = {name: 0 for name in ROLE_MAPPING.values()}
    no_role_count = 0
    total_members = 0

    # Inform the user that the scan is starting
    progress_msg = await ctx.send("📊 Calculating server referral statistics...")

    # Scan all members in the server
    async for member in ctx.guild.fetch_members(limit=None):
        if member.bot:
            continue
            
        total_members += 1
        has_tracked_role = False
        
        for role in member.roles:
            if role.id in ROLE_MAPPING:
                role_name = ROLE_MAPPING[role.id]
                stats[role_name] += 1
                has_tracked_role = True
                break
                
        if not has_tracked_role:
            no_role_count += 1

    # Format the stats beautifully into a Discord Embed message
    embed = discord.Embed(
        title="📈 Server Referral Statistics", 
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    # Add fields for the tracked roles
    for role_name, count in stats.items():
        display_name = role_name.title()
        embed.add_field(name=f"🔗 {display_name}", value=f"**{count}** members", inline=False)
        
    embed.add_field(name="❓ Unassigned / Other", value=f"**{no_role_count}** members", inline=False)
    embed.set_footer(text=f"Total Members Scanned: {total_members}")

    # Remove the progress message and send the statistics card
    await progress_msg.delete()
    await ctx.send(embed=embed)

# --- 3. START BOT ---
keep_alive()

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: No DISCORD_TOKEN found in environment variables!")