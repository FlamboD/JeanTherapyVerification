from discord.ext import commands
from discord import app_commands

import aiohttp
import discord
import os
import random
import re
from TornAPI import TornAPI

class MyBot(commands.Bot):
    def __init__(self, tasks=None):
        if tasks is None: tasks = []
        intents = discord.Intents(message_content=True, messages=True).default()
        super().__init__(lambda a, b: '-'.join(random.sample('the-snow-glows-white-on-the-mountain-tonight', 10)), intents=intents)
        self.synced = False
        self.cog_path = os.path.abspath("./cogs")
        self.tasks = tasks

        self.JEAN_COLOR = int("2243B6", 16)
        self.chars = "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz0123456789"
        self.TornAPI = TornAPI
        self.giveaways = []

    async def setup_hook(self) -> None:
        for cog in os.listdir(self.cog_path):
            try:
                if cog.endswith(".py"):
                    await self.load_extension(f'cogs.{cog.replace(".py", "")}')
            except Exception as e: print(type(e), e)

    @staticmethod
    def key() -> str:
        return os.environ["TORN_KEY"]

    async def get(self, interaction: commands.Context, url) -> dict:
        resp = await self._get(url)
        if "error" in resp:
            await interaction.reply(
                "There was an error getting the user's data, please try again in a minute", ephemeral=True)
            raise self.TornAPIError()
        return resp

    @staticmethod
    async def _get(url) -> dict:
        async with aiohttp.ClientSession() as session:
            async with session.get(str(url)) as resp:
                return await resp.json()

    class TornAPIError(Exception):
        pass

    class Autocomplete:
        @staticmethod
        def number(current, _min, _max):
            return [app_commands.Choice(name=str(_), value=_) for _ in range(_min, _max + 1) if
                    str(_).startswith(current)][:10]

        @staticmethod
        async def time(current):
            if not re.fullmatch("\d+[m|h]?", current):
                return [app_commands.Choice(name=str(current + _), value=str(current + _)) for _ in
                        ["1m", "5m", "10m", "15m", "30m", "1h"]]
            if any(_ in current for _ in ["h", "m"]):
                return [app_commands.Choice(name=current, value=current)]
            return [app_commands.Choice(name=str(current + _), value=str(current + _)) for _ in ["m", "h"]]
