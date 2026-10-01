import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
load_dotenv()

TOKEN= os.getenv("TOKEN")

class TaticalTeam(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        await self.tree.sync()


bot = TaticalTeam()


@bot.event
async def on_ready():
    print(f"✅ {bot.user} está online!")


@bot.tree.command(
    name="ola",
    description="O bot te dá um oi, simples assim."
)
async def ola(interaction: discord.Interaction):
    await interaction.response.send_message("Olá Mundo!")


import os

bot.run(TOKEN)