# This example requires the 'message_content' intent.
import os
import sqlite3
import discord
import db
from discord.ext import commands
from osu import Client
from dotenv import find_dotenv, load_dotenv

## Grabbing Keys
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
client_id = int(os.environ["client_id"])
client_secret = os.environ["client_secret"]
redirect_url = "http://127.0.0.1:8080"
key = os.environ["DISCORD_API_KEY"]

## Discord Bot Things
intents = discord.Intents.default()
intents.message_content = True
description = "The Massively Multipler osu! Project or MMosu!, turning osu! into a massively mulitplier game"
osu_client = Client.from_credentials(client_id, client_secret, redirect_url)
bot = commands.Bot(command_prefix='!', description=description, intents=intents)

## Connect to Local Database
users: db.UserDB = db.UserDB("mmosu.db", osu_client=osu_client)
scores: db.OsuScoreDB = db.OsuScoreDB("mmosu.db",osu_client=osu_client)

@bot.event
async def on_ready():
    # Tell the type checker that User is filled up at this point
    assert bot.user is not None
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

@bot.command()
async def link(ctx, user_id):
    try:
        osu_id = int(user_id)
    except ValueError:
        await ctx.send("Please provide a valid numeric osu! user ID.")
        return

    discord_id = ctx.author.id
    success = users.add_user(discord_id, osu_id)

    if success:
        await ctx.send("User was added to the database")
    else:
        await ctx.send("User could not be added to the database")
    
    print(users)
    

@bot.command()
async def clear_users(ctx):
    success = users.clear_records()
    if success:
        await ctx.send("User database was cleared")
    else:
        await ctx.send("User database could not be cleared")

@bot.command()
async def clear_scores(ctx):
    success = scores.clear_records()
    if success:
        await ctx.send("Score database was cleared")
    else:
        await ctx.send("Score database could not be cleared")


@bot.command()
async def submit(ctx):
    osu_id = users.get_osu_id(ctx.author.id)

    if osu_id is None:
        await ctx.send("You have not linked an osu! account yet. Use `!link <osu_id>` first.")
        return

    recent_scores = scores.get_recent_score(osu_id)

    if not recent_scores:
        await ctx.send("Could not find a recent score.")
        return

    found_score = recent_scores[0]
    display_name = scores.get_beatmap_display_name(found_score)

    success = scores.add_score(found_score)

    if success:
        await ctx.send(
            f"Successfully submitted score on {display_name} worth {found_score.pp}pp!"
        )
    else:
        await ctx.send(
            f"Failed to submit score on {display_name} worth {found_score.pp}pp..."
        )


@bot.command()
async def display_leaderboard(ctx):
    leaderboard = str(scores)
    if len(leaderboard) == 0:
        await ctx.send("leaderboard is empty right now")
        return
    await ctx.send(str(scores))

@bot.command()
async def display_leaderboard_pp(ctx):
    await ctx.send(f"The leaderboard has {scores.calculate_leaderboard_pp(0.95)} currently")


bot.run(key)




# @bot.command()
# async def check_recent(ctx):
#     connection = sqlite3.connect("user.db")
#     cur = connection.cursor()
#     res = cur.execute(f"""
#     SELECT osu_id
#     FROM users
#     WHERE {ctx.author.id}=discord_id
#     """
#     )
#     found_osu_id = res.fetchone()[0]
#     print(found_osu_id)
    

#     events = client.get_user_recent_activity(found_osu_id, limit=1)
#     print(events[0])
#     await ctx.send(str(events[0]))
