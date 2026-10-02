import os
import asyncio
from aiohttp import web
import discord
from discord.ext import commands


# =========================
# BOT DISCORD
# =========================

class TaticalTeam(commands.Bot):

    def __init__(self):
        intents = discord.Intents.all()

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        print("🔄 Sincronizando comandos slash...")

        try:
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} comandos slash sincronizados!")

        except Exception as e:
            print(f"❌ Erro ao sincronizar comandos: {e}")


bot = TaticalTeam()


# =========================
# SERVIDOR HTTP
# =========================

async def home(request):
    return web.Response(
        text="TaticalTeam está online!"
    )


async def health(request):
    return web.Response(
        text="OK",
        status=200
    )


async def start_web_server():

    app = web.Application()

    # Página principal
    app.router.add_get("/", home)

    # Endpoint utilizado pelo UptimeRobot
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)

    await runner.setup()

    # Render fornece a porta através da variável PORT
    port = int(os.environ.get("PORT", 10000))

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    print("===================================")
    print(f"🌐 Servidor HTTP iniciado")
    print(f"🔌 Porta: {port}")
    print("❤️ Health check: /health")
    print("===================================")


# =========================
# EVENTOS DO BOT
# =========================

@bot.event
async def on_ready():

    print("===================================")
    print(f"✅ Bot conectado com sucesso!")
    print(f"🤖 Nome: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🌐 Servidores: {len(bot.guilds)}")
    print("===================================")


@bot.event
async def on_disconnect():

    print("⚠️ Bot desconectado do Discord.")


@bot.event
async def on_resumed():

    print("🔄 Conexão com o Discord restaurada.")


# =========================
# TRATAMENTO DE ERROS
# =========================

@bot.event
async def on_command_error(ctx, error):

    # Ignora comandos inexistentes
    if isinstance(error, commands.CommandNotFound):
        return

    print(f"❌ Erro em comando: {error}")


# =========================
# INICIALIZAÇÃO
# =========================

async def main():

    print("===================================")
    print("🚀 Iniciando TaticalTeam...")
    print("===================================")

    # Inicia o servidor HTTP
    await start_web_server()

    # Obtém o token da variável de ambiente
    token = os.environ.get("DISCORD_TOKEN")

    # Verifica se o token existe
    if not token:

        print("❌ ERRO: DISCORD_TOKEN não foi encontrada!")
        print("Configure DISCORD_TOKEN nas Environment Variables do Render.")

        return

    print("🔐 Token do Discord encontrado.")
    print("🔄 Conectando ao Discord...")

    try:

        await bot.start(token)

    except discord.LoginFailure:

        print("❌ ERRO: Token do Discord inválido!")

    except Exception as e:

        print(f"❌ Erro inesperado no bot: {e}")


# =========================
# EXECUÇÃO
# =========================

if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:

        print("🛑 Bot encerrado manualmente.")

    except Exception as e:

        print(f"❌ Erro fatal: {e}")
