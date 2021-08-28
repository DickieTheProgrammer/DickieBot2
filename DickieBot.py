#!/usr/bin/env python3
#DickieBot: The Impressionable Discord Bot

import os
import discord
import re
import random
import string
import typing

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

botID = None
botName = None
help_command = commands.DefaultHelpCommand(no_category = 'Commands')
bot = commands.Bot(command_prefix = '!', description = 'DickieBot: The impressionable Discord bot!', help_command = help_command, intents = intents)

roleIDs = {}
lastFact = {}
randPerc = {}
DEFAULTPERC = 5

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

noList= [
    "https://c.tenor.com/2yJBnYOY_j8AAAAC/tonton-tonton-sticker.gif",
    "https://c.tenor.com/UIrQocNe4xYAAAAM/no-no-no-way.gif",
    "https://c.tenor.com/U9oGKTRaBo0AAAAM/bugs-bunny-bunny.gif",
    "https://c.tenor.com/xAyrbho-SPEAAAAM/bachelor-mattjames.gif"
    "https://c.tenor.com/28WY5uWjdv0AAAAM/nope-sloth.gif",
    "https://giphy.com/embed/daPCSjwus6UR2JxRX1",
    "https://giphy.com/embed/3ov9jLsBqPh6rjuHuM",
    "https://giphy.com/embed/VgqtLbNtJEWtVlfMVv",
    "https://giphy.com/embed/QIPEV0HWAiXVm",
    "https://giphy.com/embed/XymaJlgorUL8vOfF88"
]

emoteRegex = [
    # Emotes starting with underscores, retrieve group 2
    re.compile(r"^(_{1,2}\*{0,3}([^_*]*)\*{0,3}_{1,2})$"),
    # Emotes starting with asterisks, retrieve group 2
    re.compile(r"^(\*{1}|\*{3})_{0,2}([^_*]*)_{0,2}(\*{1}|\*{3})$")
]

def convertEmote(msgIn):
    if emoteRegex[0].match(msgIn):
        # Emote starts with underscore
        msgOut = '_' + emoteRegex[0].match(msgIn).group(2) + '_'
    elif emoteRegex[1].match(msgIn):
        # Emote starts with asterisk
        msgOut = '_' + emoteRegex[1].match(msgIn).group(2) + '_'
    elif msgIn.startswith('/me '):
        msgOut = '_' + msgIn[4:] + '_'
    else:
        # Ain't no emote
        msgOut = msgIn

    return(msgOut)

def mentionToSelfVar(msgIn,botRole):
    msgOut = msgIn

    # Nick ping
    nick = '<@' + str(botID) + '>'
    msgOut = msgOut.replace('!','').replace(nick,'$self') 
    # Role ping
    role = '<@&' + str(botRole) + '>'
    msgOut = msgOut.replace(role,'$self') 

    return(msgOut)

@bot.event
async def on_ready():
    global botID
    botID = bot.user.id

    global botName
    botName = bot.user.name

    global roleIDs
    for gld in bot.guilds: 
        roleIDs[gld.id] = utils.get(gld.roles,name=botName).id

    global randPerc
    for gld in bot.guilds:
        randPerc[gld.id] = DEFAULTPERC

    print(f'{bot.user.name} has connected to Discord!')
    print(f'{bot.user} is user')
    print(f'{botID} is ID')

@bot.event
async def on_guild_join(guild):
    guildRole = member.get(guild.roles,name=botName).id

    global roleIDs
    roleIDs[guild.id]=guildRole

    global randPerc
    randPerc[guild.id] = DEFAULTPERC

@bot.event
async def on_message(message):
    msgOut = None

    if message.author == bot.user:
        return

    print(message)
    print(message.content)

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
            msgOut = 'something went wrong'
        else:
            msgOut = '_added %s to his inventory_' % item
    elif not msgIn.startswith('!'):
        nsfwTag = 1 if message.channel.is_nsfw() else 0

        # Check to see if factoid triggered
        msgInParts = msgIn.split('$self')
        msgIn = '$self'.join(e.strip(string.punctuation).lower() for e in msgInParts).strip()

        id, msgOut = db.getFact(msgIn,nsfwTag)
        lastFact[message.guild.id] = id

        # If factoid not triggered by incoming message, check for random
        randomNum = random.randint(1,100)
        if id == None and randomNum <= randPerc[message.guild.id]:
            id, msgOut = db.getFact(None,nsfwTag)
            lastFact[message.guild.id] = id

        # Update called metrics for factoid if called
        if id != None:
            db.updateLastCalled(id)

        # Replace $nick variables with message author
        try:
            msgOut = msgOut.replace('$nick','<@!' + str(message.author.id) + '>') 
        except:
            None

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
        msgOut = 'Max 25 dice'
    elif rolls <= 0 or limit <= 0:
        msgOut = 'Positive numbers only'
    else:
        msgOut = ', '.join(str(random.randint(1, limit)) for r in range(rolls))

    await ctx.send(msgOut)

@bot.command(name = 'src', aliases=['source','sauce'], description='Returns GitHub source URL.', brief='Returns source URL')
async def source(ctx):
    await ctx.send("<https://github.com/DickieTheProgrammer/DickieBot2>")
    
######### INVENTORY COMMANDS #########
@bot.command(name = 'inv', aliases=['inventory','stuff','items'], description="Returns current guild's inventory.", brief='Displays inventory')
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
        msgOut = random.sample(nothingList,1)[0]
    else:
        msgOut = "I have:\n\t○ " + "\n\t○ ".join(deTupledList[0:5])

        if listLen > 5:
            msgOut = msgOut + "\nand, like, " + str(listLen-5) + " other thing"
        if listLen > 6:
            msgOut = msgOut + "s"

    await ctx.send(msgOut)

