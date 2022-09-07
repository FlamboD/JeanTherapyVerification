import asyncio
from datetime import datetime, timedelta
import random

from discord.ext import tasks
from discord.ui import *
from discord import app_commands
from TornAPI import TornAPI
import aiohttp
import discord
import dotenv
import os
import re
import typing

dotenv.load_dotenv()

class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents(message_content=True, messages=True).default()
        super().__init__(intents=intents)
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
        update_giveaway_embeds.start()




bot = MyBot()
tree = app_commands.CommandTree(bot)
JEAN_COLOR = int("2243B6", 16)
chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
giveaway_endings = ["Checking for rips", "Measuring booty circumference", "Checking if these are straight or skinny", "Testing the denim"]
giveaways = []

class ANSI:
    Black = "\u001b[30m"
    Red = "\u001b[31m"
    Green = "\u001b[32m"
    Yellow = "\u001b[33m"
    Blue = "\u001b[34m"
    Magenta = "\u001b[35m"
    Cyan = "\u001b[36m"
    White = "\u001b[37m"
    Reset = "\u001b[0m"

@tree.error
async def on_error(interaction: discord.Interaction, error: discord.app_commands.CommandInvokeError):
    raise error

@tree.command(
    name="teams",
    description="Shows the name of each team, their number of tickets, lives, and member count",
    guilds=[discord.Object(id=_) for _ in os.environ["GUILD_IDS"].split(",")]
)
async def teams(interaction: discord.Interaction):
    try:
        embed = discord.Embed(colour=JEAN_COLOR, title="Elimination Teams")
        elim_teams: list = (
            await get(interaction, TornAPI(key())
                      .torn(competition=True)
                      ))["competition"]["teams"]
        elim_teams.sort(key=lambda _: _["position"])
        data = [["#Pos", "Team", "Lives", "Tickets", "Members"]]
        for team in elim_teams:
            data.append([
                f' {team["position"]}',
                team["name"],
                team["lives"],
                team["score"],
                team["participants"] or "N/A"
            ])
        for col in range(len(data[0])):
            size = max([len(str(_[col])) for _ in data])
            for row in data:
                row[col] = (str(row[col]) + (" " * size))[:size]
        msg = ""
        for row in data:
            msg += "  ".join(row) + "\n"
        embed.add_field(name="\u200b", value=f"```glsl\n{msg}```")
        await interaction.response.send_message(embed=embed)
    except TornAPIError: return
    except Exception as e:
        print(e)
        return await interaction.response.send_message(
            "An unexpected error occurred, please try again",
            ephemeral=True)


@tasks.loop(seconds=15)
async def update_giveaway_embeds():
    global giveaways
    for _giveaway in giveaways:
        if not _giveaway.active or not _giveaway.message: continue
        if datetime.now() > _giveaway.end_time:
            await _giveaway.end()
        else:
            await _giveaway.update_message()


class Confirmation(View):
    def __init__(self, cb_yes, cb_no, timeout=180):
        super().__init__(timeout=timeout)
        self.enabled = True
        self.yes = Button(label="Yes", style=discord.ButtonStyle.green)
        self.yes.callback = self.callback(cb_yes)
        self.add_item(self.yes)
        self.no = Button(label="No", style=discord.ButtonStyle.red)
        self.no.callback = self.callback(cb_no)
        self.add_item(self.no)

    def callback(self, cb):
        async def inner(interaction: discord.Interaction):
            if not self.enabled: return
            self.enabled = False
            await cb(interaction)
        return inner

class Join(View):
    def __init__(self, cb_join, *, timeout = 180):
        super().__init__(timeout=timeout)
        self.join = Button(label="Join", style=discord.ButtonStyle.blurple)
        self.join.callback = self.callback(cb_join)
        self.add_item(self.join)

    @staticmethod
    def callback(cb):
        async def inner(interaction: discord.Interaction):
            await cb(interaction)
        return inner

