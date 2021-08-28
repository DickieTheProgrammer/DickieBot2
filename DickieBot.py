#!/usr/bin/env python3
#DickieBot: The Impressionable Discord Bot

import os
import discord
import re
import random
import string

from discord import member, utils
from discord.channel import TextChannel

from dbFunctions import Connection
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE = os.getenv('DATABASE')
intents = discord.Intents.all()

db = Connection(DATABASE)
help_command = commands.DefaultHelpCommand(no_category='Commands')
bot = commands.Bot(command_prefix='!', description='DickieBot: The impressionable Discord bot!', help_command=help_command)

botID = None
botName = None

roleIDs = {}
lastFact = {}

nothingList = [
    "https://giphy.com/embed/l41YlPKMCfNoseS8E",
    "https://giphy.com/embed/fxqlDFNqdvYiRuCLf4",
    "https://giphy.com/embed/llJIUkV73NmqvYWVqF",
    "https://giphy.com/embed/3ohhwsjzpejaSWoTkI",
    "https://c.tenor.com/nEdV6gnb35UAAAAC/i-have-nothing-eye-roll.gif",
    "https://c.tenor.com/e7Zo7FajjBUAAAAC/bejo-avarisocio.gif",
    "https://c.tenor.com/HYJcMD1hjPQAAAAM/i-have-nothing-i-dont-have-anything.gif",
    "https://giphy.com/embed/QZOaeparxsNOfKWbER",
    "https://giphy.com/embed/gjIvS6VpFQKNP0ZcvJ",
    "https://c.tenor.com/q-E5wj1K6OYAAAAM/monsters-inc-sully.gif"
]

emoteRegex = [
    # Emotes starting with underscores, retrieve group 2
    re.compile(r"^(_{1,2}\*{0,3}([^_*]*)\*{0,3}_{1,2})$"),
    # Emotes starting with asterisks, retrieve group 2
    re.compile(r"^(\*{1}|\*{3})_{0,2}([^_*]*)_{0,2}(\*{1}|\*{3})$")
]

def convertEmote(msg):
    if emoteRegex[0].match(msg):
        # Emote starts with underscore
        msgOut = '_' + emoteRegex[0].match(msg).group(2) + '_'
    elif emoteRegex[1].match(msg):
        # Emote starts with asterisk
        msgOut = '_' + emoteRegex[1].match(msg).group(2) + '_'
    elif msg.startswith('/me '):
        msgOut = '_' + msg[4:] + '_'
    else:
        # Ain't no emote
        msgOut = msg

    return(msgOut)

def mentionToSelfVar(msgIn,botRole):
    # Nick ping
    nick = '<@' + str(botID) + '>'
    msgOut = msgIn.replace('!','').replace(nick,'$self') 
    # Role ping
    role = '<@&' + str(botRole) + '>'
    msgOut = msgIn.replace(role,'$self') 

    return(msgOut)

@bot.event
async def on_ready():
    global botID
    botID = bot.user.id
    global botName
    botName = bot.user.name
    global roleIDs

    for gld in bot.guilds: 
        roleIDs[gld.id]=utils.get(gld.roles,name=botName).id

    print(f'{bot.user.name} has connected to Discord!')
    print(f'{bot.user} is user')
    print(f'{botID} is ID')

@bot.event
async def on_guild_join(guild):
    guildRole = member.get(guild.roles,name=botName).id
    global roleIDs
    roleIDs[guild.id]=guildRole

@bot.event
async def on_message(message):
    msgToSend = None

    if message.author == bot.user:
        return

    print(f'{message}')

    # Standardize emotes to _<words>_
    msgIn = convertEmote(message.content) 

    # Collapse message to one line
    msgIn = re.sub(r'\n',' ',msgIn) 

    # Convert notification reference to "$self" variable
    msgIn = mentionToSelfVar(msgIn, roleIDs[message.guild.id])

    if msgIn.startswith('_gives $self') and msgIn.endswith('_'):
        # Given Inventory item
        itemRegex = re.compile(r'^_{1}(?:gives \$self )(.*)_{1}$')
        item = itemRegex.match(msgIn).group(1)

        if not db.addToInventory(message.guild.id, message.author.display_name, item, message.author.id):
            msgToSend = 'something went wrong'
        else:
            msgToSend = '_added %s to his inventory_' % item
    elif not msgIn.startswith('!'):
        nsfwTag = 1 if message.channel.is_nsfw() else 0

        # Check to see if factoid triggered
        msgInParts = msgIn.split('$self')
        msgIn = '$self'.join(e.strip(string.punctuation).lower() for e in msgInParts).strip()

        id, msgToSend = db.getFact(msgIn,nsfwTag)
        lastFact[message.guild.id] = id

        if id != None:
            db.updateLastCalled(id)

        # Replace $nick variables with message author
        try:
            msgToSend = msgToSend.replace('$nick','<@!' + str(message.author.id) + '>') 
        except:
            None

        # Replace $rand variables each with random guild member
        guildMembers = message.guild.members
        randCount = msgToSend.count('$rand') if msgToSend != None else 0
        for i in range(randCount):
            randUser = '<@!' + str(random.sample(guildMembers,1)[0].id) + '>'
            msgToSend = msgToSend.replace('$rand', randUser, 1)

        # Replace $item variables each with random inventory item
        itemCount = msgToSend.count('$item') if msgToSend != None else 0
        for i in range(itemCount):
            randItem = db.getInventoryItem(message.guild.id)
            msgToSend = msgToSend.replace('$item', randItem, 1)
                

    if msgToSend != None:
        await message.channel.send(msgToSend)

    await bot.process_commands(message)