@bot.command(name = 'whogave', aliases = ['whogaveyou','whogaveu'], description = 'Tells who gave me an item', brief = 'Who gave me a thing?')
async def whogave(ctx, *, item: str):
    donors = db.getItemDonor(ctx.guild.id,item)
    resolvedDonors = []

    if donors == None:
        msgOut = "Something went wrong finding the donor of this item."
    elif len(donors) == 0:
        msgOut = "I don't have that."
    else:
        for donor in donors: resolvedDonors.append('<@!' + donor + '>')
        msgOut = "It was %s" % ' and '.join(resolvedDonors)
    
    await ctx.send(msgOut)
        
######### FACTOID COMMANDS #########
@bot.command(name = 'setfreq', 
            description = """Allows server owner to set frequency of non-command messages that trigger a random factoid.
            Integer provided should be between 0 and 100. 0 disables his random messages and 100 is completely insane.
            Values < 0 will default to 0. Values > 100 will default to 100. Default value if no number provided is 5.
            ONLY THE SERVER ADMIN OR BOT OWNER CAN USE THIS""",
            brief = 'Set frequency of random factoids.')
async def setfreq(ctx, frequency: typing.Optional[int] = DEFAULTPERC):
    user = ctx.message.author.id

    try:
        if str(frequency).isnumeric() and (bot.owner_id == user or ctx.guild.owner_id == user):
            randPerc[ctx.guild.id] = int(frequency)
            msgOut = f"""You're the boss. Frequency for {ctx.guild.name} set to {frequency}%"""
        else:
            msgOut = random.sample(noList,1)[0]
    except Exception as e:
        msgOut = 'Something went wrong setting random frequency'

    await ctx.send(msgOut)

@bot.command(name = 'freq', 
            aliases = ['getfreq'],
            description = """Returns the frequency with which I will respond to non-command messages with random factoids. Number is out of 100.""",
            brief = "Get random frequency of server")
async def freq(ctx):
    msgOut = f"""Frequency for {ctx.guild.name} set to {randPerc[ctx.guild.id]}%"""
    await ctx.send(msgOut)
    

@bot.command(name = 'wtf', aliases = ['what', 'wth'], description = 'Retrieves info on specified factoid or last factoid if no id provided.', brief = 'Retrieve factoid info')
async def wtf(ctx, id: typing.Optional[int] = None):
    fact = db.factInfo(id if id != None else lastFact[ctx.guild.id]) if id == None or str(id).isnumeric() else []

    if fact == None:
        msgOut = f'Something went wrong retrieving fact info for ID {id}'
    elif len(fact) == 0:
        msgOut = """¯\_(ツ)_/¯"""
    else: 
        msgOut = f"""
ID: {str(fact[0])}
Trigger: {fact[1] if fact[1] != None else "*None*"}
Response: {fact[2]}
NSFW: {str(fact[3]==1)}
Deleted: {str(fact[4]==1)}
Creator: {fact[5]}
Created: {fact[6]}
Times Triggered: {fact[7]}
Last Triggered: {fact[8]}
        """
    await ctx.send(msgOut)

@bot.command(name='onrand', 
            aliases = ['onrandnsfw'],
            description="""Give me something random to do/say. Uses the same variables as !on.
            Use !onrandnsfw for nsfw factoids.""", 
            brief = 'Give me something to randomly blurt.')
async def onrand(ctx, *, args: str):
    botCommand = True if args.startswith('!') else False

    if botCommand:
        msgOut = "I'm not remembering bot commands."
    else:
        nsfw = 1 if ctx.invoked_with == 'onnsfwrand' else 0

        success, known = db.addRandFact(args, nsfw, ctx.message.author.display_name, ctx.message.author.id)

        if success:
            msgOut = f"""Ok. I'll randomly say "{args}\""""
        else:
            if known:
                msgOut = 'Oh, I already know that.'
            else:
                msgOut = 'Something went wrong adding this factoid.'

    await ctx.send(msgOut)

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
        msgOut = 'Usage is !on<nsfw> trigger -say response'

    trigger = convertEmote(parts[0]).strip()
    response = ''.join(parts[1:]).strip()
    botCommand = True if trigger.startswith('!') or response.startswith('!') else False
    
    cleanTrigger = mentionToSelfVar(trigger, roleIDs[ctx.guild.id])
    triggerParts = cleanTrigger.split('$self')
    cleanTrigger = '$self'.join(e.strip(string.punctuation).lower() for e in triggerParts).strip()

    if botCommand:
        msgOut = "I'm not remembering bot commands."
    elif len(cleanTrigger) < 4:
        msgOut = 'Trigger must be >= 4 alphanumeric characters'
    else:    
        if trigger.startswith('_') and trigger.endswith('_'):
            cleanTrigger = '_' + trigger + '_'

        nsfw = 1 if ctx.invoked_with == 'onnsfw' else 0

        success, known = db.addFact(cleanTrigger, response, nsfw, ctx.message.author.display_name, ctx.message.author.id)

        if success:
            msgOut = f"""Ok. When I see "{trigger}" I'll say "{response}\""""
        else:
            if known:
                msgOut = 'Oh, I already know that.'
            else:
                msgOut = 'Something went wrong adding this factoid.'

    await ctx.send(msgOut)

bot.run(TOKEN)