class Giveaway:
    def __init__(self, webhook: discord.Webhook, author: discord.Member, channel: discord.TextChannel, seconds: int, prize: str, winners: int):
        self.id = "".join([random.choice(chars) for _ in range(5)])
        self.active = False
        self.author = author
        self.channel = channel
        self.end_time = datetime.now() + timedelta(seconds=seconds)
        self.message: typing.Optional[discord.WebhookMessage] = None
        self.participants = []
        self.prize = prize
        self.seconds = seconds
        self.start_time = datetime.now()
        self.webhook = webhook
        self.winners = winners

    async def confirm(self):
        self.log(f"{self.author.display_name} has started a giveaway for {self.prize} for {self.winners} winners running for {self.seconds//3600}h{self.seconds//60%60}m")
        timeout = 180
        await self.webhook.send(
            f"please confirm that everything is correct?\n*This view will expire* <t:{int((datetime.now() + timedelta(seconds=timeout)).timestamp())}:R>",
            embed=self.embed(),
            view=Confirmation(self.cb_yes, self.cb_no, timeout),
            ephemeral=True
        )

    async def send_starting_embed(self):
        self.message = await self.channel.send(embed=self.embed(), view=Join(self.cb_join))

    async def end(self):
        global giveaways
        self.active = False
        giveaways.remove(self)
        embed_base = discord.Embed(
            color=JEAN_COLOR,
            title="GIVEAWAY ENDED",
            description=f"Let's find out who pulled their jeans up first and won `{self.prize}` from {self.author.display_name}")

        message: typing.Optional[discord.Message] = await self.channel.send(
            f"Results <t:{int((datetime.now() + timedelta(seconds=5)).timestamp())}:R>",
            embed=embed_base.copy().add_field(
                name="Let's see who got their jeans up first",
                value=f"```\n{random.choice(giveaway_endings)}...```"
            )
        )

        try: await self.message.delete()
        except discord.HTTPException: pass

        await asyncio.sleep(5)
        try: winners = random.sample(self.participants, self.winners)
        except ValueError: winners = self.participants

        arr_winners = []

        for member in winners:
            try:
                data = await _get(TornAPI(key()).user(member.id, basic=True))
                arr_winners.append(f"- {member.display_name} [[Torn Profile](https://www.torn.com/profiles.php?XID={data['player_id']})]")
            except (TornAPIError, KeyError):
                arr_winners.append(f"- {member.display_name}")

        if len(arr_winners) == 0:
            arr_winners.append("No winners? Maybe these jeans were a bit too skinny :jeans:")

        try:
            await message.edit(
                content=None,
                embed=embed_base.copy().add_field(
                    name="The winners are",
                    value="\n".join(arr_winners)
                )
            )
        except discord.HTTPException:
            await self.channel.send(
                embed=embed_base.copy().add_field(
                    name="The winners are",
                    value="\n".join(arr_winners)
                )
            )

    async def update_message(self):
        try:
            await self.message.edit(embed=self.embed(), view=Join(self.cb_join))
        except discord.HTTPException:
            self.message = await self.channel.send(embed=self.embed(), view=Join(self.cb_join))

    async def bring_to_front(self):
        await self.message.delete()
        await self.send_starting_embed()

    def embed_content(self):
        return \
            f"```autohotkey\n" \
            f"Prize: {self.prize}\n" \
            f"Participants: {len(self.participants)}\n" \
            f"Possible winners: {self.winners}\n" \
            f"```" \
            f"This giveaway ends <t:{int(self.end_time.timestamp())}:R>\n" \
            f"Update <t:{int((datetime.now() + timedelta(seconds=15)).timestamp())}:R> :jeans:"

    def embed(self) -> discord.Embed:
        return discord.Embed(
            color=JEAN_COLOR,
            title="GIVEAWAY",
            description="We're back with another game of \"Who Can Fit Into Theeeeeese Jeans?!\"\nJoin if you think you can pull it up"
        ).add_field(
            name=f"{self.author.display_name} has started a giveaway!",
            value=self.embed_content()
        )

    def log(self, text: str):
        _text = f"{datetime.now()} [{self.id}] {text}"
        print(_text)
        with open("GiveawayLog.txt", "a") as _log:
            _log.write(f"{_text}\n")

    async def cb_yes(self, interaction: discord.Interaction):
        global giveaways
        await interaction.response.send_message("Option selected: Yes", ephemeral=True)
        giveaways.append(self)
        self.end_time = datetime.now() + timedelta(seconds=self.seconds)
        self.start_time = datetime.now()
        await self.send_starting_embed()
        self.active = True

    async def cb_no(self, interaction: discord.Interaction):
        self.log("Giveaway canceled")
        await interaction.response.send_message("Option selected: No", ephemeral=True)

    async def cb_join(self, interaction: discord.Interaction):
        if not self.active: return
        user = interaction.user
        if user.id == self.author.id:
            return await interaction.response.send_message(
                "You can't give away your jeans AND wear them :jeans:",
                ephemeral=True)
        if user in self.participants:
            return await interaction.response.send_message(
                "Only one pair of jeans per participant! :jeans:",
                ephemeral=True)
        self.log(f"{user.display_name} has joined the giveaway")
        self.participants.append(user)
        return await interaction.response.send_message(
            "Here are your pair of jeans :jeans:\n"
            "Let's see if you manage to get them on\n"
            "*You have been entered into the giveaway*",
            ephemeral=True)





