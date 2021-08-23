#!/usr/bin/env python3
#DickieBot: The Impressionable Discord Bot

import os
import discord
import re
from dbFunctions import Connection

from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE = os.getenv('DATABASE')

db = Connection(DATABASE)

client = discord.Client()
botID = None

emoteRegex = [
    # Emotes starting with underscores, retrieve group 3
    re.compile(r"^([_]{1,2}([*]{0,1}|[*]{3})([^_*]*)([*]{0,1}|[*]{3})[_]{1,2})$"),
    # Emotes starting with asterisks, retrieve group 2
    re.compile(r"^([*]{1}|[*]{3})[_]{0,2}([^_*]*)[_]{0,2}([*]{1}|[*]{3})$")
]

def convertEmote(msg):
    if emoteRegex[0].match(msg):
        # Emote starts with underscore
        msgOut = '_' + emoteRegex[0].match(msg).group(3) + '_'
    elif emoteRegex[1].match(msg):
        # Emote starts with asterisk
        msgOut = '_' + emoteRegex[1].match(msg).group(2) + '_'
    else:
        # Ain't no emote
        msgOut = msg

    return(msgOut)

def parseMsg(msg, user, guild, user_id, discriminator):
    msgOut = None
    
    # Normalize emotes to _<words>_
    msgIn = convertEmote(msg) 

    # Collapse message to one line
    msgIn = re.sub(r'\n',' ',msg) 

    # Convert notification reference to "$self" variable
    myself = '<@!' + str(botID) + '>'
    msgIn = msgIn.replace(myself,'$self') 
    myself = '<@&' + str(botID) + '>'
    msgIn = msgIn.replace(myself,'$self') 

    if msgIn.startswith('_gives $self'):

        # Given Inventory item
        itemRegex = re.compile(r'^[_](?:gives \$self )(.*)[_]$')
        item = itemRegex.match(msgIn).group(1)

        if not db.addToInventory(guild, user, item, user_id, discriminator):
            msgOut = 'something went wrong'
        else:
            msgOut = '_added %s to his inventory_' % item

    return(msgOut)

@client.event
async def on_ready():
    global botID
    botID = client.user.id
    print(f'{client.user.name} has connected to Discord!')
    print(f'{client.user} is user')
    print(f'{botID}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    msgToSend = parseMsg(message.content, message.author.display_name, message.guild.id, message.author.id, message.author.discriminator)

    if msgToSend != None:
        await message.channel.send(msgToSend)
    #await message.channel.send("""this sends a message""")

    #print(f'{message}')
    #print(f'{message.content}')

client.run(TOKEN)

