# This example requires the 'message_content' intent.
import os
import discord
import sqlite3
from discord.ext import commands
from discord import app_commands
from osu import Client
from dotenv import find_dotenv, load_dotenv

## Grabbing Keys
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
client_id = int(os.environ["client_id"])
client_secret = os.environ["client_secret"]
redirect_uri = "http://127.0.0.1:8080"
key = os.environ["DISCORD_API_KEY"]



## Discord Bot Things
intents = discord.Intents.default()
intents.message_content = True
description = "Hell, This is actual hell right now"
client = Client.from_credentials(client_id, client_secret, redirect_uri)
bot = commands.Bot(command_prefix='?', description=description, intents=intents)

@bot.event
async def on_ready():
    # Tell the type checker that User is filled up at this point
    assert bot.user is not None

    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

@bot.command()
async def add(ctx, left: int, right: int):
    """Adds two numbers together."""
    await ctx.send(left + right)


@bot.command()
async def say(ctx, text):
    """Bot says something."""

    if "idiot" in text:
        await ctx.send("I'm not saying that")
    else:
        await ctx.send(text)

@bot.command()
async def check_recent(ctx):
    connection = sqlite3.connect("user.db")
    cur = connection.cursor()
    res = cur.execute(f"""
    SELECT osu_id
    FROM users
    WHERE {ctx.author.id}=discord_id
    """
    )
    found_osu_id = res.fetchone()[0]
    print(found_osu_id)
    

    events = client.get_user_recent_activity(found_osu_id, limit=1)
    print(events[0])
    await ctx.send(str(events[0]))

@bot.command()
async def link(ctx, user_id):
    try:
        osu_id = int(user_id)
    except:
        print("bot broke cause id couldn't be casted")
    
    discord_id = ctx.author.id

    connection = sqlite3.connect("user.db")
    cur = connection.cursor()
    cur.execute(
    """
    INSERT INTO users (discord_id, osu_id)
    VALUES(?, ?)
    """, (discord_id,osu_id)
    )
    connection.commit()

    for row in cur.execute(""" SELECT * FROM users"""):
        print(row)

    connection.close()

    




bot.run(key)
