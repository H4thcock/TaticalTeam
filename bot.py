import os
import sqlite3
import asyncio

import discord
from discord import app_commands
from discord.ext import commands

from aiohttp import web


# =========================================================
# CONFIGURAÇÕES
# =========================================================

TOKEN = os.getenv("DISCORD_TOKEN")

DATABASE = "team_kills.db"


# =========================================================
# BANCO DE DADOS
# =========================================================

def conectar_banco():
    return sqlite3.connect(DATABASE)


def criar_banco():

    banco = conectar_banco()
    cursor = banco.cursor()

    # Tabela responsável pelos Team Kills
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_kills (
            user_id INTEGER PRIMARY KEY,
            kills INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Tabela responsável pelo painel
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS painel (
            id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            channel_id INTEGER,
            message_id INTEGER
        )
    """)

    banco.commit()
    banco.close()


# =========================================================
# ADICIONAR TK
# =========================================================

def adicionar_tk(user_id):

    banco = conectar_banco()
    cursor = banco.cursor()

    cursor.execute("""
        INSERT INTO team_kills (user_id, kills)
        VALUES (?, 1)

        ON CONFLICT(user_id)
        DO UPDATE SET kills = kills + 1
    """, (user_id,))

    banco.commit()
    banco.close()


# =========================================================
# REMOVER TK
# =========================================================

def remover_tk(user_id):

    banco = conectar_banco()
    cursor = banco.cursor()

    cursor.execute("""
        UPDATE team_kills
        SET kills = CASE
            WHEN kills > 0 THEN kills - 1
            ELSE 0
        END
        WHERE user_id = ?
    """, (user_id,))

    banco.commit()
    banco.close()


# =========================================================
# OBTER RANKING
# =========================================================

def obter_ranking():

    banco = conectar_banco()
    cursor = banco.cursor()

    cursor.execute("""
        SELECT user_id, kills
        FROM team_kills
        WHERE kills > 0
        ORDER BY kills DESC
    """)

    resultado = cursor.fetchall()

    banco.close()

    return resultado


# =========================================================
# OBTER TOTAL DE TKs
# =========================================================

def obter_total():

    banco = conectar_banco()
    cursor = banco.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(kills), 0)
        FROM team_kills
    """)

    total = cursor.fetchone()[0]

    banco.close()

    return total


# =========================================================
# RESETAR TODOS OS TKs
# =========================================================

def resetar_tks():

    banco = conectar_banco()
    cursor = banco.cursor()

    cursor.execute("""
        DELETE FROM team_kills
    """)

    banco.commit()
    banco.close()


# =========================================================
# GERAR PAINEL
# =========================================================

async def gerar_painel():

    ranking = obter_ranking()
    total = obter_total()

    texto = ""

    if not ranking:

        texto = "Nenhum Team Kill registrado ainda."

    else:

        medalhas = ["🥇", "🥈", "🥉"]

        for posicao, (user_id, kills) in enumerate(ranking):

            try:

                usuario = await bot.fetch_user(user_id)

                nome = usuario.mention

            except discord.NotFound:

                nome = f"<@{user_id}>"

            if posicao < 3:

                medalha = medalhas[posicao]

            else:

                medalha = f"`{posicao + 1}º`"

            texto += (
                f"{medalha} {nome} — **{kills} TKs**\n"
            )

    embed = discord.Embed(
        title="💀 CONTROLE DE TEAM KILLS",
        description=texto,
        color=discord.Color.red()
    )

    embed.add_field(
        name="📊 Total de TKs",
        value=f"**{total}**",
        inline=False
    )

    embed.set_footer(
        text="Use /tk adicionar @usuario para registrar um TK."
    )

    return embed


# =========================================================
# ATUALIZAR PAINEL
# =========================================================

async def atualizar_painel():

    banco = conectar_banco()
    cursor = banco.cursor()

    cursor.execute("""
        SELECT guild_id, channel_id, message_id
        FROM painel
        WHERE id = 1
    """)

    dados = cursor.fetchone()

    banco.close()

    # Se ainda não existe painel configurado
    if not dados:
        return

    guild_id, channel_id, message_id = dados

    canal = bot.get_channel(channel_id)

    if canal is None:
        return

    try:

        mensagem = await canal.fetch_message(message_id)

        embed = await gerar_painel()

        await mensagem.edit(embed=embed)

    except discord.NotFound:

        # Se o painel antigo foi apagado,
        # cria outro automaticamente.

        embed = await gerar_painel()

        mensagem = await canal.send(
            embed=embed
        )

        banco = conectar_banco()
        cursor = banco.cursor()

        cursor.execute("""
            UPDATE painel
            SET message_id = ?
            WHERE id = 1
        """, (mensagem.id,))

        banco.commit()
        banco.close()


