import discord
import requests
import asyncio
import json
import parseUtil
import wikipedia
import random
import inspect
import fandom
import re
from discord.ext import commands

class Information(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Information cog loaded")

    @commands.command(name='fandom',
                    description = """Retrieves Fandom summary for the provided search term in the provided wiki, returning the best approximation of the article summary as can be derived from the subpar API.
                    The wikiName arg refers to the fandom site's subdomain, such as "memory-alpha" (memory-alpha.fandom.com) or "minecraft" (minecraft.fandom.com)""",
                    brief = 'Returns Fandom wiki article')
    async def fandom(self, ctx, wikiName, *, searchTerm = None):
        if searchTerm == None:
            await ctx.send("I haven't figured out random articles yet.")
            return
        else:
            try:
                results = fandom.search(searchTerm, wikiName)
                if len(results)==0:
                    await ctx.send(f"""{searchTerm} returned no results from {wikiName}.fandom.com""")
                    return
                else:
                    page = fandom.page(pageid = results[0][1], wiki = wikiName)   
                    url = page.url
                    title = page.title

                    #summary doesn't work right, so I'll parse out the suggestions and quotes from "content"
                    content = re.sub(r'This article is.*\n','', page.content['content'])
                    content = re.sub(r'For.*\n','', page.content['content'])
                    #content = re.sub(r'"[^"]*"\n', '', content)
                    #content = re.sub(rf'{chr(8211)}.*\)\n','',content)

                    #for readability
                    content = re.sub(r"""(?<!["”])\n""",'\n\n', content)

                    if len(content) > 3000: content = content[:(content[:3000].rfind('.')+1)]
                    print(len(content))
            except:
                await ctx.send("Something went wrong, probably that wiki doesn't exist.")
                return

            msgEmbed = discord.Embed(title = f"{title}",
                                    url = f"{url}",
                                    description = f"{content.strip()}",
                                    color = discord.Color.blue())
            msgEmbed.add_field(name = "\u200B", 
                            value = f"""Via [https://{wikiName}.fandom.com](https://{wikiName}.fandom.com)""")

            await ctx.send(embed = msgEmbed)

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
        
        content = re.sub(r'\n','\n\n', page.summary).strip()
        msgEmbed = discord.Embed(title = f"{page.title}",
                            url = f"{page.url}",
                            description = f"{content}",
                            color = discord.Color.blue())

        await ctx.send(embed = msgEmbed)

    @commands.command(name = 'ud', 
                    description = """Retrieves Urban Dictionary definition of search term. Omitting search term returns list of random definitions.
                    The pages of definitions displayed in chat are navigable only by the caller. The bot response will self-destruct after 5 minutes.""", 
                    brief = 'Get Urban Dictionary definition')
    async def ud(self, ctx, *, searchTerm = None):
        st = '' # Spoiler Tags

        if ctx.channel.nsfw == False:
            await ctx.send("This channel is SFW. Urban dictionary... is not.")
            return
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

        #def check(reaction, user):
        #    return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=300, check=check)

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