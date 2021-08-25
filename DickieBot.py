#!/usr/bin/env python3
#DickieBot: The Impressionable Discord Bot

import os
import discord
import re
import random

from discord import member, utils

from dbFunctions import Connection
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE = os.getenv('DATABASE')
intents = discord.Intents.all()

db = Connection(DATABASE)
bot = commands.Bot(command_prefix='!')

botID = None
botName = None

roleIDs = {}

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
    else:
        # Ain't no emote
        msgOut = msg

    return(msgOut)

def parseMsg(msg, user, guild, user_id, discriminator):
    msgOut = None
    
    # Standardize emotes to _<words>_
    msgIn = convertEmote(msg) 

    # Collapse message to one line
    msgIn = re.sub(r'\n',' ',msg) 

    # Convert notification reference to "$self" variable
    # Nick ping
    nick = '<@!' + str(botID) + '>'
    msgIn = msgIn.replace(nick,'$self') 
    # Role ping
    role = '<@&' + str(roleIDs[guild]) + '>'
    msgIn = msgIn.replace(role,'$self') 
    print (msgIn)
    print(roleIDs[guild])

    if msgIn.startswith('_gives $self'):

        # Given Inventory item
        itemRegex = re.compile(r'^_{1}(?:gives \$self )(.*)_{1}$')
        item = itemRegex.match(msgIn).group(1)

        if not db.addToInventory(guild, user, item, user_id, discriminator):
            msgOut = 'something went wrong'
        else:
            msgOut = '_added %s to his inventory_' % item

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
    print(f'{botID}')

@bot.event
async def on_guild_join(guild):
    guildRole = member.get(guild.roles,name=botName).id
    global roleIDs
    roleIDs[guild.id]=guildRole

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    print(f'{message.content}')

    msgToSend = parseMsg(message.content, message.author.display_name, message.guild.id, message.author.id, message.author.discriminator)

    if msgToSend != None:
        await message.channel.send(msgToSend)

    await bot.process_commands(message)

@bot.command(name = 'source')
async def source(ctx):
    await ctx.send("https://github.com/DickieTheProgrammer/DickieBot2")

@bot.command(name = 'inv', aliases=['inventory','stuff'])
# add @commands.cooldown(2, 20, commands.BucketType.user) here?
async def inv(ctx):
    print(ctx.guild.id)
    itemList = db.getInventory(ctx.guild.id)

    if itemList == None:
        await ctx.send("Something went wrong fetching inventory.")
        return

    deTupledList = [' '.join(elem) for elem in itemList]

    listLen = len(deTupledList)
    if listLen == 0:
        msgToSend = random.sample(nothingList,1)[0]
    else:
        msgToSend = "I have:\n\t○ " + "\n\t○ ".join(deTupledList[0:5])

        if listLen > 5:
            msgToSend = msgToSend + "\nand, like, " + str(listLen-5) + " other thing"
        if listLen > 6:
            msgToSend = msgToSend + "s"

    print(msgToSend)
    await ctx.send(msgToSend)

@bot.command(name = 'roll')
async def roll(ctx, dice: str):
    # Rolls a dice in NdN format. 
    try:
        rolls, limit = map(int, dice.split('d'))
    except Exception:
        await ctx.send('Format has to be in \{number\}**d**\{number\}')
        return

    if rolls>25:
        msgToSend = 'Max 25 dice'
    elif rolls <= 0 or limit <= 0:
        msgToSend = 'Positive numbers only'
    else:
        msgToSend = ', '.join(str(random.randint(1, limit)) for r in range(rolls))

    await ctx.send(msgToSend)

bot.run(TOKEN)

