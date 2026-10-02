import os
import asyncio
import aiohttp
from aiohttp import web
import discord
from discord.ext import commands


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


# =========================
# SERVIDOR HTTP DO RENDER
# =========================

async def home(request):
    return web.Response(
        text="TaticalTeam está online!"
    )


async def start_web_server():
    app = web.Application()

    app.router.add_get("/", home)
    app.router.add_get("/health", home)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.environ.get("PORT", 10000))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print(f"🌐 Servidor HTTP iniciado na porta {port}")


# =========================
# EVENTOS DO BOT
# =========================

@bot.event
async def on_ready():
    print(f"✅ {bot.user} está online!")


# =========================
# INICIALIZAÇÃO
# =========================

async def main():
    await start_web_server()

    token = os.environ["DISCORD_TOKEN"]

    await bot.start(token)


asyncio.run(main())
