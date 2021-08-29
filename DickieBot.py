#!/usr/bin/env python3
#DickieBot: The Impressionable Discord Bot

import os
import discord
import re
import random
import string
import parseUtil

from cogs import general
from cogs import factoids
from cogs import inventory

from discord import member, utils
from dbFunctions import Connection
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE = os.getenv('DATABASE')
intents = discord.Intents.all()

db = Connection(DATABASE)

botID = None
botName = None
help_command = commands.DefaultHelpCommand(no_category = 'Other')
bot = commands.Bot(command_prefix = '!', description = 'DickieBot: The impressionable Discord bot!', help_command = help_command, intents = intents)

@bot.event
async def on_ready():
    global botID
    botID = bot.user.id

    global botName
    botName = bot.user.name

    for gld in bot.guilds: db.initGuild(gld.id, utils.get(gld.roles,name=botName).id)

    print(f'{bot.user.name} has connected to Discord!')
    print(f'{bot.user} is user')
    print(f'{botID} is ID')

@bot.event
async def on_guild_join(guild):
    guildRole = member.get(guild.roles,name=botName).id
    db.initGuild(guild.id, guildRole)

@bot.event
async def on_message(message):
    msgOut = None

    if message.author == bot.user:
        return

    print(message)
    print(message.content)

    # Standardize emotes to _<words>_
    msgIn = parseUtil.convertEmote(message.content) 

    # Collapse message to one line
    msgIn = re.sub(r'\n',' ',msgIn) 

    # Convert notification reference to "$self" variable
    msgIn = parseUtil.mentionToSelfVar(msgIn, db.getBotRole(message.guild.id), botID)

    if msgIn.startswith('_gives $self') and msgIn.endswith('_'):
        # Given Inventory item
        itemRegex = re.compile(r'^_{1}(?:gives \$self )(.*)_{1}$')
        item = itemRegex.match(msgIn).group(1)

        if not db.addToInventory(message.guild.id, message.author.display_name, item, message.author.id):
            msgOut = 'something went wrong'
        else:
            msgOut = '_added %s to his inventory_' % item
    elif not msgIn.startswith('!'):
        nsfwTag = 1 if message.channel.is_nsfw() else 0

        # Check to see if factoid triggered
        msgInParts = msgIn.split('$self')
        msgIn = '$self'.join(e.strip(string.punctuation).lower() for e in msgInParts).strip()

        id, msgOut = db.getFact(msgIn,nsfwTag)
        if id != None:
            db.updateLastFact(message.guild.id, id)

        # If factoid not triggered by incoming message, check for random
        randomNum = random.randint(1,100)
        if id == None and randomNum <= db.getFreq(message.guild.id):
            id, msgOut = db.getFact(None,nsfwTag)
            db.updateLastFact(message.guild.id, id)

        # Update called metrics for factoid if called
        if id != None:
            db.updateLastCalled(id)

        # Replace $nick variables with message author
        try:
            msgOut = msgOut.replace('$nick','<@!' + str(message.author.id) + '>') 
        except:
            pass

        # Replace $rand variables each with random guild member
        guildMembers = message.guild.members
        for m in guildMembers:
            if m.status != 'online' and m.status != 'idle': guildMembers.remove(m)

        randCount = msgOut.count('$rand') if msgOut != None else 0
        for i in range(randCount):
            randUser = '<@!' + str(random.sample(guildMembers,1)[0].id) + '>'
            msgOut = msgOut.replace('$rand', randUser, 1)

        # Replace $item variables each with random inventory item
        itemCount = msgOut.count('$item') if msgOut != None else 0
        for i in range(itemCount):
            randItem = db.getInventoryItem(message.guild.id)
            msgOut = msgOut.replace('$item', randItem, 1)
                
    if msgOut != None:
        await message.channel.send(msgOut)

    await bot.process_commands(message)

bot.add_cog(general.General(bot))
bot.add_cog(inventory.Inventory(bot, db))
bot.add_cog(factoids.Factoids(bot, db))
bot.run(TOKEN)