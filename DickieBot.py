#!/usr/bin/env python3
# DickieBot: The Impressionable Discord Bot

import os
import discord
import re
import random
import string
import parseUtil
import logging
import emoji
from cogs import general, factoids, inventory, info
from discord import utils
from dbFunctions import Connection
from dotenv import load_dotenv
from discord.ext import commands

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("log/myapp.log"),
        logging.StreamHandler(),
    ],
)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE = os.getenv("DATABASE")
OWNER = os.getenv("OWNER")
WEATHERAPIKEY = os.getenv("OWMAPIKEY")
GH_USR_PW_REPO = os.getenv("GITHUB")
GH_user, GH_token, GH_repo = GH_USR_PW_REPO.split(",")

# optional config file options
TRIGGER_ANYWHERE = int(os.getenv("TRIGGER_ANYWHERE", default=0)) == 1

intents = discord.Intents.all()
db = Connection(DATABASE)

botID = None
botName = None
help_command = commands.DefaultHelpCommand(no_category="Other")
bot = commands.Bot(
    command_prefix="!",
    description="DickieBot: The impressionable Discord bot!",
    help_command=help_command,
    intents=intents,
)


@bot.event
async def on_ready():
    global botID
    botID = bot.user.id

    global botName
    botName = bot.user.name

    await bot.change_presence(
        activity=discord.Activity(type=discord.ActivityType.watching, name="you.")
    )

    for gld in bot.guilds:
        # Sometimes the bot joins a server and automatically gets a role with the same name as him
        # If this happens, capture it and save the bot role
        role = utils.get(gld.roles, name=botName)
        roleID = 0 if role is None else role.id
        for i in gld.text_channels:
            db.initGuild(gld.id, roleID, i.id)

    logging.info(f"{bot.user.name} has connected to Discord!")
    logging.info(f"{bot.user} is user")
    logging.info(f"{botID} is ID")


@bot.event
async def on_guild_join(guild):
    # Sometimes the bot joins a server and automatically gets a role with the same name as him
    # If this happens, capture it and save the bot role
    role = utils.get(guild.roles, name=botName)
    roleID = 0 if role is None else role.id
    for i in guild.text_channels:
        if db.initGuild(guild.id, roleID, i.id):
            logging.info(f"{i.name} in {guild.name} initialized.")
        else:
            logging.info(f"{i.name} in {guild.name} was not initialized.")


@bot.event
async def on_guild_channel_create(channel):
    # If new text channel created, intialize.
    if type(channel) != discord.TextChannel:
        return

    role = utils.get(channel.guild.roles, name=botName)
    roleID = 0 if role is None else role.id
    if db.initGuild(channel.guild.id, roleID, channel.id):
        logging.info(f"{channel.name} in {channel.guild.name} initialized.")
    else:
        logging.info(f"{channel.name} in {channel.guild.name} was not initialized.")


@bot.event
async def on_guild_channel_delete(channel):
    # If channel removed, purge the record holding its state
    if db.deleteGuildState(channel.guild.id, channel.id):
        logging.info(f"{channel.name} in {channel.guild.name} deleted.")
    else:
        logging.info(f"{channel.name} in {channel.guild.name} was not deleted.")


@bot.event
async def on_guild_remove(guild):
    # If guild is removed, purge the record(s) holding its state
    if db.deleteGuildState(guild.id):
        logging.info(f"{guild.name} deleted.")
    else:
        logging.info(f"{guild.name} was not deleted.")


@bot.event
async def on_member_update(before, after):
    # Sometimes the bot joins a server and automatically gets a role with the same name as him
    # If that role is created and assigned AFTER joining at some later time, capture it and save the bot role
    if after.id == botID and len(before.roles) < len(after.roles):
        newRole = next(role for role in after.roles if role not in before.roles)

        if newRole.name == botName:
            for i in after.guild.text_channels:
                logging.info(f"{i.name} in {after.guild.name} initialized.")
                db.setBotRole(after.guild.id, newRole.id, i.id)


