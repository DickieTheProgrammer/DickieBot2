import random
from discord.ext import commands

class General(commands.Cog):

    def __init__(self,bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("General cog loaded")

    @commands.command(name = 'roll', 
                    description = f'Simulates dice rolls. Syntax is !roll {{number}}d{{number}}.', 
                    brief = f'Rolls dem bones - {{number}}d{{number}}')
    async def roll(self, ctx, dice: str):
        # Rolls a dice in NdN format. 
        try:
            rolls, limit = map(int, dice.split('d'))
        except Exception:
            await ctx.send(f'Format has to be in {{number}}**d**{{number}}')
            return

        if rolls>25:
            msgOut = 'Max 25 dice'
        elif rolls <= 0 or limit <= 0:
            msgOut = 'Positive numbers only'
        else:
            msgOut = ', '.join(str(random.randint(1, limit)) for r in range(rolls))

        await ctx.send(msgOut)

    @commands.command(name = 'src', 
                    aliases=['source','sauce'], 
                    description='Returns GitHub source URL.', 
                    brief='Returns source URL')
    async def source(self, ctx):
        await ctx.send("<https://github.com/DickieTheProgrammer/DickieBot2>")
