from discord.ext import commands
from MyBot import MyBot
from watchgod import awatch
from watchgod.watcher import Change

class WatchGod(commands.Cog):
    def __init__(self, bot: MyBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        async for change in awatch(self.bot.cog_path):
            try:
                if change:
                    c = change.pop()
                    if c[1].endswith(".py"):
                        fn = c[1].split("\\")[-1].replace('.py', '')
                        cfn = f'cogs.{fn}'

                        if cfn not in self.bot.extensions:
                            if not c[0] == c[0].deleted:
                                await self.bot.load_extension(cfn)
                                print(f"Added cog {fn}")
                        else:
                            if not c[0] == c[0].deleted:
                                await self.bot.reload_extension(cfn)
                                print(f"Reloaded cog {fn}")
                            else:
                                await self.bot.unload_extension(cfn)
                                print(f"Removed cog {fn}")
                        await self.bot.tree.sync()
            except Exception as e:
                print(type(e), e)

async def setup(bot: MyBot):
    await bot.add_cog(WatchGod(bot))