@bot.event
async def on_reaction_add(reaction, user):
    users = []
    thumbDown = 0
    msg = reaction.message

    # If the emoji is non-standard, return
    if reaction.custom_emoji:
        logging.info(
            f"{user.name} reacted to {msg.id} with custom emoji id {reaction.emoji.id}({type(reaction.emoji)})."
        )
        return
    else:
        logging.info(
            f"{user.name} reacted to {msg.id} with {emoji.demojize(reaction.emoji)}."
        )

    # Some reactions trigger the equivalent of !shutup
    if reaction.emoji in ("🤐", "🤫", "🔇") and msg.author == bot.user:
        found, duration, started = db.getShutUpDuration(msg.guild.id, msg.channel.id)
        if found:
            await msg.add_reaction(emoji="\U0001f197")  # Ok
        elif db.addShutUpRecord(msg.guild.id, msg.channel.id, 15):
            await msg.add_reaction(emoji="\U0001f197")  # Ok
            await msg.add_reaction(emoji="⌚")
            await msg.add_reaction(emoji="1️⃣")
            await msg.add_reaction(emoji="5️⃣")

    # Check to see if the people want a message removed
    for r in msg.reactions:
        if not r.emoji.startswith("👎"):
            continue

        thumbDown += r.count

        reactors = await r.users().flatten()
        for i in reactors:
            if i.id not in users:
                users.append(i.id)

    if len(users) >= 3 and thumbDown >= 3:
        logging.info(f"Deleting message {msg.id} by popular vote")
        await msg.delete()


@bot.event
async def on_message(message):
    logStmt = (
        f"{message.guild.name}-{message.channel.name}-{message.author.name}-{message.id}: {message.content}".encode(
            "ascii", "ignore"
        )
        .decode("ascii")
        .strip()
    )
    if message.attachments:
        logStmt += "\n" + ";".join([a.url for a in message.attachments])
    logging.info(logStmt)

    # Ignore bots (should include himself)
    if message.author.bot:
        return

    # Reject DMs. May do something with this later.
    if isinstance(message.channel, discord.channel.DMChannel):
        await message.channel.send("""I don't _do_ "DM"s ...yet""")
        return

    if message.content.startswith("!"):
        await bot.process_commands(message)
        return

    msgOut = None
    id = None
    reaction = 0
    cap = False
    isNSFW = 0

    msgIn = cleanMsgIn(message.content, message)

    if msgIn.startswith("_gives $self") and msgIn.endswith("_"):
        msgOut = inventoryCommand(msgIn, message)
        await message.channel.send(msgOut)
        return

    found, duration, started = db.getShutUpDuration(
        message.guild.id, message.channel.id
    )
    if found:
        return

    nsfwTag = 1 if message.channel.is_nsfw() else 0

    # Try to prevent triggering "$item" factoids when inventory empty
    omitNothing = 0 if len(db.getInventory(message.guild.id)) > 0 else 1

    # Check to see if factoid triggered
    msgInParts = msgIn.split("$self")
    msgIn = "$self".join(
        e.translate(str.maketrans(dict.fromkeys(string.punctuation))).lower()
        for e in msgInParts
    ).strip()

    id, msgOut, reaction, isNSFW = db.getFact(msgIn, nsfwTag, omitNothing)
    if id:
        logging.info(f"Triggered {id} with {msgIn}")

    # If factoid not triggered by incoming message, check for random
    randomNum = random.randint(1, 100)
    freq = db.getFreq(message.guild.id, message.channel.id)

    if id is None and randomNum <= freq:
        id, msgOut, reaction, isNSFW = db.getFact(None, nsfwTag, omitNothing)
        cap = True if msgOut.startswith("$item") else False

        logging.info(
            f"({message.guild.name}|{message.channel.name}) Triggered {id} with num {randomNum} <= freq {freq}"
        )

    # Update called metrics for factoid if called
    if id is not None:
        db.updateLastFact(message.guild.id, id, message.channel.id)
        db.updateLastCalled(id)

    # Replace $item variables each with random inventory item
    itemCount = msgOut.count("$item") if msgOut is not None else 0
    for i in range(itemCount):
        randItem = db.getInventoryItem(message.guild.id)
        msgOut = msgOut.replace("$item", randItem, 1)

    # Replace $nick variables with message author and replace $self in the response to appease Chazz
    if msgOut is not None:
        msgOut = msgOut.replace("$nick", "<@!" + str(message.author.id) + ">")
        msgOut = parseUtil.selfVarToMention(msgOut, botID)

    # Replace $rand variables each with random guild member or "nobody" if $rands outnumber guild members
    randCount = msgOut.count("$rand") if msgOut is not None else 0
    if randCount:
        logging.info(f"Found {randCount} rand{'s' if abs(randCount)!=1 else ''}")
        msgOut = replaceRands(msgOut, randCount, message)

    if msgOut is not None:
        if reaction == 1:
            await message.add_reaction(msgOut)
        else:
            mess = await message.channel.send(msgOut.capitalize() if cap else msgOut)
            if isNSFW:
                await mess.add_reaction("☣️")