# =========================================================
# BOT
# =========================================================

class TaticalTeam(commands.Bot):

    def __init__(self):

        intents = discord.Intents.all()

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):

        criar_banco()

        await self.tree.sync()

        print("✅ Comandos sincronizados!")


bot = TaticalTeam()


# =========================================================
# BOT ONLINE
# =========================================================

@bot.event
async def on_ready():

    print(
        f"✅ {bot.user} está online!"
    )


# =========================================================
# GRUPO /TK
# =========================================================

tk = app_commands.Group(
    name="tk",
    description="Sistema de controle de Team Kills."
)


# =========================================================
# /TK ADICIONAR
# =========================================================
# PERMISSÃO: TODOS
# =========================================================

@tk.command(
    name="adicionar",
    description="Adiciona 1 Team Kill para um jogador."
)
async def tk_adicionar(
    interaction: discord.Interaction,
    jogador: discord.Member
):

    adicionar_tk(jogador.id)

    await atualizar_painel()

    await interaction.response.send_message(
        f"💀 **+1 TK** registrado para {jogador.mention}!",
        ephemeral=True
    )


# =========================================================
# /TK REMOVER
# =========================================================
# PERMISSÃO: SOMENTE ADMINISTRADORES
# =========================================================

@tk.command(
    name="remover",
    description="Remove 1 Team Kill de um jogador."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def tk_remover(
    interaction: discord.Interaction,
    jogador: discord.Member
):

    remover_tk(jogador.id)

    await atualizar_painel()

    await interaction.response.send_message(
        f"↩️ **-1 TK** removido de {jogador.mention}!",
        ephemeral=True
    )


# =========================================================
# /TK PAINEL
# =========================================================
# PERMISSÃO: SOMENTE ADMINISTRADORES
# =========================================================

@tk.command(
    name="painel",
    description="Cria ou fixa o painel de Team Kills neste canal."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def tk_painel(
    interaction: discord.Interaction
):

    embed = await gerar_painel()

    mensagem = await interaction.channel.send(
        embed=embed
    )

    banco = conectar_banco()
    cursor = banco.cursor()

    cursor.execute("""
        INSERT INTO painel (
            id,
            guild_id,
            channel_id,
            message_id
        )

        VALUES (1, ?, ?, ?)

        ON CONFLICT(id)
        DO UPDATE SET
            guild_id = excluded.guild_id,
            channel_id = excluded.channel_id,
            message_id = excluded.message_id
    """, (
        interaction.guild.id,
        interaction.channel.id,
        mensagem.id
    ))

    banco.commit()
    banco.close()

    await interaction.response.send_message(
        "✅ Painel de Team Kills configurado neste canal!",
        ephemeral=True
    )


# =========================================================
# /TK RANKING
# =========================================================
# PERMISSÃO: TODOS
# =========================================================

@tk.command(
    name="ranking",
    description="Mostra o ranking de Team Kills."
)
async def tk_ranking(
    interaction: discord.Interaction
):

    embed = await gerar_painel()

    await interaction.response.send_message(
        embed=embed
    )


# =========================================================
# /TK RESET
# =========================================================
# PERMISSÃO: SOMENTE ADMINISTRADORES
# =========================================================

@tk.command(
    name="reset",
    description="Zera todos os Team Kills."
)
@app_commands.checks.has_permissions(
    administrator=True
)
async def tk_reset(
    interaction: discord.Interaction
):

    resetar_tks()

    await atualizar_painel()

    await interaction.response.send_message(
        "🗑️ **Todos os Team Kills foram zerados!**"
    )


# =========================================================
# ADICIONAR GRUPO /TK AO BOT
# =========================================================

bot.tree.add_command(tk)


# =========================================================
# TRATAMENTO DE ERROS DOS COMANDOS
# =========================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    if isinstance(
        error,
        app_commands.MissingPermissions
    ):

        await interaction.response.send_message(
            "❌ Você não tem permissão para utilizar esse comando.",
            ephemeral=True
        )

        return

    print(
        f"❌ Erro: {error}"
    )


# =========================================================
# SERVIDOR WEB PARA O RENDER
# =========================================================

async def health_check(request):

    return web.Response(
        text="Tatical Team está online!"
    )


async def iniciar_servidor_web():

    app = web.Application()

    app.router.add_get(
        "/",
        health_check
    )

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(
        os.getenv(
            "PORT",
            10000
        )
    )

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()


# =========================================================
# INICIAR BOT
# =========================================================

async def main():

    await iniciar_servidor_web()

    await bot.start(TOKEN)


# =========================================================
# EXECUTAR
# =========================================================

asyncio.run(main())
