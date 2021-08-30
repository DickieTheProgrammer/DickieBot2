import typing
import random
import string

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
            if str(frequency).isnumeric() and (self.bot.owner_id == user or ctx.guild.owner_id == user):
                self.randPerc[ctx.guild.id] = int(frequency)
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

    @commands.command(name = 'delfact',
                    aliases = ['del','baleet','delete'],
                    description = 'Marks a factoid as deleted, preventing its triggering in chat.',
                    brief = 'Deletes a factoid')
    async def delfact(self, ctx, id = None):
        if not id.isnumeric() and id != None:
            await ctx.send("This is not a valid factoid ID")
            return

        fact = self.db.factInfo(id if id != None else self.db.getLastFactID(ctx.guild.id)) if id == None or str(id).isnumeric() else []

        if fact == None:
            msgOut = f"Something went wrong deleting fact ID {fact[0]}"""
        elif len(fact) == 0 :
            msgOut = f"Couldn't find fact ID {fact[0]}"
        else:
            result, deleted = self.db.delFact(fact[0], ctx.message.author.display_name, ctx.message.author.id)
            if not result:
                if deleted:
                    msgOut = f"ID {fact[0]} already deleted."
                else:
                    msgOut = f"Something went wrong deleting fact ID {fact[0]}"""
            else:
                msgOut = f"Fact with ID {fact[0]} has been marked deleted."

        await ctx.send(msgOut)
        
    @commands.command(name = 'undelfact',
                    aliases = ['undel','unbaleet','undelete'],
                    description = 'Marks a factoid as undeleted, allowing its triggering in chat.',
                    brief = 'Undeletes a factoid')
    async def undelfact(self, ctx, id = None):
        if not id.isnumeric() and id != None:
            await ctx.send("This is not a valid factoid ID")
            return

        fact = self.db.factInfo(id if id != None else self.db.getLastFactID(ctx.guild.id)) if id == None or str(id).isnumeric() else []

        if fact == None:
            msgOut = f"Something went wrong undeleting fact ID {fact[0]}"""
        elif len(fact) == 0 :
            msgOut = f"Couldn't find fact ID {fact[0]}"
        else:
            result, undeleted = self.db.undelFact(fact[0], ctx.message.author.display_name, ctx.message.author.id)
            if not result:
                if undeleted:
                    msgOut = f"ID {fact[0]} was not deleted."
                else:
                    msgOut = f"Something went wrong undeleting fact ID {fact[0]}"""
            else:
                msgOut = f"Fact with ID {fact[0]} has been marked undeleted."

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
            msgOut = f"""
    ID: {str(fact[0])}
    Trigger: {fact[1] if fact[1] != None else "*None*"}
    Response: {fact[2]}
    NSFW: {str(fact[3]==1)}
    Deleted: {str(fact[4]==1)}
    Creator: {fact[5]}
    Created: {fact[6]}
    Times Triggered: {fact[7]}
    Last Triggered: {fact[8]}
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

            success, known = self.db.addRandFact(args, nsfw, ctx.message.author.display_name, ctx.message.author.id)

            if success:
                msgOut = f"""Ok. I'll randomly say "{args}\""""
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

            nsfw = 1 if ctx.invoked_with == 'onnsfw' else 0

            success, known = self.db.addFact(cleanTrigger, response, nsfw, ctx.message.author.display_name, ctx.message.author.id)

            if success:
                msgOut = f"""Ok. When I see "{trigger}" I'll say "{response}\""""
            else:
                if known:
                    msgOut = 'Oh, I already know that.'
                else:
                    msgOut = 'Something went wrong adding this factoid.'

        await ctx.send(msgOut)