import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
import os
import asyncio
import re

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
intents.members = True          # Required to track joins and role updates
intents.message_content = True  # Required to read commands

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"), 
    intents=intents
)

ROLE_MAPPING = {
    1457418827028500661: "youtube",
    1461009316424318997: "tiktok",
    1461009416597012562: "other socials",
    1461009481713582323: "from friends"
}

TARGET_CHANNEL_NAME = "📝┃join-log"

def get_join_log_channel(guild):
    return discord.utils.get(guild.text_channels, name=TARGET_CHANNEL_NAME)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

# --- NEW EVENT: Triggers ONLY when a member first hits the server ---
@bot.event
async def on_member_join(member):
    # Find the "🍍・roles" channel by its exact name
    roles_channel = discord.utils.get(member.guild.text_channels, name="🍍・roles")
    if roles_channel:
        # Pings them immediately upon joining, then deletes the message 15 seconds later
        await roles_channel.send(
            f"{member.mention} React above to get notified.", 
            delete_after=15.0
        )

# Event: Triggers automatically when a member's roles change (Used ONLY for tracking logs now)
@bot.event
async def on_member_update(before, after):
    # Check if a role was added
    if len(before.roles) < len(after.roles):
        added_roles = [role for role in after.roles if role not in before.roles]
        
        # LOGGING JOIN ROLES ONLY
        for role in added_roles:
            if role.id in ROLE_MAPPING:
                channel = get_join_log_channel(after.guild)
                if channel:
                    source = ROLE_MAPPING[role.id]
                    await channel.send(f"({after.id}) {after.mention} joined from **{source}**")
                break 

# Command 1: Clears the channel and re-checks everyone's roles
@bot.command()
@commands.has_permissions(manage_messages=True)
async def bgrefresh(ctx):
    channel = get_join_log_channel(ctx.guild)
    if not channel:
        await ctx.send(f"Error: Could not find a channel named '{TARGET_CHANNEL_NAME}'.")
        return

    await ctx.send("Refreshing logs... Purging channel and scanning members.")

    try:
        await channel.purge(limit=None)
    except discord.Forbidden:
        await ctx.send("Error: I do not have permission to delete messages in that channel.")
        return

    count = 0
    async for member in ctx.guild.fetch_members(limit=None):
        if member.bot:
            continue
            
        for role in member.roles:
            if role.id in ROLE_MAPPING:
                source = ROLE_MAPPING[role.id]
                await channel.send(f"({member.id}) {member.mention} joined from **{source}**")
                count += 1
                await asyncio.sleep(0.5)
                break

    await ctx.send(f"Refresh complete! Logged {count} members to {channel.mention}.")


# Command 2: Incremental add
@bot.command()
@commands.has_permissions(manage_messages=True)
async def bgadd(ctx):
    channel = get_join_log_channel(ctx.guild)
    if not channel:
        await ctx.send(f"Error: Could not find a channel named '{TARGET_CHANNEL_NAME}'.")
        return

    progress_msg = await ctx.send("🔍 Checking existing logs and finding missing members...")

    logged_user_ids = set()
    async for message in channel.history(limit=None):
        matches = re.findall(r'\((\d+)\)', message.content)
        for user_id in matches:
            logged_user_ids.add(int(user_id))

    added_count = 0
    async for member in ctx.guild.fetch_members(limit=None):
        if member.bot or member.id in logged_user_ids:
            continue
            
        for role in member.roles:
            if role.id in ROLE_MAPPING:
                source = ROLE_MAPPING[role.id]
                await channel.send(f"({member.id}) {member.mention} joined from **{source}**")
                added_count += 1
                await asyncio.sleep(0.5)
                break

    await progress_msg.delete()
    await ctx.send(f"✅ Incremental add complete! Added **{added_count}** new missing members to {channel.mention}.")


# Command 3: Displays real-time server referral statistics
@bot.command()
async def bgstats(ctx):
    stats = {name: 0 for name in ROLE_MAPPING.values()}
    no_role_count = 0
    total_members = 0

    progress_msg = await ctx.send("📊 Calculating server referral statistics...")

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

    embed = discord.Embed(title="📈 Server Referral Statistics", color=discord.Color.blue())
    embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    for role_name, count in stats.items():
        display_name = role_name.title()
        embed.add_field(name=f"🔗 {display_name}", value=f"**{count}** members", inline=False)
        
    embed.add_field(name="❓ Unassigned / Other", value=f"**{no_role_count}** members", inline=False)
    embed.set_footer(text=f"Total Members Scanned: {total_members}")

    await progress_msg.delete()
    await ctx.send(embed=embed)

# --- 3. START BOT ---
keep_alive()

TOKEN = os.environ.get("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: No DISCORD_TOKEN found in environment variables!")