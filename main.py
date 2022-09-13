from MyBot import MyBot
import discord
import dotenv
import os

dotenv.load_dotenv()

bot = MyBot()

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    if not bot.synced:
        try:
            await bot.tree.sync()
        except discord.Forbidden:
            pass
        bot.synced = True
    print(f"Logged in as {bot.user}")
    for task in bot.tasks:
        task.start()
    # update_giveaway_embeds.start()

bot.run(os.environ["BOT_KEY"])