######### GENERAL COMMANDS #########
@bot.command(name = 'roll', description = f'Simulates dice rolls. Syntax is !roll {{number}}d{{number}}.', brief = f'Rolls dem bones - {{number}}d{{number}}')
async def roll(ctx, dice: str):
    # Rolls a dice in NdN format. 
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await ctx.send(f'Format has to be in {{number}}**d**{{number}}')
        return

    if rolls>25:
        msgToSend = 'Max 25 dice'
    elif rolls <= 0 or limit <= 0:
        msgToSend = 'Positive numbers only'
    else:
        msgToSend = ', '.join(str(random.randint(1, limit)) for r in range(rolls))

    await ctx.send(msgToSend)

@bot.command(name = 'src', aliases=['source','sauce'], description='Returns GitHub source URL.', brief='Returns source URL')
async def source(ctx):
    await ctx.send("<https://github.com/DickieTheProgrammer/DickieBot2>")
    
######### INVENTORY COMMANDS #########
@bot.command(name = 'inv', aliases=['inventory','stuff','items'], description="Returns current guild's inventory. Aliases: inventory, stuff.", brief='Displays inventory')
# add @commands.cooldown(2, 20, commands.BucketType.user) here?
async def inv(ctx):
    itemList = db.getInventory(ctx.guild.id)

    if itemList == None:
        await ctx.send("Something went wrong fetching inventory.")
        return

    deTupledList = [' '.join(elem) for elem in itemList]
    listLen = len(deTupledList)

    # Randomly order list to give "first in" items some visibility
    deTupledList = random.sample(deTupledList,listLen)

    if listLen == 0:
        msgToSend = random.sample(nothingList,1)[0]
    else:
        msgToSend = "I have:\n\t○ " + "\n\t○ ".join(deTupledList[0:5])

        if listLen > 5:
            msgToSend = msgToSend + "\nand, like, " + str(listLen-5) + " other thing"
        if listLen > 6:
            msgToSend = msgToSend + "s"

    await ctx.send(msgToSend)

@bot.command(name = 'whogave', aliases = ['whogaveyou','whogaveu'], description = 'Tells who gave me an item', brief = 'Who gave me a thing?')
async def whogave(ctx, *, item):
    donors = db.getItemDonor(ctx.guild.id,item)
    resolvedDonors = []

    if donors == None:
        msgToSend = "Something went wrong finding the donor of this item."
    elif len(donors) == 0:
        msgToSend = "I don't have that."
    else:
        for donor in donors: resolvedDonors.append('<@!' + donor + '>')
        msgToSend = "It was %s" % ' and '.join(resolvedDonors)
    
    await ctx.send(msgToSend)
        
######### FACTOID COMMANDS #########
@bot.command(name = 'on', 
            aliases = ['onnsfw'], 
            description = f"""Assign a response to triggering phrase. !on<nsfw> {{trigger}} -say {{response}}. 
            Using !onnsfw marks the response as NSFW and will not be triggered in SFW channels.
            Use $self to refer to the bot in the trigger. i.e. !on "Hi $self" -say Hello. 
            Use $rand, $nick, and $item in response to sub in a random user, the triggering user, and an inventory item, respectively.
            $item consumes the inventory item.""", 
            brief = 'Teach me to respond to something')
async def on(ctx, *, args):
    parts = args.split('-say')
    if len(parts) <= 1:
        msgToSend = 'Usage is !on<nsfw> trigger -say response'

    trigger = convertEmote(parts[0]).strip()
    botCommand = True if trigger.startswith('!') else False

    cleanTrigger = mentionToSelfVar(trigger, roleIDs[ctx.guild.id])
    triggerParts = cleanTrigger.split('$self')
    cleanTrigger = '$self'.join(e.strip(string.punctuation).lower() for e in triggerParts).strip()

    if botCommand:
        msgToSend = "I'm not remembering bot commands."
    elif len(cleanTrigger) <= 3:
        msgToSend = 'Trigger must be >= 4 alphanumeric characters'
    else:    
        if trigger.startswith('_') and trigger.endswith('_'):
            cleanTrigger = '_' + trigger + '_'

        response = ''.join(parts[1:]).strip()

        nsfw = 1 if ctx.invoked_with == 'onnsfw' else 0

        success, known = db.addFact(cleanTrigger, response, nsfw, ctx.message.author.display_name, ctx.message.author.id)

        if success:
            msgToSend = f"""Ok. When I see "{trigger}" I'll say "{response}\""""
        else:
            if known:
                msgToSend = 'Oh, I already know that.'
            else:
                msgToSend = 'Something went wrong adding this factoid.'

    await ctx.send(msgToSend)

bot.run(TOKEN)