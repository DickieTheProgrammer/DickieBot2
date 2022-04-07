#!/usr/bin/env python3
# DickieBot: The Impressionable Discord Bot

import os
import discord
import re
import random
import string
import parseUtil
from cogs import general, factoids, inventory, info
from discord import utils
from dbFunctions import Connection
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE = os.getenv("DATABASE")
OWNER = os.getenv("OWNER")
WEATHERAPIKEY = os.getenv("OWMAPIKEY")
SOURCE = os.getenv("SOURCE")

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

    for gld in bot.guilds:
        # Sometimes the bot joins a server and automatically gets a role with the same name as him
        # If this happens, capture it and save the bot role
        role = utils.get(gld.roles, name=botName)
        roleID = 0 if role is None else role.id
        for i in gld.text_channels:
            db.initGuild(gld.id, roleID, i.id)

    print(f"{bot.user.name} has connected to Discord!")
    print(f"{bot.user} is user")
    print(f"{botID} is ID")


@bot.event
async def on_guild_join(guild):
    # Sometimes the bot joins a server and automatically gets a role with the same name as him
    # If this happens, capture it and save the bot role
    role = utils.get(guild.roles, name=botName)
    roleID = 0 if role is None else role.id
    for i in guild.text_channels:
        if db.initGuild(guild.id, roleID, i.id):
            print(f"""{i.name} in {guild.name} initialized.""")
        else:
            print(f"""{i.name} in {guild.name} was not initialized.""")


@bot.event
async def on_guild_channel_create(channel):
    # If new text channel created, intialize.
    if type(channel) != discord.TextChannel:
        return

    role = utils.get(channel.guild.roles, name=botName)
    roleID = 0 if role is None else role.id
    if db.initGuild(channel.guild.id, roleID, channel.id):
        print(f"""{channel.name} in {channel.guild.name} initialized.""")
    else:
        print(f"""{channel.name} in {channel.guild.name} was not initialized.""")


@bot.event
async def on_guild_channel_delete(channel):
    # If channel removed, purge the record holding its state
    if db.deleteGuildState(channel.guild.id, channel.id):
        print(f"""{channel.name} in {channel.guild.name} deleted.""")
    else:
        print(f"""{channel.name} in {channel.guild.name} was not deleted.""")


@bot.event
async def on_guild_remove(guild):
    # If guild is removed, purge the record(s) holding its state
    if db.deleteGuildState(guild.id):
        print(f"""{guild.name} deleted.""")
    else:
        print(f"""{guild.name} was not deleted.""")


@bot.event
async def on_member_update(before, after):
    # Sometimes the bot joins a server and automatically gets a role with the same name as him
    # If that role is created and assigned AFTER joining at some later time, capture it and save the bot role
    if after.id == botID and len(before.roles) < len(after.roles):
        newRole = next(role for role in after.roles if role not in before.roles)

        if newRole.name == botName:
            for i in after.guild.text_channels:
                print(f"""{i.name} in {after.guild.name} initialized.""")
                db.setBotRole(after.guild.id, newRole.id, i.id)


@bot.event
async def on_reaction_add(reaction, user):
    users = []
    thumbDown = []
    msg = reaction.message

    # If the message wasn't authored by bot or the emoji is non-standard, return
    if msg.author != bot.user or type(reaction.emoji) == discord.PartialEmoji:
        return

    if reaction.emoji in ("🤐", "🤫", "🔇"):
        found, duration, started = db.getShutUpDuration(msg.guild.id, msg.channel.id)
        if found:
            await msg.add_reaction(emoji="\U0001f197")  # Ok
        else:
            success = db.addShutUpRecord(msg.guild.id, msg.channel.id, 5)
            if success:
                await msg.add_reaction(emoji="\U0001f197")  # Ok
                await msg.add_reaction(emoji="⌚")
                await msg.add_reaction(emoji="5️⃣")

    for r in msg.reactions:
        reactors = await r.users().flatten()
        for i in reactors:
            if i not in users:
                users.append(i.id)
        if r.emoji.startswith("👎"):
            thumbDown.append(r.emoji)

    if len(users) >= 3 and len(thumbDown) >= 3:
        await msg.delete()


