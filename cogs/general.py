import random
from discord.ext import commands

class General(commands.Cog):

    def __init__(self, bot, src):
        self.bot = bot
        self.src = src

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
        elif limit > 999999:
            msgOut = 'Max 999999-sided die'
        else:
            results = []
            for r in range(rolls): results.append(random.randint(1, limit))
            msgOut = ', '.join(str(r) for r in results) + f'\n\nTotal: {sum(results)}'

        await ctx.send(msgOut)

    @commands.command(name = 'src', 
                    aliases = ['source','sauce'], 
                    description = 'Returns GitHub source URL.', 
                    brief = 'Returns source URL')
    async def source(self, ctx):
        await ctx.send(f"<{self.src}>")
