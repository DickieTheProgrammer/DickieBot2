#!/usr/bin/env python3
#DickieBot: The Impressionable Discord Bot

import os
import discord
import re
import dbFunctions as db

from dotenv import load_dotenv

emoteRegex = [
    # Emotes starting with underscores, retrieve group 3
    re.compile(r"^([_]{1,2}([*]{0,1}|[*]{3})([^_*]*)([*]{0,1}|[*]{3})[_]{1,2})$"),
    # Emotes starting with asterisks, retrieve group 2
    re.compile(r"^([*]{1}|[*]{3})[_]{0,2}([^_*]*)[_]{0,2}([*]{1}|[*]{3})$")

    #re.compile(r"^[_]{1}[^_].+[^-][_]{1}$"),                # _x_, /me converts to this
    #re.compile(r"[*]{1}[^*].+[^*][*]{1}$"),                 # *x*
    #re.compile(r"^[_]{2}[*]{1}[^*].+[^*][*]{1}[_]{2}$"),    # __*x*__
    #re.compile(r"^[*]{1}[_]{2}[^_].+[^_][_]{2}[*]{1}$"),    # *__x__*
    #re.compile(r"^[*]{3}[_]{2}[^_].+[^_][_]{2}[*]{3}$"),    # ***__x__***
    #re.compile(r"^[*]{3}[^*].+[^*][*]{3}$"),                # ***x***
    #re.compile(r"^[_]{2}[*]{3}[^*].+[^*][*]{3}[_]{2}$"),    # __***x***__
    #re.compile(r"^[*]{1}[_]{1}[^_].+[^_][_]{1}[*]{1}$"),    # *_x_*
    #re.compile(r"^[_]{1}[*]{1}[^*].+[^*][*]{1}[_]{1}$"),    # _*x*_
]

def convertEmote(msg):
    if emoteRegex[0].match(msg):
        # Emote starts with underscore
        retMsg = '_' + emoteRegex[0].match(msg).group(3) + '_'
    elif emoteRegex[1].match(msg):
        retMsg = '_' + emoteRegex[1].match(msg).group(2) + '_'
    else:
        retMsg = msg

    return(retMsg)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
DATABASE = os.getenv('DATABASE')

DickieBase = db.Connection(DATABASE)

client = discord.Client()

@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')
    print(f'{client.user} is user')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    #await message.channel.send("""this sends a message""")
    newMessage = convertEmote(message.content)

    print(f'{message}')
    #print(f'{message.content}')
    print(f'{newMessage}')

client.run(TOKEN)