@bot.event
async def on_message(message):  # noqa: C901
    msgOut = None
    botCommand = True if message.content.startswith("!") else False
    id = None
    reaction = 0
    cap = False

    # Ignore bots (should include himself)
    if message.author.bot:
        return

    # Reject DMs. May do something with this later.
    if isinstance(message.channel, discord.channel.DMChannel):
        await message.channel.send("""I don't _do_ "DM"s""")
        return

    print("===========================================================")
    print(message.content)
    print(message)

    # Standardize emotes to _<words>_
    msgIn = parseUtil.convertEmote(message.content)

    # Collapse message to one line
    msgIn = re.sub(r"\n", " ", msgIn)

    # Convert notification reference to "$self" variable
    msgIn = parseUtil.mentionToSelfVar(
        msgIn, db.getBotRole(message.guild.id, message.channel.id), botID
    )
    # Discord removes spaces from between successive mentions, so we'll put one back if that's the case
    msgIn = msgIn.replace("$self<", "$self <")

    if msgIn.startswith("_gives $self") and msgIn.endswith("_"):
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
                message.guild.id, message.author.display_name, item, message.author.id
            ):
                msgOut = "something went wrong"
            else:
                msgOut = "_added %s to his inventory_" % item

    elif not botCommand:
        found, duration, started = db.getShutUpDuration(
            message.guild.id, message.channel.id
        )
        if found:
            return

        nsfwTag = 1 if message.channel.is_nsfw() else 0

        # Check to see if factoid triggered
        msgInParts = msgIn.split("$self")
        msgIn = "$self".join(
            e.translate(str.maketrans(dict.fromkeys(string.punctuation))).lower()
            for e in msgInParts
        ).strip()

        id, msgOut, reaction = db.getFact(msgIn, nsfwTag)
        if id:
            print(f"Triggered {id} with {msgIn}")

        # If factoid not triggered by incoming message, check for random
        randomNum = random.randint(1, 100)
        print(
            f"Random number {randomNum} <= {db.getFreq(message.guild.id, message.channel.id)} ({message.guild.name}|{message.channel.name})?"
        )

        if id is None and randomNum <= db.getFreq(message.guild.id, message.channel.id):
            id, msgOut, reaction = db.getFact(None, nsfwTag)
            if msgOut.startswith("$item"):
                cap = True
            print(f"Triggered {id}")

        # Update called metrics for factoid if called
        if id is not None:
            db.updateLastFact(message.guild.id, id, message.channel.id)
            db.updateLastCalled(id)

        # Replace $nick variables with message author
        try:
            msgOut = msgOut.replace("$nick", "<@!" + str(message.author.id) + ">")
        except:  # noqa: E722
            pass

        # Replace $rand variables each with random guild member or "nobody" if $rands outnumber guild members
        randCount = msgOut.count("$rand") if msgOut is not None else 0
        print(f"Found {randCount} rand{'s' if randCount!=1 else ''}")

        if randCount:
            guildMembers = []

            for m in message.guild.members:
                if (m.status in (discord.Status.online,discord.Status.idle) and m.id != botID):
                    print(f"Adding user {m.name} - {m.nick} - {m.id} to rand list")
                    guildMembers.append(m.id)

            if randCount >= len(guildMembers):
                for i in range(randCount-len(guildMembers)):
                    guildMembers.append(0)
                randList = guildMembers
            else:
                randList = random.sample(guildMembers, randCount)

            for i in range(randCount):
                if randList[i-1] == 0:
                    msgOut = msgOut.replace("$rand", "nobody", 1)
                else:
                    randUser = "<@!" + str(randList[i - 1]) + ">"
                    msgOut = msgOut.replace("$rand", randUser, 1)

        # Replace $item variables each with random inventory item
        itemCount = msgOut.count("$item") if msgOut is not None else 0
        for i in range(itemCount):
            randItem = db.getInventoryItem(message.guild.id)
            msgOut = msgOut.replace("$item", randItem, 1)

    if msgOut is not None:
        if reaction == 1:
            await message.add_reaction(msgOut)
        else:
            await message.channel.send(msgOut.capitalize() if cap else msgOut)

    await bot.process_commands(message)


def main():
    bot.add_cog(general.General(bot, SOURCE))
    bot.add_cog(info.Information(bot, WEATHERAPIKEY))
    bot.add_cog(inventory.Inventory(bot, db))
    bot.add_cog(factoids.Factoids(bot, db, OWNER, TRIGGER_ANYWHERE))
    bot.run(TOKEN)


if __name__ == "__main__":
    main()
