import os
import discord
from discord.ext import commands
from aiohttp import web


TOKEN = os.getenv("DISCORD_TOKEN")


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


# Página necessária para o Render
async def health_check(request):
    return web.Response(text="Tatical Team está online!")


async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", 10000))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()


async def main():
    await start_web_server()
    await bot.start(TOKEN)


import asyncio

asyncio.run(main())
