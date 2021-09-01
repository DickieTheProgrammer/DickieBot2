#!/usr/bin/env python3
#DickieBot: The Impressionable Discord Bot

import os
import discord
import re
import random
import string
import parseUtil

from cogs import general, factoids, inventory, info

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

    for gld in bot.guilds: 
        # Sometimes the bot joins a server and automatically gets a role with the same name as him
        # If this happens, capture it and save the bot role
        role = utils.get(gld.roles,name=botName)
        roleID = 0 if role == None else role.id
        db.initGuild(gld.id, roleID)

    print(f'{bot.user.name} has connected to Discord!')
    print(f'{bot.user} is user')
    print(f'{botID} is ID')

@bot.event
async def on_guild_join(guild):
    # Sometimes the bot joins a server and automatically gets a role with the same name as him
    # If this happens, capture it and save the bot role
    role = utils.get(guild.roles,name=botName)
    roleID = 0 if role == None else role.id
    db.initGuild(guild.id, roleID)

@bot.event
async def on_member_update(before, after):
    # Sometimes the bot joins a server and automatically gets a role with the same name as him
    # If that role is created and assigned AFTER joining at some later time, capture it and save the bot role
    if after.id == botID and len(before.roles) < len(after.roles):
        newRole = next(role for role in after.roels if role not in before.roles)

        if newRole.name == botName:
            db.setBotRole(after.guild.id, newRole.id)

@bot.event
async def on_message(message):
    msgOut = None
    botCommand = True if message.content.startswith('!') else False

    if message.author == bot.user: return

    if isinstance(message.channel, discord.channel.DMChannel): 
        await message.channel.send("""I don't _do_ "DM"s""")
        return

    print("===========================================================")
    print(message.content)
    print(message)

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
    elif not botCommand:
        nsfwTag = 1 if message.channel.is_nsfw() else 0

        # Check to see if factoid triggered
        msgInParts = msgIn.split('$self')
        msgIn = '$self'.join(e.strip(string.punctuation).lower() for e in msgInParts).strip()

        id, msgOut = db.getFact(msgIn,nsfwTag)
        ###if id != None: db.updateLastFact(message.guild.id, id)

        # If factoid not triggered by incoming message, check for random
        randomNum = random.randint(1,100)
        print(f"Random number {randomNum} <= {db.getFreq(message.guild.id)} ({message.guild.name})?")
        if id == None and randomNum <= db.getFreq(message.guild.id): id, msgOut = db.getFact(None,nsfwTag)

        # Update called metrics for factoid if called
        if id != None:
            db.updateLastFact(message.guild.id, id)
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

        # Replace $rand variables each with random guild member or "nobody" if $rands outnumber guild members
        randCount = msgOut.count('$rand') if msgOut != None else 0
        randList = random.sample(guildMembers,randCount)
        for i in range(randCount):
            if i >= len(randList): randList.append('nobody')
            randUser = '<@!' + str(randList[i-1].id) + '>'
            msgOut = msgOut.replace('$rand', randUser, 1)

        # Replace $item variables each with random inventory item
        itemCount = msgOut.count('$item') if msgOut != None else 0
        for i in range(itemCount):
            randItem = db.getInventoryItem(message.guild.id)
            msgOut = msgOut.replace('$item', randItem, 1)
                
    if msgOut != None:
        await message.channel.send(msgOut)
        
    #embed = discord.Embed()
    #embed.description = "This is a hyperlink test. Check out [Google.com](http://www.google.com)"
    #await message.channel.send(embed = embed)

    await bot.process_commands(message)

bot.add_cog(general.General(bot))
bot.add_cog(info.Information(bot))
bot.add_cog(inventory.Inventory(bot, db))
bot.add_cog(factoids.Factoids(bot, db))
bot.run(TOKEN)