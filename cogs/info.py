import discord
import requests
import asyncio
import json

from discord.ext import commands

class Information(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Information cog loaded")

    @commands.command(name = 'ud', 
                    description="Retrieves Urban Dictionary definition of search term. Omitting search term returns list of random definitions.", 
                    brief='Get Urban Dictionary definition')
    async def ud(self, ctx, *, searchTerm = None):

        if ctx.channel.nsfw == False:
            await ctx.send("This channel is SFW. Urban dictionary... is not.")
            return

        URL = """https://api.urbandictionary.com/v0/"""
        contents = []

        if searchTerm == None:
            URL = URL + """random"""
        else:
            URL = URL + f"""define?term={searchTerm}"""

        response = requests.get(URL)

        if response.status_code != 200:
            await ctx.send(f'Response code {response.status_code} for <{URL}>')
            return
        
        results = json.loads(response.content)["list"]

        pages = len(results)
        print(pages)
        curPage = 1

        for rec in range(pages):
            contents.append({
                "definition": f"{results[rec-1]['definition']}",
                "word": f"{results[rec-1]['word']}",
                "permalink": f"{results[rec-1]['permalink']}",
                "example": f"{results[rec-1]['example']}"
            })

        msgEmbed = discord.Embed(title = f"{contents[curPage-1]['word']}",
                            url = f"{contents[curPage-1]['permalink']}",
                            description = f"{contents[curPage-1]['definition']}",
                            color = discord.Color.blue())
        msgEmbed.add_field(name = "Example",
                        value = f"{contents[curPage-1]['example']}",
                        inline = False)
        
        message = await ctx.send(embed=msgEmbed)

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=check)

                if str(reaction.emoji) == "▶️" and curPage != pages:
                    curPage += 1

                    msgEmbed = discord.Embed(title = f"{contents[curPage-1]['word']}",
                            url = f"{contents[curPage-1]['permalink']}",
                            description = f"{contents[curPage-1]['definition']}",
                            color = discord.Color.blue())
                    msgEmbed.add_field(name = "Example",
                                    value = f"{contents[curPage-1]['example']}",
                                    inline = False)   

                    await message.edit(embed=msgEmbed)
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and curPage > 1:
                    curPage -= 1

                    msgEmbed = discord.Embed(title = f"{contents[curPage-1]['word']}",
                            url = f"{contents[curPage-1]['permalink']}",
                            description = f"{contents[curPage-1]['definition']}",
                            color = discord.Color.blue())
                    msgEmbed.add_field(name = "Example",
                                    value = f"{contents[curPage-1]['example']}",
                                    inline = False)    
                                                    
                    await message.edit(embed=msgEmbed)
                    await message.remove_reaction(reaction, user)

                else:
                    await message.remove_reaction(reaction, user)
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page
            except asyncio.TimeoutError:
                await message.delete()
                break