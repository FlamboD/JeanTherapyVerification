from datetime import datetime, timedelta
from discord.ext import commands
from enum import Enum
from MyBot import MyBot

import discord
import sqlite3
import typing


class EliminationTeams(Enum):
    Dirty_Cops = 'dirty-cops'
    Firestarters = 'firestarters'
    Hard_Boiled = 'hard-boiled'
    Jean_Therapy = 'jean-therapy'
    Laughing_Stock = 'laughing-stock'
    Rawring_Thunder = 'rawring-thunder'
    Rain_Men = 'rain-men'
    Satans_Soldiers = 'satants-soldiers'
    Sleepyheads = 'sleepyheads'
    Totally_Boned = 'totally-boned'
    Quack_Addicts = 'quack-addicts'
    Wolf_Pack = 'wolf-pack'
    Unknown = 'unknown'


class SQL:
    PATH = "attacks.sqlite"

    def __init__(self):
        self.conn = sqlite3.connect(self.PATH)

    @staticmethod
    def past_hour():
        if datetime.now().minute < 30:
            end = datetime.replace(datetime.now(), minute=0, second=0, microsecond=0)
        else:
            end = datetime.replace(datetime.now(), minute=30, second=0, microsecond=0)
        start = end - timedelta(minutes=30)
        return [start, end]

    def get_attacks(self, team=EliminationTeams.Jean_Therapy.value, incoming=True):
        sql = f"SELECT * FROM attacks WHERE time > ? AND time < ? AND {'defender' if incoming else 'attacker'} = ?"
        cur = self.conn.execute(sql, [*self.past_hour(), team])
        return cur.fetchall()


class Elimination(commands.Cog):
    def __init__(self, bot: MyBot):
        self.bot = bot

    @commands.hybrid_command(
        name="teams",
        description="Shows the name of each team, their number of tickets, lives, and member count"
    )
    @commands.cooldown(2, 60, commands.BucketType.guild)
    async def teams(self, interaction: commands.Context):
        try:
            embed = discord.Embed(colour=self.bot.JEAN_COLOR, title="Elimination Teams")
            elim_teams: list = (
                await self.bot.get(interaction, self.bot.TornAPI(self.bot.key())
                          .torn(competition=True)
                          ))["competition"]["teams"]
            elim_teams.sort(key=lambda _: _["position"])
            data = [["#Pos", "Team", "Lives", "Ticks", "Members", "Win", "Lose"]]
            for team in elim_teams:
                data.append([
                    f' {team["position"]}',
                    team["name"],
                    team["lives"],
                    team["score"],
                    team["participants"] or "N/A",
                    team["wins"],
                    team["losses"]
                ])
            for col in range(len(data[0])):
                size = max([len(str(_[col])) for _ in data])
                for row in data:
                    row[col] = str(row[col]).ljust(size)
            msg = ""
            for row in data:
                msg += "  ".join(row) + "\n"
            embed.add_field(name="\u200b", value=f"```glsl\n{msg}```")
            await interaction.reply(embed=embed)
        except self.bot.TornAPIError:
            return
        except Exception as e:
            print(e)
            return await interaction.reply(
                "An unexpected error occurred, please try again",
                ephemeral=True)

    @teams.error
    async def on_teams_error(self, interaction: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await interaction.reply(str(error), ephemeral=True)

    @commands.hybrid_command(
        name="attacks",
        description="Display incoming/outgoing attacks for a team"
    )
    @commands.cooldown(5, 60, commands.BucketType.guild)
    async def attacks(self, interaction: commands.Context, team: EliminationTeams,
                      direction: typing.Literal["incoming", "outgoing", "both"]):
        def title(name: EliminationTeams):
            return name.name.replace('-', ' ').title()
        print("A")
        embed = discord.Embed(color=self.bot.JEAN_COLOR, title=f"{title(team)}", description="Attacks between " + " and ".join(
            [f"<t:{int(_.timestamp())}:T>" for _ in SQL.past_hour()]))
        incoming = None
        outgoing = None
        print("B")
        if direction == 'both':
            incoming = SQL().get_attacks(team.value, True)
            outgoing = SQL().get_attacks(team.value, False)
        elif direction == 'incoming':
            incoming = SQL().get_attacks(team.value, True)
        else:
            outgoing = SQL().get_attacks(team.value, False)
        print("C")
        br = "\n"
        if incoming is not None:
            embed.add_field(
                name="Incoming",
                value=f"```py\n"
                      f"{br.join([f'{title(_)}: {len([__ for __ in incoming if __[1] == _.value])}' for _ in EliminationTeams if _ != team])}"
                      f"{br}{br}"
                      f"Total: {sum([_[1] for _ in incoming])}"
                      f"```"
            )
        print("D")
        if outgoing is not None:
            embed.add_field(
                name="Outgoing",
                value=f"```py\n"
                      f"{br.join([f'{title(_)}: {len([__ for __ in outgoing if __[2] == _.value])}' for _ in EliminationTeams if _ != team])}"
                      f"{br}{br}"
                      f"Total: {sum([_[1] for _ in outgoing])}"
                      f"```"
            )
        print("F")
        await interaction.reply(embed=embed)
        print("G")

    @attacks.error
    async def on_attacks_error(self, interaction: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandOnCooldown):
            await interaction.reply(str(error), ephemeral=True)
        print(error)


async def setup(bot: MyBot):
    await bot.add_cog(Elimination(bot))