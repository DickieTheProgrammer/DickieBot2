import typing
import random
import string
import asyncio

from discord.ext import commands
import dbFunctions
import parseUtil

DEFAULTPERC = 5

class Factoids(commands.Cog):
    
    def __init__(self, bot, db: dbFunctions.Connection):
        self.bot = bot
        self.db = db

        self.noList= [
            "https://c.tenor.com/2yJBnYOY_j8AAAAC/tonton-tonton-sticker.gif",
            "https://c.tenor.com/UIrQocNe4xYAAAAM/no-no-no-way.gif",
            "https://c.tenor.com/U9oGKTRaBo0AAAAM/bugs-bunny-bunny.gif",
            "https://c.tenor.com/xAyrbho-SPEAAAAM/bachelor-mattjames.gif"
            "https://c.tenor.com/28WY5uWjdv0AAAAM/nope-sloth.gif",
            "https://giphy.com/embed/daPCSjwus6UR2JxRX1",
            "https://giphy.com/embed/3ov9jLsBqPh6rjuHuM",
            "https://giphy.com/embed/VgqtLbNtJEWtVlfMVv",
            "https://giphy.com/embed/QIPEV0HWAiXVm",
            "https://giphy.com/embed/XymaJlgorUL8vOfF88"
        ]

    @commands.Cog.listener()
    async def on_ready(self):
        print("Factoids cog loaded")

    @commands.command(name = 'setfreq', 
                description = """Allows server owner to set frequency of non-command messages that trigger a random factoid.
                Integer provided should be between 0 and 100. 0 disables his random messages and 100 is completely insane.
                Values < 0 will default to 0. Values > 100 will default to 100. Default value if no number provided is 5.
                ONLY THE SERVER ADMIN OR BOT OWNER CAN USE THIS""",
                brief = 'Set frequency of random factoids.')
    async def setfreq(self, ctx, frequency: typing.Optional[int] = DEFAULTPERC):
        user = ctx.message.author.id

        try:
            if self.bot.owner_id == user or ctx.guild.owner_id == user:
                self.db.updateFreq(ctx.guild.id, frequency)
                msgOut = f"""You're the boss. Frequency for {ctx.guild.name} set to {frequency}%"""
            else:
                msgOut = random.sample(self.noList,1)[0]
        except Exception as e:
            msgOut = 'Something went wrong setting random frequency'

        await ctx.send(msgOut)

    @commands.command(name = 'freq', 
                aliases = ['getfreq'],
                description = """Returns the frequency with which I will respond to non-command messages with random factoids. Number is out of 100.""",
                brief = "Get random frequency of server")
    async def freq(self, ctx):
        msgOut = f"""Frequency for {ctx.guild.name} set to {self.db.getFreq(ctx.guild.id)}%"""
        await ctx.send(msgOut)

    @commands.command(name = 'delete',
                    aliases = ['del','undel','undelete','baleet','unbaleet'],
                    description = 'Toggles deleted flag on specified factoid or most recent triggered factoid if none specified.',
                    brief = 'or !undelete, toggles deleted/undeleted')
    async def delfact(self, ctx, id = None):
        if not id.isnumeric() and id != None:
            await ctx.send("This is not a valid factoid ID")
            return

        fact = self.db.factInfo(id if id != None else self.db.getLastFactID(ctx.guild.id)) if id == None or str(id).isnumeric() else []

        delDesc = 'delete' if ctx.invoked_with in ['delete','del','baleet'] else 'undelete'
        delNum = 1 if ctx.invoked_with in ['delete','del','baleet'] else 0

        if fact == None:
            msgOut = f"Something went wrong trying to {delDesc} fact ID {fact[0]}"""
        elif len(fact) == 0 :
            msgOut = f"Couldn't find fact ID {fact[0]}"
        else:
            result, changed = self.db.delFact(fact[0], ctx.message.author.display_name, ctx.message.author.id, delNum)
            if not result:
                if not changed:
                    msgOut = f"ID {fact[0]} already {delDesc}d."
                else:
                    msgOut = f"Something went wrong trying to {delDesc} fact ID {fact[0]}"""
            else:
                msgOut = f"Fact with ID {fact[0]} has been marked {delDesc}d."

        await ctx.send(msgOut)
        
    @commands.command(name = 'wtf', 
                    aliases = ['what', 'wth'], 
                    description = 'Retrieves info on specified factoid or last factoid if no id provided.', 
                    brief = 'Retrieve factoid info')
    async def wtf(self, ctx, id: typing.Optional[int] = None):
        fact = self.db.factInfo(id if id != None else self.db.getLastFactID(ctx.guild.id)) if id == None or str(id).isnumeric() else []

        if fact == None:
            msgOut = f'Something went wrong retrieving fact info for ID {id}'
        elif len(fact) == 0:
            msgOut = """¯\_(ツ)_/¯"""
        else: 
            msgOut = f"""ID: {str(fact[0])}\nTrigger: {fact[1] if fact[1] != None else "*None*"}\nResponse: {fact[2]}\nNSFW: {str(fact[3]==1)}\nDeleted: {str(fact[4]==1)}\nCreator: {fact[5]}\nCreated: {fact[6]}\nTimes Triggered: {fact[7]}\nLast Triggered: {fact[8]}
            """
        await ctx.send(msgOut)

    @commands.command(name='onrand', 
                aliases = ['onrandnsfw'],
                description="""Give me something random to do/say. Uses the same variables as !on.
                Use !onrandnsfw for nsfw factoids.""", 
                brief = 'Give me something to randomly blurt.')
    async def onrand(self, ctx, *, args: str):
        botCommand = True if args.startswith('!') else False

        if botCommand:
            msgOut = "I'm not remembering bot commands."
        else:
            nsfw = 1 if ctx.invoked_with == 'onnsfwrand' else 0

            success, known, id = self.db.addRandFact(args, nsfw, ctx.message.author.display_name, ctx.message.author.id)

            if success:
                msgOut = f"""Ok. I'll randomly say "{args}\"\n(ID: {id})"""
            else:
                if known:
                    msgOut = 'Oh, I already know that.'
                else:
                    msgOut = 'Something went wrong adding this factoid.'

        await ctx.send(msgOut)

    @commands.command(name = 'mod',
                    aliases = ['modfact','modthat'],
                    description = """
                    Allows you to modify a factoid response by providing a substitution regex formatted s/pattern/replacement
                    !mod <id> {substitution string}, if id blank, updates last called factoid""",
                    brief = 'Modify factoid response')
    async def mod(self, ctx, id: typing.Optional[int] = 0, *, regEx):
        lastID = self.db.getLastFactID(ctx.guild.id) if id == 0 else id

        try:
            if regEx.endswith('//'):
                s, pattern = regEx.strip('/').split('/')
                repl = ''
            else:
                s, pattern, repl = regEx.strip('g').strip('/').split('/')
        except Exception as e:
            await ctx.send("Syntax is !mod <id> {substitution string in form s/pattern/replacement}")
            return

        results = self.db.modFact(lastID, pattern, repl, ctx.message.author.display_name, ctx.message.author.id)
        
        # results returned list = [success, known, matched, changed, oldResp, newResp]
        if not results[1]:
            msgOut = f"Fact ID {lastID} not found."
        elif not results[2]:
            msgOut = f"""Pattern "{pattern}" not found."""
        elif not results[3]:
            msgOut = f"""Message wasn't changed by this substitution."""
        elif not results[0]:
            msgOut = f"Something went wrong modifying fact id {lastID}"
        else:
            msgOut = f"""Successfully changed fact {id} response from 
{results[4]}
to
{results[5]}"""

        await ctx.send(msgOut)                

    @commands.command(name='nsfw',
                    aliases = ['sfw'],
                    description = 'Toggles NSFW flag on factoid record.',
                    brief = 'or !sfw, mark factoid NSFW/SFW')
    async def nsfw(self, ctx, id: typing.Optional[int] = 0):        
        
        lastID = self.db.getLastFactID(ctx.guild.id) if id == 0 else id
        valueNSFW = 1 if ctx.invoked_with == 'nsfw' else 0

        success, changed = self.db.toggleNSFW(lastID, valueNSFW)

        descNSFW = 'NSFW' if ctx.invoked_with == 'nsfw' else 'sfw'

        if not success:
            msgOut = f"""Something went wrong marking {lastID} as {descNSFW}."""
        elif not changed:
            msgOut = f"""ID {lastID} already marked {descNSFW}."""
        else:
            msgOut = f"""Successfully set ID {lastID} as {descNSFW}."""
            
        await ctx.send(msgOut)

    @commands.command(name = 'on', 
                    aliases = ['onnsfw'], 
                    description = f"""Assign a response to triggering phrase. !on<nsfw> {{trigger}} -say {{response}}. 
                    Using !onnsfw marks the response as NSFW and will not be triggered in SFW channels.
                    Use $self to refer to the bot in the trigger. i.e. !on "Hi $self" -say Hello. 
                    Use $rand, $nick, and $item in response to sub in a random user, the triggering user, and an inventory item, respectively.
                    $item consumes the inventory item.""", 
                    brief = 'Teach me to respond to something')
    async def on(self, ctx, *, args):
        parts = args.split('-say')
        if len(parts) <= 1:
            msgOut = 'Usage is !on<nsfw> trigger -say response'
        else:
            trigger = parseUtil.convertEmote(parts[0]).strip()
            response = ''.join(parts[1:]).strip()
            botCommand = True if trigger.startswith('!') or response.startswith('!') else False
            
            cleanTrigger = parseUtil.mentionToSelfVar(trigger, self.db.getBotRole(ctx.guild.id), self.bot.user.id)
            triggerParts = cleanTrigger.split('$self')
            cleanTrigger = '$self'.join(e.strip(string.punctuation).lower() for e in triggerParts).strip()

            if botCommand:
                msgOut = "I'm not remembering bot commands."
            elif len(cleanTrigger) < 4:
                msgOut = 'Trigger must be >= 4 alphanumeric characters'
            else:    
                if trigger.startswith('_') and trigger.endswith('_'):
                    cleanTrigger = '_' + trigger + '_'

                print(ctx.invoked_with)

                nsfw = 1 if ctx.invoked_with == 'onnsfw' else 0

                success, known, id = self.db.addFact(cleanTrigger, response, nsfw, ctx.message.author.display_name, ctx.message.author.id)

                if success:
                    msgOut = f"""Ok. When I see "{trigger}" I'll say "{response}\"\n(ID: {id})"""
                else:
                    if known:
                        msgOut = 'Oh, I already know that.'
                    else:
                        msgOut = 'Something went wrong adding this factoid.'

        await ctx.send(msgOut)

    @commands.command(name = 'hist',
                    aliases = ['gethist'],
                    description = """Returns change log for factoid provided or last triggered factoid if none provided.
                    The change log pages displayed in chat are navigable only by the caller and will eventually self-destruct after 60s of inactivity.""",
                    brief = 'Get factoid change log')
    async def hist(self, ctx, id: typing.Optional[int] = 0):
        #return # disabling for now
        searchID = self.db.getLastFactID(ctx.guild.id) if id == 0 else id
        contents = []
        
        success, history = self.db.getFactHist(searchID)

        if not success:
            await ctx.send(f"Something went wrong getting history for ID {searchID}.")
            return
        elif len(history) == 0:
            await ctx.send(f"History for ID {searchID} not found.")
            return
            
        pages = len(history)
        curPage = 1

        for rec in range(pages):
            contents.append(f"""**{len(pages)} Pages**\n\nID: {history[rec-1][0]}\nTrigger: {history[rec-1][1]}\nOldMsg: {history[rec-1][2]}\nNewMsg: {history[rec-1][3]}\nDeleted: {history[rec-1][4]==1}\nNSFW: {history[rec-1][5]==1}\nUser: {history[rec-1][6]}\nDate: {history[rec-1][7]}
            """)

        message = await ctx.send(contents[curPage-1])

        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        def check(reaction,user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]
        
        while True:
            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60, check=check)

                if str(reaction.emoji) == "▶️" and curPage != pages:
                    curPage += 1
                    await message.edit(content=f"Page {curPage}/{pages}:\n{contents[curPage-1]}")
                    await message.remove_reaction(reaction, user)

                elif str(reaction.emoji) == "◀️" and curPage > 1:
                    curPage -= 1
                    await message.edit(content=f"Page {curPage}/{pages}:\n{contents[curPage-1]}")
                    await message.remove_reaction(reaction, user)

                else:
                    await message.remove_reaction(reaction, user)
                    # removes reactions if the user tries to go forward on the last page or
                    # backwards on the first page
            except asyncio.TimeoutError:
                await message.delete()
                break