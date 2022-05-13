import random
import requests
import json
import logging
import typing
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
    async def roll(self, ctx, dice: typing.Optional[str] = None):
        if dice is None:
            await self.bot.invoke("Syntax is !roll {number}d{number}")
            return

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
        aliases=["bug"],
        description="""Submit an issue to bot's GitHub.
        Usage: !issue|bug {title} -b {body}. If -b omitted, all args are body and generic title generated.
        Username appended to title and truncated if exceeding 256 char.
        See GitHub's markdown at https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet.
        Please note offending factoid id if relevant.""",
        brief="Submit a bot issue",
    )
    async def issue(self, ctx, *, issueDesc):
        url = f"https://api.github.com/repos/{self.gh_user}/{self.gh_repo}/issues"
        msgURL = f"https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{ctx.message.id}"
        author = ctx.author.name

        headers = {
            "Authorization": f"token {self.gh_token}",
            "Accept": "application/vnd.github.VERSION.raw+json",
        }

        if "-b" in issueDesc:
            title, body = issueDesc.split("-b")

            # Max title length 256. Appending delimiter and author name with truncation if necessary.
            if len(title) + len(author) + 3 > 256:
                await ctx.send(
                    "Length of title + username exceeds 256 characters. Truncating."
                )
                body = f"Submitted title truncated. Full title: {title}\n\n{body}\n\n{msgURL}"

            title = f"{title[:256-(len(author)+3)]} - {author}"
        else:
            title = f"Issue submitted by {ctx.author.name}"
            body = f"{issueDesc}\n\n{msgURL}"

        issue = {"title": title, "body": body}
        data = json.dumps(issue)
        response = requests.request("POST", url, data=data, headers=headers)
        contentDict = json.loads(response.content)

        if response.status_code == 201:
            await ctx.send(f"""Success: {contentDict["html_url"]}""")
        else:
            await ctx.send(
                f"There was a problem submitting this issue please notify bot admin.\nResponse: {response.status_code}-{response.reason}"
            )
