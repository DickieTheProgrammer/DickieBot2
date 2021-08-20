#!/usr/bin/env python3
#DickieBot: The Impressionable Discord Bot

import os
import discord

from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()

@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    #await message.channel.send('this sends a message')

    print(f'{message}')
    print(f'{message.content}')

client.run(TOKEN)