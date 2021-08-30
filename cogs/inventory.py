import random

from discord.ext import commands
import dbFunctions

class Inventory(commands.Cog):

    def __init__(self, bot, db: dbFunctions.Connection):
        self.bot = bot
        self.db = db

        self.nothingList = [
            "https://giphy.com/embed/l41YlPKMCfNoseS8E",
            "https://giphy.com/embed/fxqlDFNqdvYiRuCLf4",
            "https://giphy.com/embed/llJIUkV73NmqvYWVqF",
            "https://giphy.com/embed/3ohhwsjzpejaSWoTkI",
            "https://c.tenor.com/nEdV6gnb35UAAAAC/i-have-nothing-eye-roll.gif",
            "https://c.tenor.com/e7Zo7FajjBUAAAAC/bejo-avarisocio.gif",
            "https://c.tenor.com/HYJcMD1hjPQAAAAM/i-have-nothing-i-dont-have-anything.gif",
            "https://giphy.com/embed/QZOaeparxsNOfKWbER",
            "https://giphy.com/embed/gjIvS6VpFQKNP0ZcvJ",
            "https://c.tenor.com/q-E5wj1K6OYAAAAM/monsters-inc-sully.gif"
        ]

    @commands.Cog.listener()
    async def on_ready(self):
        print("Inventory cog loaded")

    @commands.command(name = 'inv', 
                    aliases=['inventory','stuff','items'], 
                    description="Returns current guild's inventory.", 
                    brief='Displays inventory')
    # add @commands.cooldown(2, 20, commands.BucketType.user) here?
    async def inv(self, ctx):
        itemList = self.db.getInventory(ctx.guild.id)

        if itemList == None:
            await ctx.send("Something went wrong fetching inventory.")
            return

        deTupledList = [' '.join(elem) for elem in itemList]
        listLen = len(deTupledList)

        # Randomly order list to give "first in" items some visibility
        deTupledList = random.sample(deTupledList,listLen)

        if listLen == 0:
            msgOut = random.sample(self.nothingList,1)[0]
        else:
            msgOut = "I have:\n\t○ " + "\n\t○ ".join(deTupledList[0:5])

            if listLen > 5:
                msgOut = msgOut + "\nand, like, " + str(listLen-5) + " other thing"
            if listLen > 6:
                msgOut = msgOut + "s"

        await ctx.send(msgOut)

    @commands.command(name = 'whogave', 
                    aliases = ['whogaveyou','whogaveu'], 
                    description = 'Tells who gave me an item', 
                    brief = 'Who gave me a thing?')
    async def whogave(self, ctx, *, item: str):
        donors = self.db.getItemDonor(ctx.guild.id,item)
        resolvedDonors = []

        if donors == None:
            msgOut = "Something went wrong finding the donor of this item."
        elif len(donors) == 0:
            msgOut = "I don't have that."
        else:
            for donor in donors: resolvedDonors.append('<@!' + donor + '>')
            msgOut = "It was %s" % ' and '.join(resolvedDonors)
        
        await ctx.send(msgOut)