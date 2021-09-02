import discord
import requests
import asyncio
import json
import parseUtil
import wikipedia
import random
import inspect
from discord.ext import commands

class Information(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Information cog loaded")

    @commands.command(name = 'wiki',
                    description = """Retrieves Wikipedia summary for the provided search term. Omitting search term returns random article summary.""",
                    brief = 'Get Wikipedia article summary')
    async def wiki(self, ctx, *, searchTerm = None):
        if searchTerm == None:
            page = wikipedia.page(wikipedia.random(pages=1))
        else:
            try:
                page = wikipedia.page(searchTerm)
            except wikipedia.DisambiguationError as e:
                choice = random.choice(e.options)
                print(f"""wiki "{searchTerm}"" didn't work, trying {choice}""")
                page = wikipedia.page(choice)
            except Exception as e:
                print(inspect.stack()[0][3])
                print(inspect.stack()[1][3])
                print(e)
                return
        
        msgEmbed = discord.Embed(title = f"{page.title}",
                            url = f"{page.url}",
                            description = f"{page.summary}",
                            color = discord.Color.blue())

        await ctx.send(embed = msgEmbed)

    @commands.command(name = 'ud', 
                    description = """Retrieves Urban Dictionary definition of search term. Omitting search term returns list of random definitions.
                    The pages of definitions displayed in chat are navigable only by the caller and will eventually self-destruct after 60s of inactivity.""", 
                    brief = 'Get Urban Dictionary definition')
    async def ud(self, ctx, *, searchTerm = None):
        st = '' # Spoiler Tags

        if ctx.channel.nsfw == False:
            #await ctx.send("This channel is SFW. Urban dictionary... is not.")
            #return
            st = "||"

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
        
        if response.content == """{"error":404}""":
            await ctx.send(f'Response code 404 for <{URL}>')
            return

        results = json.loads(response.content)["list"]

        pages = len(results)
        curPage = 1

        for rec in range(pages):
            contents.append({
                "definition": f"{st}{results[rec-1]['definition']}{st}",
                "word": f"{st}{results[rec-1]['word']}{st}",
                "permalink": f"{results[rec-1]['permalink']}",
                "example": f"{st}{results[rec-1]['example']}{st}"
            })

        msgEmbed = discord.Embed(title = f"{contents[curPage-1]['word']}",
                            url = f"{contents[curPage-1]['permalink']}",
                            description = parseUtil.convertLinkMarkdown(f"{contents[curPage-1]['definition']}"),
                            color = discord.Color.blue())
        msgEmbed.add_field(name = "Example",
                        value = parseUtil.convertLinkMarkdown(f"{contents[curPage-1]['example']}"),
                        inline = False)
        msgEmbed.set_footer(text=f"""Page {curPage} of {pages}. {'Spoiler tags for SFW channel' if st else ''}""")
        
        message = await ctx.send(embed = msgEmbed)

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
                            description = parseUtil.convertLinkMarkdown(f"{contents[curPage-1]['definition']}"),
                            color = discord.Color.blue())
                    msgEmbed.add_field(name = "Example",
                                    value = parseUtil.convertLinkMarkdown(f"{contents[curPage-1]['example']}"),
                                    inline = False)  
                    msgEmbed.set_footer(text=f"""Page {curPage} of {pages}. {'Spoiler tags for SFW channel' if st else ''}""")

                    await message.edit(embed = msgEmbed)
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and curPage > 1:
                    curPage -= 1

                    msgEmbed = discord.Embed(title = f"{contents[curPage-1]['word']}",
                            url = f"{contents[curPage-1]['permalink']}",
                            description = parseUtil.convertLinkMarkdown(f"{contents[curPage-1]['definition']}"),
                            color = discord.Color.blue())
                    msgEmbed.add_field(name = "Example",
                                    value = parseUtil.convertLinkMarkdown(f"{contents[curPage-1]['example']}"),
                                    inline = False)     
                    msgEmbed.set_footer(text=f"""Page {curPage} of {pages}. {'Spoiler tags for SFW channel' if st else ''}""")
                                                    
                    await message.edit(embed = msgEmbed)
                    await message.remove_reaction(reaction, user)

                else:
                    await message.remove_reaction(reaction, user)
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page
            except asyncio.TimeoutError:
                await message.delete()
                break