import discord
import requests
import asyncio
import json

# import wikipedia
# import random
import fandom
import re
import pyowm
import logging
from discord.ext import commands


class Information(commands.Cog):
    def __init__(self, bot, apiKey):
        self.bot = bot

        try:
            self.owm = pyowm.OWM(apiKey)
        except Exception as e:  # noqa: F841
            self.owm = None
            self.mgr = None
            logging.exception("Exception occurred.")

    def fandomRedirect(self, subdomain):
        redirectSubdomain = None
        r = requests.get(f"http://{subdomain}.fandom.com")
        if r.status_code == 200:
            redirectSubdomain = re.search(r"^https://(.*)\.fandom.*$", r.url).group(1)

        return redirectSubdomain

    def convertLinkMarkdown(self, msgIn):
        searchResults = re.findall(r"\[.+?\]", msgIn)
        links = []
        msgOut = msgIn

        if len(searchResults) > 0:
            links = list(set(searchResults))
            for i in links:
                msgOut = msgOut.replace(
                    i,
                    i
                    + f"""(https://www.urbandictionary.com/define.php?term={i.strip('[').strip(']').replace(' ','%20')})""",
                )

        return msgOut

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("Information cog loaded")

    @commands.command(
        name="weather",
        description="""Get the weather at a given location, default 'Huntsville, AL'""",
        brief="Get the weather at a location",
    )
    async def weather(self, ctx, *, location="Huntsville, AL, US"):
        if not self.owm:
            await ctx.send("OWM Weather Not Connected")
            return

        try:
            mgr = self.owm.weather_manager()
            try:
                observation = mgr.weather_at_place(location)
            except:  # noqa: E722
                observation = mgr.weather_at_place(location + ", US")
            weather = observation.weather
            resolvedLoc = (
                observation.to_dict()["location"]["name"]
                + ", "
                + observation.to_dict()["location"]["country"]
            )
            status = weather.detailed_status
            td = weather.temperature("fahrenheit")
            temp = f"""{td['temp']}, feels like {td['feels_like']}"""
            humidity = f"""{weather.humidity}%"""
        except:  # noqa: E722
            await ctx.send(f"Unable to retrieve weather information from {location}")
            return

        msgEmbed = discord.Embed(
            title=f"Current weather for {resolvedLoc}",
            description=f"Status: {status}\nTemp: {temp}\nHumidity: {humidity}",
            color=discord.Color.blue(),
        )
        msgEmbed.add_field(
            name="\u200B",
            value="""Via [https://openweathermap.org/](https://openweathermap.org/)""",
        )
        await ctx.send(embed=msgEmbed)

    @commands.command(
        name="fandom",
        description="""Retrieves Fandom summary for the provided search term in the provided wiki, returning the best approximation of the article summary as can be derived from the subpar API.
                    The wikiName arg refers to the fandom site's subdomain, such as "memory-alpha" (memory-alpha.fandom.com) or "minecraft" (minecraft.fandom.com)""",
        brief="Returns Fandom wiki article",
    )
    async def fandom(self, ctx, wikiName, *, searchTerm=None):
        subdomain = self.fandomRedirect(wikiName)

        if subdomain is None:
            await ctx.send(f"""Subdomain {wikiName} not found.""")
            return

        if searchTerm is None:
            r = requests.get(f"""https://{subdomain}.fandom.com/Special:Random""")
            searchTerm = r.url.strip(f"""https://{subdomain}.fandom.com/wiki/""")

        try:
            results = fandom.search(searchTerm, subdomain)
            if len(results) == 0:
                await ctx.send(
                    f"""{searchTerm} returned no results from {subdomain}.fandom.com"""
                )
                return
            else:
                page = fandom.page(pageid=results[0][1], wiki=subdomain)
                url = page.url
                title = page.title

                # summary doesn't work right, so I'll parse out the suggestions from "content"
                content = re.sub(r"This article is.*\n", "", page.content["content"])
                content = re.sub(r"For.*\n", "", page.content["content"])

                # for readability
                content = re.sub(r"""(?<!["”])\n""", "\n\n", content)

                if len(content) > 3000:
                    content = content[: (content[:3000].rfind(".") + 1)]
        except:  # noqa: E722
            await ctx.send("Something went wrong, probably that wiki doesn't exist.")
            return

        msgEmbed = discord.Embed(
            title=f"{title}",
            url=f"{url}",
            description=f"{content.strip()}",
            color=discord.Color.blue(),
        )
        msgEmbed.add_field(
            name="\u200B",
            value=f"""Via [https://{subdomain}.fandom.com](https://{subdomain}.fandom.com)""",
        )

        await ctx.send(embed=msgEmbed)

    #    @commands.command(
    #        name="wiki",
    #        description="""Retrieves Wikipedia summary for the provided search term. Omitting search term returns random article summary.""",
    #        brief="Get Wikipedia article summary",
    #    )
    #    async def wiki(self, ctx, *, searchTerm=None):
    #        if searchTerm is None:
    #            page = wikipedia.page(wikipedia.random(pages=1))
    #        else:
    #            try:
    #                page = wikipedia.page(searchTerm)
    #            except wikipedia.DisambiguationError as e:
    #                choice = random.choice(e.options)
    #                logging.info(f"""wiki "{searchTerm}"" didn't work, trying {choice}""")
    #                page = wikipedia.page(choice)
    #            except Exception as e:  # noqa: F841
    #                logging.exception("Exception occurred")
    #
    #                await ctx.send(f"No article found for '{searchTerm}'.")
    #
    #                return
    #
    #        content = re.sub(r"\n", "\n\n", page.summary).strip()
    #        msgEmbed = discord.Embed(
    #            title=f"{page.title}",
    #            url=f"{page.url}",
    #            description=f"{content}",
    #            color=discord.Color.blue(),
    #        )
    #
    #        await ctx.send(embed=msgEmbed)

    @commands.command(
        name="ud",
        description="""Retrieves Urban Dictionary definition of search term. Omitting search term returns list of random definitions.
                    The pages of definitions displayed in chat are navigable only by the caller.""",
        brief="Get Urban Dictionary definition",
    )
    async def ud(self, ctx, *, searchTerm=None):
        st = ""  # Spoiler Tags

        if ctx.channel.nsfw is False:
            st = "||"

        URL = """https://api.urbandictionary.com/v0/"""
        contents = []

        if searchTerm is None:
            URL = URL + """random"""
        else:
            URL = URL + f"""define?term={searchTerm}"""

        response = requests.get(URL)

        if response.status_code != 200:
            await ctx.send(f"Response code {response.status_code} for <{URL}>")
            return

        if response.content == """{"error":404}""":
            await ctx.send(f"Response code 404 for <{URL}>")
            return

        results = json.loads(response.content)["list"]

        pages = len(results)
        curPage = 1

        for rec in range(pages):
            contents.append(
                {
                    "definition": f"{st}{results[rec-1]['definition']}{st}",
                    "word": f"{st}{results[rec-1]['word']}{st}",
                    "permalink": f"{results[rec-1]['permalink']}",
                    "example": f"{st}{results[rec-1]['example'] if results[rec-1]['example'] else 'No example provided.'}{st}",
                }
            )

        msgEmbed = discord.Embed(
            title=f"{contents[curPage-1]['word']}",
            url=f"{contents[curPage-1]['permalink']}",
            description=self.convertLinkMarkdown(
                f"{contents[curPage-1]['definition']}"
            ),
            color=discord.Color.blue(),
        )
        msgEmbed.add_field(
            name="Example",
            value=self.convertLinkMarkdown(f"{contents[curPage-1]['example']}"),
            inline=False,
        )
        msgEmbed.set_footer(
            text=f"""Page {curPage} of {pages}. {'Spoiler tags for SFW channel' if st else ''}"""
        )

        message = await ctx.send(embed=msgEmbed)

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]

        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", check=check)

                if str(reaction.emoji) == "▶️" and curPage != pages:
                    curPage += 1

                    msgEmbed = discord.Embed(
                        title=f"{contents[curPage-1]['word']}",
                        url=f"{contents[curPage-1]['permalink']}",
                        description=self.convertLinkMarkdown(
                            f"{contents[curPage-1]['definition']}"
                        ),
                        color=discord.Color.blue(),
                    )
                    msgEmbed.add_field(
                        name="Example",
                        value=self.convertLinkMarkdown(
                            f"{contents[curPage-1]['example']}"
                        ),
                        inline=False,
                    )
                    msgEmbed.set_footer(
                        text=f"""Page {curPage} of {pages}. {'Spoiler tags for SFW channel' if st else ''}"""
                    )

                    await message.edit(embed=msgEmbed)
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and curPage > 1:
                    curPage -= 1

                    msgEmbed = discord.Embed(
                        title=f"{contents[curPage-1]['word']}",
                        url=f"{contents[curPage-1]['permalink']}",
                        description=self.convertLinkMarkdown(
                            f"{contents[curPage-1]['definition']}"
                        ),
                        color=discord.Color.blue(),
                    )
                    msgEmbed.add_field(
                        name="Example",
                        value=self.convertLinkMarkdown(
                            f"{contents[curPage-1]['example']}"
                        ),
                        inline=False,
                    )
                    msgEmbed.set_footer(
                        text=f"""Page {curPage} of {pages}. {'Spoiler tags for SFW channel' if st else ''}"""
                    )

                    await message.edit(embed=msgEmbed)
                    await message.remove_reaction(reaction, user)

                else:
                    await message.remove_reaction(reaction, user)
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page
            except asyncio.TimeoutError:
                await message.delete()
                break
