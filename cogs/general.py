import random
import requests
import json
import logging
from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot, GH_user, GH_token, GH_repo):
        self.bot = bot
        self.gh_user = GH_user
        self.gh_token = GH_token
        self.gh_repo = GH_repo
        self.src = f"https://github.com/{self.gh_user}/{self.gh_repo}"

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("General cog loaded")

    @commands.command(
        name="roll",
        description="Simulates dice rolls. Syntax is !roll {number}d{number}.",
        brief="Rolls dem bones - {number}d{number}",
    )
    async def roll(self, ctx, dice: str):
        # Rolls a dice in NdN format.
        try:
            rolls, limit = map(int, dice.split("d"))
        except Exception:
            await ctx.send("Format has to be in {number}**d**{number}")
            return

        if rolls > 25:
            msgOut = "Max 25 dice"
        elif rolls <= 0 or limit <= 0:
            msgOut = "Positive numbers only"
        elif limit > 999999:
            msgOut = "Max 999999-sided die"
        else:
            results = []
            for r in range(rolls):
                results.append(random.randint(1, limit))
            msgOut = ", ".join(str(r) for r in results) + f"\n\nTotal: {sum(results)}"

        await ctx.send(msgOut)

    @commands.command(
        name="src",
        aliases=["source", "sauce"],
        description="Returns GitHub source URL.",
        brief="Returns source URL",
    )
    async def source(self, ctx):
        await ctx.send(f"<{self.src}>")

    @commands.command(
        name="issue",
        aliases=['bug'],
        description="Submit an issue to bot's GitHub",
        brief="Submit a bot issue"
    )
    async def issue(self, ctx, *, issue_desc):
        url = f"https://api.github.com/repos/{self.gh_user}/{self.gh_repo}/issues"

        headers = {"Authorization": f"token {self.gh_token}",
                    "Accept": "application/vnd.github.VERSION.raw+json"}

        title = f"Issue submitted by {ctx.author.name}"
        body = f"{issue_desc}\n\nhttps://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}"

        issue = {"title": title,
                "body": body
                }
        data = json.dumps(issue)
        
        response = requests.request("POST", url, data = data, headers = headers)

        contentDict = json.loads(response.content)

        if response.status_code == 201:
            await ctx.send(f"""Success: {contentDict["html_url"]}""")
        else:
            await ctx.send(f"There was a problem submitting this issue.\nResponse: {response.status_code}-{response.reason}")