def cleanMsgIn(msgIn, messageObj):
    # Standardize emotes to _<words>_
    msgIn = parseUtil.convertEmote(messageObj.content)

    # Collapse message to one line
    msgIn = re.sub(r"\n", " ", msgIn)

    # Convert notification reference to "$self" variable
    msgIn = parseUtil.mentionToSelfVar(
        msgIn, db.getBotRole(messageObj.guild.id, messageObj.channel.id), botID
    )
    # Discord removes spaces from between successive mentions, so we'll put one back if that's the case
    msgIn = msgIn.replace("$self<", "$self <")

    return msgIn


def inventoryCommand(msgIn, messageObj):
    # Given Inventory item
    itemRegex = re.compile(r"^_{1}(?:gives \$self )(.*)_{1}$")
    item = itemRegex.match(msgIn).group(1).strip("!.?")

    # If given a url or an item containing an image, reject
    if re.match(r"^<?https?:\/\/.*>?$", item, re.I) or re.match(
        r".*<?https?:\/\/.*(.gif|.jpg|.png|.jpeg|.bmp)>?.*$", item, re.I
    ):
        msgOut = "_throws it on the ground_"
    else:
        if not db.addToInventory(
            messageObj.guild.id,
            messageObj.author.display_name,
            item,
            messageObj.author.id,
        ):
            msgOut = "something went wrong"
        else:
            msgOut = "_added %s to his inventory_" % item

    return msgOut


def replaceRands(msgIn, randCount, messageObj):
    guildMembers = []
    if not randCount:
        return msgIn

    for m in messageObj.guild.members:
        if (
            m.status in (discord.Status.online, discord.Status.idle)
            and m.id != botID
            and messageObj.author.id != m.id
        ):
            guildMembers.append(m.id)

    if randCount >= len(guildMembers):
        for i in range(randCount - len(guildMembers)):
            guildMembers.append(0)
        randList = guildMembers
    else:
        randList = random.sample(guildMembers, randCount)

    msgOut = msgIn
    for i in range(randCount):
        if randList[i - 1] == 0:
            msgOut = msgOut.replace("$rand", "nobody", 1)
        else:
            randUser = "<@!" + str(randList[i - 1]) + ">"
            msgOut = msgOut.replace("$rand", randUser, 1)

    return msgOut


def main():
    bot.add_cog(general.General(bot, GH_user, GH_token, GH_repo))
    bot.add_cog(info.Information(bot, WEATHERAPIKEY))
    bot.add_cog(inventory.Inventory(bot, db))
    bot.add_cog(factoids.Factoids(bot, db, OWNER, TRIGGER_ANYWHERE))
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
