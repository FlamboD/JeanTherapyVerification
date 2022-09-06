from discord.ext import commands
import aiohttp
import discord
import dotenv
import os

dotenv.load_dotenv()

intents = discord.Intents()

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.synced = False

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            for guild_id in os.environ["GUILD_IDS"].split(","):
                try:
                    await tree.sync(guild=discord.Object(id=guild_id))
                except discord.Forbidden: pass
            self.synced = True
        print(f"Logged in as {self.user}")


bot = MyBot()
tree = discord.app_commands.CommandTree(bot)


@tree.command(
    name="username",
    description="Get torn username of a member",
    guilds=[discord.Object(id=_) for _ in os.environ["GUILD_IDS"].split(",")]
)
async def username(
        interaction: discord.Interaction,
        member: discord.Member,
        ephemeral: bool = True):
    try:
        key = os.environ["TORN_KEY"]
        user_info = await _get(f"https://api.torn.com/user/{member.id}/?key={key}&selections=basic")
        if "error" in user_info:
            if user_info["error"]["code"] == 6:
                return await interaction.response.send_message(f"{member.display_name}'s discord account isn't liked to a torn account. https://www.torn.com/discord", ephemeral=ephemeral)
            return await interaction.response.send_message("There was an error getting the user's data, please try again in a minute", ephemeral=True)
        return await interaction.response.send_message(f"{member.display_name}'s torn username is `{user_info['name']} [{user_info['player_id']}]`", ephemeral=ephemeral)
    except TornAPIError:
        return
    except:
        return await interaction.response.send_message("An unexpected error occurred, please try again", ephemeral=True)

# @bot.command()
async def verify(ctx: commands.Context):
    pass

async def get(interaction: discord.Interaction, url) -> dict:
    resp = await _get(url)
    if "error" in resp:
        await interaction.response.send_message("There was an error getting the user's data, please try again in a minute", ephemeral=True)
        raise TornAPIError()
    return resp

async def _get(url) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()


class TornAPIError(Exception):
    pass


bot.run(os.environ["BOT_KEY"])
