from datetime import datetime, timedelta
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import *
from MyBot import MyBot

import asyncio
import discord
import random
import re
import typing

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
    ENDINGS = ["Checking for rips", "Measuring booty circumference", "Checking if these are straight or skinny", "Testing the denim"]

    def __init__(self, bot: MyBot, webhook: discord.Webhook, author: discord.Member, channel: discord.TextChannel, seconds: int, prize: str, winners: int):
        self.bot = bot
        self.id = "".join([random.choice(self.bot.chars) for _ in range(5)])
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
        try:
            self.message = await self.channel.send(embed=self.embed(), view=Join(self.cb_join))
        except discord.Forbidden:
            await self.webhook.send("I am missing the permissions to execute this command", ephemeral=True)
            self.log("Permission denied, canceling giveaway")
            self.bot.giveaways.remove(self)

    async def end(self):
        self.active = False
        self.bot.giveaways.remove(self)
        embed_base = discord.Embed(
            color=self.bot.JEAN_COLOR,
            title="GIVEAWAY ENDED",
            description=f"Let's find out who pulled their jeans up first and won `{self.prize}` from {self.author.display_name}")

        message: typing.Optional[discord.Message] = await self.channel.send(
            f"Results <t:{int((datetime.now() + timedelta(seconds=5)).timestamp())}:R>",
            embed=embed_base.copy().add_field(
                name="Let's see who got their jeans up first",
                value=f"```\n{random.choice(self.ENDINGS)}...```"
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
                data = await self.bot._get(self.bot.TornAPI(self.bot.key()).user(member.id, basic=True))
                arr_winners.append(f"- {member.display_name} [[Torn Profile](https://www.torn.com/profiles.php?XID={data['player_id']})]")
            except (self.bot.TornAPIError, KeyError):
                arr_winners.append(f"- {member.display_name}")

        if len(arr_winners) == 0:
            arr_winners.append("No winners? Maybe these jeans were a bit too skinny :jeans:")

        try:
            await message.edit(
                content=None,
                embed=embed_base.copy().add_field(
                    name=f"Out of the {len(self.participants)} who entered, the winners are",
                    value="\n".join(arr_winners)
                )
            )
        except discord.HTTPException:
            await self.channel.send(
                embed=embed_base.copy().add_field(
                    name=f"Out of the {len(self.participants)} who entered, the winners are",
                    value="\n".join(arr_winners)
                )
            )
        self.log(f"Giveaway ended with {len(self.participants)} participants, the winners are {', '.join([_.display_name for _ in winners])}")

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
            color=self.bot.JEAN_COLOR,
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
        await interaction.response.send_message("Option selected: Yes", ephemeral=True)
        self.bot.giveaways.append(self)
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

class GiveawayCog(commands.Cog):
    def __init__(self, bot: MyBot):
        self.bot = bot
        self.ctx_menu = app_commands.ContextMenu(
            name="Bring giveaway to front",
            callback=self.giveaway_to_front
        )

    @commands.hybrid_command(
        name="giveaway",
        description="Creates a giveaway"
    )
    async def giveaway(self, interaction: commands.Context, prize: str, runtime: str, winners: int = 1):
        prize = prize.replace("\\", "\\\\").replace("`", "\\`")
        MAX_HOURS = 24
        if not re.fullmatch('\d+[m|h]', runtime):
            return await interaction.reply("Invalid `runtime` amount entered", ephemeral=True)
        if ("h" in runtime and int(re.findall("\d+", runtime)[0]) > MAX_HOURS) or int(
                re.findall("\d+", runtime)[0]) > MAX_HOURS * 60:
            return await interaction.reply(f"Giveaway cannot exceed {MAX_HOURS} hours", ephemeral=False)

        await interaction.reply("Creating giveaway...", ephemeral=True)

        seconds = int(re.match("\d+", runtime)[0]) * (60 * 60 if "h" in runtime else 60)
        running_giveaway = Giveaway(self.bot, interaction, interaction.author, interaction.channel, seconds, prize, winners)
        # giveaways.append(running_giveaway)

        await running_giveaway.confirm()

    @giveaway.autocomplete('runtime')
    async def winners_autocomplete(self, interaction: commands.Context, current: str):
        return await self.bot.Autocomplete.time(current)

    @giveaway.autocomplete('winners')
    async def winners_autocomplete(self, interaction: commands.Context, current: str):
        return self.bot.Autocomplete.number(current, 1, 20)

    # @app_commands.context_menu(
    #     name="Bring giveaway to front"
    # )
    async def giveaway_to_front(self, interaction: discord.Interaction, message: discord.Message):
        for _giveaway in self.bot.giveaways:
            if _giveaway.message == message:
                await _giveaway.bring_to_front()
                return await interaction.response.send_message("Giveaway has been moved to the end of the channel",
                                                               ephemeral=True)
        return await interaction.response.send_message("This doesn't seem to be an active giveaway", ephemeral=True)

    @tasks.loop(seconds=15)
    async def update_giveaway_embeds(self):
        for _giveaway in self.bot.giveaways:
            if not _giveaway.active or not _giveaway.message: continue
            if datetime.now() > _giveaway.end_time:
                await _giveaway.end()
            else:
                await _giveaway.update_message()

    def cog_load(self) -> None:
        self.update_giveaway_embeds.start()

    def cog_unload(self) -> None:
        self.update_giveaway_embeds.stop()

async def setup(bot: MyBot):
    await bot.add_cog(GiveawayCog(bot))