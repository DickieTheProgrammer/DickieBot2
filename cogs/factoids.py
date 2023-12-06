import typing
import random
import string
import asyncio
import math
import time
import dbFunctions
import parseUtil
import discord
import logging
from discord.ext import commands

DEFAULTPERC = 5


class Factoids(commands.Cog):
    def __init__(
        self, bot, db: dbFunctions.Connection, owner, match_anywhere_by_default
    ):
        self.bot = bot
        self.db = db
        self.owner = owner
        self.match_anywhere_by_default = match_anywhere_by_default

        self.noList = [
            "https://c.tenor.com/2yJBnYOY_j8AAAAC/tonton-tonton-sticker.gif",
            "https://c.tenor.com/UIrQocNe4xYAAAAM/no-no-no-way.gif",
            "https://c.tenor.com/U9oGKTRaBo0AAAAM/bugs-bunny-bunny.gif",
            "https://c.tenor.com/xAyrbho-SPEAAAAM/bachelor-mattjames.gif"
            "https://c.tenor.com/28WY5uWjdv0AAAAM/nope-sloth.gif",
            "https://giphy.com/embed/daPCSjwus6UR2JxRX1",
            "https://giphy.com/embed/3ov9jLsBqPh6rjuHuM",
            "https://giphy.com/embed/VgqtLbNtJEWtVlfMVv",
            "https://giphy.com/embed/QIPEV0HWAiXVm",
            "https://giphy.com/embed/XymaJlgorUL8vOfF88",
        ]

    @commands.Cog.listener()
    async def on_ready(self):
        logging.info("Factoids cog loaded")

    @commands.command(
        name="setfreq",
        description="""Allows server owner to set frequency of non-command messages that trigger a random factoid.
                Integer provided should be between 0 and 100. 0 disables his random messages and 100 is completely insane.
                Values < 0 will default to 0. Values > 100 will default to 100. Default value if no number provided is 5.
                ONLY THE SERVER ADMIN OR BOT OWNER CAN USE THIS""",
        brief="Set frequency of random factoids.",
    )
    async def setfreq(self, ctx, frequency: typing.Optional[int] = DEFAULTPERC):
        user = ctx.message.author.id

        try:
            if self.owner == str(user) or ctx.guild.owner_id == user:
                self.db.updateFreq(ctx.guild.id, frequency, ctx.channel.id)
                msgOut = f"""You're the boss. Frequency for {ctx.channel.name} set to {frequency}%"""
            else:
                msgOut = random.sample(self.noList, 1)[0]
        except:  # noqa: E722
            msgOut = "Something went wrong setting random frequency"

        await ctx.send(msgOut)

    @commands.command(
        name="freq",
        aliases=["getfreq"],
        description="""Returns the frequency with which I will respond to non-command messages with random factoids. Number is out of 100.""",
        brief="Get random frequency of server",
    )
    async def freq(self, ctx):
        msgOut = f"""Random frequency for {ctx.channel.name} set to {self.db.getFreq(ctx.guild.id, ctx.channel.id)}%"""
        await ctx.send(msgOut)

    @commands.command(
        name="delete",
        aliases=["del", "undel", "undelete", "delfact", "undelfact"],
        description="Sets deleted flag on factoid. !delete and !undelete on specified factoid or most recent triggered factoid if none specified.",
        brief="or !undelete, sets deleted/undeleted",
    )
    async def delfact(self, ctx, id=None):
        if id is not None and not id.isnumeric():
            await ctx.send("This is not a valid factoid ID")
            return

        fact = (
            self.db.factInfo(
                id
                if id is not None
                else self.db.getLastFactID(ctx.guild.id, ctx.channel.id)
            )
            if id is None or str(id).isnumeric()
            else []
        )

        delDesc = (
            "delete" if ctx.invoked_with in ["delete", "del", "delfact"] else "undelete"
        )
        delNum = 1 if ctx.invoked_with in ["delete", "del", "delfact"] else 0

        if fact is None:
            msgOut = f"Something went wrong trying to {delDesc} fact ID {fact[0]}" ""
        elif len(fact) == 0:
            msgOut = f"Couldn't find fact ID {fact[0]}"
        else:
            result, changed = self.db.delFact(
                fact[0], ctx.message.author.name, ctx.message.author.id, delNum
            )
            if not result:
                if not changed:
                    msgOut = f"ID {fact[0]} already {delDesc}d."
                else:
                    msgOut = (
                        f"Something went wrong trying to {delDesc} fact ID {fact[0]}" ""
                    )
            else:
                msgOut = f"Fact with ID {fact[0]} has been marked {delDesc}d."

        await ctx.send(msgOut)

    @commands.command(
        name="wtf",
        aliases=["what", "wth"],
        description="""Retrieves info on specified factoid or last factoid if no id provided.""",
        brief="Retrieve factoid info",
    )
    async def wtf(self, ctx, id: typing.Optional[int] = None):
        fact = (
            self.db.factInfo(
                id
                if id is not None
                else self.db.getLastFactID(ctx.guild.id, ctx.channel.id)
            )
            if id is None or str(id).isnumeric()
            else []
        )

        if fact is None:
            msgOut = f"Something went wrong retrieving fact info for ID {id}"
            await ctx.send(msgOut)
        elif len(fact) == 0:
            msgOut = r"""¯\_(ツ)_/¯"""
            await ctx.send(msgOut)
        else:
            # spoiler tag
            st = "||" if fact[3] == 1 and not ctx.channel.is_nsfw else ""

            msgEmbed = discord.Embed(
                title=f"{fact[0]}{' (Reaction)' if fact[9] == 1 else ''}",
                description=parseUtil.escapeFormatting(
                    f"""Trigger: {st}{fact[1] if fact[1] != None else "*None*"}{st}\nResponse: {st}{fact[2]}{st}\nNSFW: {str(fact[3]==1)}\nDeleted: {str(fact[4]==1)}\nCreator: {fact[5]}\nCreated: {fact[6]}\nTimes Triggered: {fact[7]}\nLast Triggered: {fact[8]}"""
                ),
                color=discord.Color.blue(),
            )
            msgEmbed.set_footer(
                text=f"""{'Spoiler tags for SFW channel' if st else ''}"""
            )

            await ctx.send(embed=msgEmbed)

            def check(reaction, user):
                return False

    @commands.command(
        name="onrand",
        aliases=["onrandnsfw"],
        description="""Give me something random to do/say. Uses the same variables as !on.\nUse !onrandnsfw for nsfw factoids.""",
        brief="Give me something to randomly blurt.",
    )
    async def onrand(self, ctx, *, args: str = None):
        if args is None:
            await ctx.send(
                "Usage is !onrand <thing to say>. Be mindful of discord markdown."
            )
            return

        botCommand = True if args.startswith("!") else False

        if botCommand:
            msgOut = "I'm not remembering bot commands."
        else:
            nsfw = 1 if ctx.invoked_with == "onrandnsfw" else 0

            success, known, id, deleted = self.db.addRandFact(
                args, nsfw, ctx.message.author.name, ctx.message.author.id
            )

            if success:
                msgOut = f"""Ok. I'll randomly say "{args}\"\n(ID: {id})"""
            else:
                if known:
                    if deleted:
                        msgOut = (
                            f"""I've undeleted id {id} which matched this factoid."""
                        )
                    else:
                        msgOut = f"""Oh, I already know that. It's ID {id}."""
                else:
                    msgOut = "Something went wrong adding this factoid."

        await ctx.send(msgOut)

    @commands.command(
        name="mod",
        aliases=["modfact", "modthat"],
        description="""
                    Allows you to modify a factoid response by providing a substitution regex formatted s/pattern/replacement
                    !mod <id> {-t|r} {substitution string}, if id blank, updates last called factoid; if t/r option omitted, defaults to response update""",
        brief="Modify factoid response",
    )
    async def mod(self, ctx, id: typing.Optional[int] = 0, *, regEx):
        lastID = self.db.getLastFactID(ctx.guild.id, ctx.channel.id) if id == 0 else id

        if regEx.startswith("-"):
            cleanRegEx = regEx[2:].strip()
            subType = regEx[1].lower()
        else:
            cleanRegEx = regEx
            subType = "r"

        try:
            if cleanRegEx.endswith("//"):
                s, pattern = cleanRegEx.strip("/").split("/")
                repl = ""
            else:
                s, pattern, repl = cleanRegEx.strip("g").strip("/").split("/")
        except:  # noqa: E722
            await ctx.send(
                "Syntax is !mod <id> {substitution string in form s/pattern/replacement}"
            )
            return

        results = self.db.modFact(
            lastID,
            pattern,
            repl,
            ctx.message.author.name,
            ctx.message.author.id,
            subType,
        )

        # results returned list = [success, known, matched, valid, changed, oldResp/Trig, newResp/Trig]
        if not results[1]:
            msgOut = f"Fact ID {lastID} not found."
        elif not results[2]:
            msgOut = f"""Pattern "{pattern}" not found in {'response' if subType == 'r' else 'trigger'} for factoid ID {lastID}."""
        elif not results[3]:
            msgOut = "Invalid replacement. Trigger too short, response a command, or trying to convert to/from random factoid."
        elif not results[4]:
            msgOut = """Message wasn't changed by this substitution."""
        elif not results[0]:
            msgOut = f"Something went wrong modifying fact id {lastID}"
        else:
            msgOut = f"Successfully changed fact {lastID} {'response' if subType == 'r' else 'trigger'} from\n{results[5]}\nto\n{results[6]}"

        await ctx.send(msgOut)

    @commands.command(
        name="nsfw",
        aliases=["sfw"],
        description="Sets NSFW flag on factoid record. !nsfw for true, !sfw for false",
        brief="or !sfw, mark factoid NSFW/SFW",
    )
    async def nsfw(self, ctx, id: typing.Optional[int] = 0):

        lastID = self.db.getLastFactID(ctx.guild.id, ctx.channel.id) if id == 0 else id
        valueNSFW = 1 if ctx.invoked_with == "nsfw" else 0

        success, changed = self.db.toggleNSFW(lastID, valueNSFW)

        descNSFW = "NSFW" if ctx.invoked_with == "nsfw" else "SFW"

        if not success:
            msgOut = f"""Something went wrong marking {lastID} as {descNSFW}."""
        elif not changed:
            msgOut = f"""ID {lastID} already marked {descNSFW}."""
        else:
            msgOut = f"""Successfully set ID {lastID} as {descNSFW}."""

        await ctx.send(msgOut)

    @commands.command(
        name="on",
        aliases=["onnsfw"],
        description="""Assign a response to triggering phrase. !on<nsfw> {{trigger}} -say|-react {{response}}.
                    Using !onnsfw marks the response as NSFW and will not be triggered in SFW channels.
                    Use $self to refer to the bot in the trigger. i.e. !on "Hi $self" -say Hello.
                    Use $rand, $nick, and $item in response to sub in a random user, the triggering user, and an inventory item, respectively.
                    $item consumes the inventory item.
                    Using -react will expect a single emoji as the response arg. All reactions are SFW.""",
        brief="Teach me to respond to something",
    )
    async def on(self, ctx, *, args):  # noqa: C901
        usage = "Usage is !on<nsfw> trigger -say|react response."

        if args.find("-say") > 0:
            parts = args.split("-say")
            if len(parts) <= 1:
                msgOut = usage
                await ctx.send(msgOut)

            trigger = parseUtil.convertEmote(parts[0]).strip()
            response = "".join(parts[1:]).strip()
            botCommand = (
                True if trigger.startswith("!") or response.startswith("!") else False
            )

            cleanTrigger = parseUtil.mentionToSelfVar(
                trigger,
                self.db.getBotRole(ctx.guild.id, ctx.channel.id),
                self.bot.user.id,
            )
            triggerParts = cleanTrigger.split("$self")
            cleanTrigger = "$self".join(
                e.translate(str.maketrans(dict.fromkeys(string.punctuation))).lower()
                for e in triggerParts
            ).strip()

            if botCommand:
                msgOut = "I'm not remembering bot commands."
            elif len(cleanTrigger) < 4:
                msgOut = "Trigger must be >= 4 alphanumeric characters."
            else:
                if trigger.startswith("_") and trigger.endswith("_"):
                    cleanTrigger = "_" + cleanTrigger + "_"

                nsfw = 1 if ctx.invoked_with == "onnsfw" else 0

                success, known, id, deleted = self.db.addFact(
                    cleanTrigger,
                    response,
                    nsfw,
                    ctx.message.author.name,
                    ctx.message.author.id,
                    0,
                    self.match_anywhere_by_default,
                )

                if success:
                    msgOut = f"""Ok. When I see "{trigger}" I'll say "{response}\"\n(ID: {id})"""
                else:
                    if known:
                        if deleted:
                            msgOut = f"""I've undeleted id {id} which matched this factoid."""
                        else:
                            msgOut = f"""Oh, I already know that. It's ID {id}."""
                    else:
                        msgOut = "Something went wrong adding this factoid."

        elif args.find("-react") > 0:
            parts = args.split("-react")

            if len(parts) <= 1:
                msgOut = usage
                await ctx.send(msgOut)
                return

            trigger = parseUtil.convertEmote(parts[0]).strip()
            reaction = parts[1].strip()
            if len(reaction) == 0:
                msgOut = usage
                await ctx.send(msgOut)
                return

            botCommand = True if trigger.startswith("!") else False

            cleanTrigger = parseUtil.mentionToSelfVar(
                trigger,
                self.db.getBotRole(ctx.guild.id, ctx.channel.id),
                self.bot.user.id,
            )
            triggerParts = cleanTrigger.split("$self")
            cleanTrigger = "$self".join(
                e.translate(str.maketrans(dict.fromkeys(string.punctuation))).lower()
                for e in triggerParts
            ).strip()

            if botCommand:
                msgOut = "I'm not remembering bot commands."
            elif len(cleanTrigger) < 4:
                msgOut = "Trigger must be >= 4 alphanumeric characters."
            else:
                try:
                    await ctx.message.add_reaction(parts[1].strip())
                except Exception as e:  # noqa: F841
                    logging.exception("Exception occurred.")
                    await ctx.send("Invalid emoji... I think")
                    return

                success, known, id, deleted = self.db.addFact(
                    trigger,
                    reaction,
                    0,
                    ctx.message.author.name,
                    ctx.message.author.id,
                    1,
                    self.match_anywhere_by_default,
                )

                if success:
                    msgOut = f"""Ok. When I see "{trigger}" I'll do a "{reaction}\"\n(ID: {id})"""
                else:
                    if known:
                        if deleted:
                            msgOut = f"""I've undeleted id {id} which matched this factoid."""
                        else:
                            msgOut = f"""Oh, I already know that. It's ID {id}."""
                    else:
                        msgOut = "Something went wrong adding this factoid."

        else:
            msgOut = usage

        await ctx.send(msgOut)

    @commands.command(
        name="hist",
        aliases=["gethist"],
        description="""Returns change log for factoid provided or last triggered factoid if none provided.
                    The change log pages displayed in chat are navigable only by the caller.""",
        brief="Get factoid change log",
    )
    async def hist(self, ctx, id: typing.Optional[int] = 0):
        searchID = (
            self.db.getLastFactID(ctx.guild.id, ctx.channel.id) if id == 0 else id
        )

        success, history = self.db.getFactHist(searchID)

        if not success:
            await ctx.send(f"Something went wrong getting history for ID {searchID}.")
            return
        elif len(history) == 0:
            await ctx.send(f"History for ID {searchID} not found.")
            return

        pages = len(history)
        curPage = 1

        # Add spoiler tags if showing NSFW factoid in SFW channel
        st = "||" if history[0][5] == 1 and not ctx.channel.is_nsfw else ""

        msgEmbed = discord.Embed(
            title=f"""{history[curPage-1][0]}""",
            description=f"""OldTrigger: {st}{history[curPage-1][1]}{st}
            NewTrigger: {st}{history[curPage-1][8]}{st}
            OldMsg: {st}{history[curPage-1][2]}{st}
            NewMsg: {st}{history[curPage-1][3]}{st}
            Deleted: {history[curPage-1][4]==1}
            NSFW: {history[curPage-1][5]==1}
            User: {history[curPage-1][6]}
            Date: {history[curPage-1][7]}""",
            color=discord.Color.blue(),
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
                        title=f"""{history[curPage-1][0]}""",
                        description=f"""Trigger: {st}{history[curPage-1][1]}{st}\nOldMsg: {st}{history[curPage-1][2]}{st}\nNewMsg: {st}{history[curPage-1][3]}{st}\nDeleted: {history[curPage-1][4]==1}\nNSFW: {history[curPage-1][5]==1}\nUser: {history[curPage-1][6]}\nDate: {history[curPage-1][7]}""",
                        color=discord.Color.blue(),
                    )

                    msgEmbed.set_footer(
                        text=f"""Page {curPage} of {pages}. {'Spoiler tags for SFW channel' if st else ''}"""
                    )

                    await message.edit(embed=msgEmbed)
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and curPage > 1:
                    curPage -= 1
                    msgEmbed = discord.Embed(
                        title=f"""{history[curPage-1][0]}""",
                        description=f"""Trigger: {st}{history[curPage-1][1]}{st}\nOldMsg: {st}{history[curPage-1][2]}{st}\nNewMsg: {st}{history[curPage-1][3]}{st}\nDeleted: {history[curPage-1][4]==1}\nNSFW: {history[curPage-1][5]==1}\nUser: {history[curPage-1][6]}\nDate: {history[curPage-1][7]}""",
                        color=discord.Color.blue(),
                    )

                    msgEmbed.set_footer(
                        text=f"""Page {curPage} of {pages}. {'Spoiler tags for SFW channel' if st else ''}"""
                    )

                    await message.edit(embed=msgEmbed)
                    await message.remove_reaction(reaction, user)

                else:
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page
                    await message.remove_reaction(reaction, user)
            except asyncio.TimeoutError:
                await message.delete()
                break

    @commands.command(
        name="shutup",
        aliases=["shaddup", "stfu"],
        description="""Silences triggering of factoids for the duration provided, or 5 minutes if no duration provided. Max duration 30 min.""",
        brief="""Prevents triggering of factoids""",
    )
    async def shutup(self, ctx, shutUpDuration: typing.Optional[int] = 15):
        found, duration, started = self.db.getShutUpDuration(
            ctx.guild.id, ctx.channel.id
        )

        if found:
            timeLeft = (duration * 60) - (time.time() - started)

            if timeLeft < 0:
                msgOut = """Strange. I should be done with"""
            elif timeLeft < 10:
                msgOut = """Almost done with"""
            elif timeLeft < 30:
                msgOut = """I've got less than 30 seconds of"""
            elif timeLeft < 60:
                msgOut = """I've got less than a minute left of"""
            elif timeLeft < 120:
                msgOut = """I've got over a minute left of"""
            else:
                msgOut = f"""I've got over {math.floor(timeLeft/60)} minutes left of"""

            msgOut = msgOut + f" my current {duration} minute cooldown."
        else:
            if shutUpDuration > 30 or shutUpDuration < 1:
                msgOut = "I'm just gonna be quiet for 5 minutes."
                minutes = 5
            else:
                msgOut = f"""Okay, I'll shut up for {shutUpDuration} {'minutes' if shutUpDuration != 1 else 'minute'}."""
                minutes = shutUpDuration

            success = self.db.addShutUpRecord(ctx.guild.id, ctx.channel.id, minutes)
            if not success:
                msgOut = f"""Something went wrong shutting up for {shutUpDuration} {'minutes' if shutUpDuration != 1 else 'minute'}."""

        await ctx.send(msgOut)