async def time_autocomplete(interaction, current):
    if not re.fullmatch("\d+[m|h]?", current):
        return [app_commands.Choice(name=str(current+_), value=str(current+_)) for _ in ["1m", "5m", "10m", "15m", "30m", "1h"]]
    if any(_ in current for _ in ["h", "m"]):
        return [app_commands.Choice(name=current, value=current)]
    return [app_commands.Choice(name=str(current+_), value=str(current+_)) for _ in ["m", "h"]]

def number_autocomplete(_min, _max):
    async def inner(interaction, current):
        return [app_commands.Choice(name=str(_), value=_) for _ in range(_min, _max+1) if str(_).startswith(current)][:10]
    return inner

@tree.command(
    name="giveaway",
    description="creates a giveaway",
    guilds=[discord.Object(id=_) for _ in os.environ["GUILD_IDS"].split(",")]
)
@app_commands.autocomplete(runtime=time_autocomplete, winners=number_autocomplete(1, 20))
async def giveaway(interaction: discord.Interaction, prize: str, runtime: str, winners: int = 1):
    prize = prize.replace("\\", "\\\\").replace("`", "\\`")
    MAX_HOURS = 24
    if not re.fullmatch('\d+[m|h]', runtime):
        return await interaction.response.send_message("Invalid `runtime` amount entered", ephemeral=True)
    if ("h" in runtime and int(re.findall("\d+", runtime)[0]) > MAX_HOURS) or int(re.findall("\d+", runtime)[0]) > MAX_HOURS*60:
        return await interaction.response.send_message(f"Giveaway cannot exceed {MAX_HOURS} hours", ephemeral=False)

    await interaction.response.send_message("Creating giveaway...", ephemeral=True)

    seconds = int(re.match("\d+", runtime)[0]) * (60*60 if "h" in runtime else 60)
    running_giveaway = Giveaway(interaction.followup, interaction.user, interaction.channel, seconds, prize, winners)
    # giveaways.append(running_giveaway)

    await running_giveaway.confirm()


@tree.context_menu(
    name="Bring giveaway to front",
    guilds=[discord.Object(id=_) for _ in os.environ["GUILD_IDS"].split(",")]
)
async def giveaway_to_front(interaction: discord.Interaction, message: discord.Message):
    global giveaways
    for _giveaway in giveaways:
        if _giveaway.message == message:
            await _giveaway.bring_to_front()
            return await interaction.response.send_message("Giveaway has been moved to the end of the channel", ephemeral=True)
    return await interaction.response.send_message("This doesn't seem to be an active giveaway", ephemeral=True)




def key() -> str:
    return os.environ["TORN_KEY"]

async def get(interaction: discord.Interaction, url) -> dict:
    resp = await _get(url)
    if "error" in resp:
        await interaction.response.send_message("There was an error getting the user's data, please try again in a minute", ephemeral=True)
        raise TornAPIError()
    return resp

async def _get(url) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(str(url)) as resp:
            return await resp.json()


class TornAPIError(Exception):
    pass


bot.run(os.environ["BOT_KEY"])
