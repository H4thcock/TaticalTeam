import os
import asyncio
import sqlite3

from aiohttp import web

import discord
from discord import app_commands
from discord.ext import commands


# ============================================================
# CONFIGURAÇÕES
# ============================================================

DATABASE = "team_kills.db"


# ============================================================
# BANCO DE DADOS
# ============================================================

def conectar_banco():
    return sqlite3.connect(DATABASE)


def iniciar_banco():

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_kills (
            user_id INTEGER PRIMARY KEY,
            username TEXT NOT NULL,
            kills INTEGER NOT NULL DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS painel (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            channel_id INTEGER,
            message_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS team_kills_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            target_user_id INTEGER NOT NULL,
            target_username TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            executor_user_id INTEGER NOT NULL,
            executor_username TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def adicionar_kill(user_id, username, quantidade=1):

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO team_kills (user_id, username, kills)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            username = excluded.username,
            kills = kills + excluded.kills
    """, (user_id, username, quantidade))

    conn.commit()
    conn.close()


def remover_kill(user_id, quantidade=1):

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT kills
        FROM team_kills
        WHERE user_id = ?
    """, (user_id,))

    resultado = cursor.fetchone()

    if resultado is None:
        conn.close()
        return 0

    kills_atual = resultado[0]

    nova_quantidade = max(0, kills_atual - quantidade)

    cursor.execute("""
        UPDATE team_kills
        SET kills = ?
        WHERE user_id = ?
    """, (nova_quantidade, user_id))

    conn.commit()
    conn.close()

    return nova_quantidade


def registrar_auditoria(
    action,
    target_user_id,
    target_username,
    quantity,
    executor_user_id,
    executor_username
):
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO team_kills_audit (
            action,
            target_user_id,
            target_username,
            quantity,
            executor_user_id,
            executor_username,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
    """, (
        action,
        target_user_id,
        target_username,
        quantity,
        executor_user_id,
        executor_username
    ))

    conn.commit()
    conn.close()


def obter_auditoria(limite=20):
    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            action,
            target_user_id,
            target_username,
            quantity,
            executor_user_id,
            executor_username,
            created_at
        FROM team_kills_audit
        ORDER BY id DESC
        LIMIT ?
    """, (limite,))

    resultados = cursor.fetchall()
    conn.close()

    return resultados


def resetar_kills():

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM team_kills")

    conn.commit()
    conn.close()


def obter_ranking():

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_id, username, kills
        FROM team_kills
        WHERE kills > 0
        ORDER BY kills DESC, username ASC
    """)

    resultados = cursor.fetchall()

    conn.close()

    return resultados


def salvar_painel(channel_id, message_id):

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO painel (id, channel_id, message_id)
        VALUES (1, ?, ?)
        ON CONFLICT(id)
        DO UPDATE SET
            channel_id = excluded.channel_id,
            message_id = excluded.message_id
    """, (channel_id, message_id))

    conn.commit()
    conn.close()


def obter_painel():

    conn = conectar_banco()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT channel_id, message_id
        FROM painel
        WHERE id = 1
    """)

    resultado = cursor.fetchone()

    conn.close()

    return resultado


# ============================================================
# EMBED DO PAINEL
# ============================================================

def criar_embed_ranking():

    ranking = obter_ranking()

    embed = discord.Embed(
        title="🎯 TEAM KILLS",
        description=(
            "Ranking de Team Kills da equipe.\n\n"
            "Use `/tk adicionar` para registrar uma Team Kill."
        ),
        color=discord.Color.green()
    )

    if not ranking:

        embed.add_field(
            name="📊 Ranking",
            value="Nenhuma Team Kill registrada.",
            inline=False
        )

    else:

        linhas = []

        for posicao, (user_id, username, kills) in enumerate(ranking, start=1):

            if posicao == 1:
                medalha = "🥇"
            elif posicao == 2:
                medalha = "🥈"
            elif posicao == 3:
                medalha = "🥉"
            else:
                medalha = f"`{posicao}.`"

            linhas.append(
                f"{medalha} **{username}** — `{kills}` TK"
            )

        embed.add_field(
            name="📊 Ranking",
            value="\n".join(linhas),
            inline=False
        )

    total = sum(kills for _, _, kills in ranking)

    embed.add_field(
        name="💀 Total de Team Kills",
        value=f"**{total}**",
        inline=False
    )

    embed.set_footer(
        text="Tatical Team • Sistema de Team Kills"
    )

    return embed


# ============================================================
# ATUALIZAR PAINEL
# ============================================================

async def atualizar_painel():

    painel = obter_painel()

    if not painel:
        return

    channel_id, message_id = painel

    try:

        channel = bot.get_channel(channel_id)

        if channel is None:

            channel = await bot.fetch_channel(channel_id)

        message = await channel.fetch_message(message_id)

        await message.edit(
            embed=criar_embed_ranking()
        )

    except discord.NotFound:

        print("⚠️ O painel salvo não existe mais.")

    except discord.Forbidden:

        print("❌ Não tenho permissão para atualizar o painel.")

    except Exception as e:

        print(f"❌ Erro ao atualizar painel: {e}")


# ============================================================
# BOT
# ============================================================

class TaticalTeam(commands.Bot):

    def __init__(self):

        intents = discord.Intents.all()

        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):

        print("🔄 Sincronizando comandos...")

        try:

            # Sincronização global
            comandos = await self.tree.sync()

            print(
                f"✅ {len(comandos)} comandos globais sincronizados."
            )

            # ==================================================
            # SINCRONIZAÇÃO IMEDIATA PARA SERVIDOR DE TESTE
            # ==================================================

            guild_id = os.environ.get("DISCORD_GUILD_ID")

            if guild_id:

                try:

                    guild = discord.Object(
                        id=int(guild_id)
                    )

                    self.tree.copy_global_to(
                        guild=guild
                    )

                    comandos_guild = await self.tree.sync(
                        guild=guild
                    )

                    print(
                        f"✅ {len(comandos_guild)} comandos "
                        f"sincronizados no servidor de teste."
                    )

                except Exception as e:

                    print(
                        f"⚠️ Erro ao sincronizar servidor: {e}"
                    )

        except Exception as e:

            print(
                f"❌ Erro ao sincronizar comandos: {e}"
            )


bot = TaticalTeam()


# ============================================================
# GRUPO /TK
# ============================================================

tk = app_commands.Group(
    name="tk",
    description="Sistema de Team Kills"
)


# ============================================================
# /TK ADICIONAR
# QUALQUER USUÁRIO PODE USAR
# ============================================================

@tk.command(
    name="adicionar",
    description="Adiciona Team Kill para um jogador."
)
@app_commands.describe(
    jogador="Jogador que recebeu a Team Kill.",
    quantidade="Quantidade de Team Kills a adicionar."
)
async def tk_adicionar(
    interaction: discord.Interaction,
    jogador: discord.Member,
    quantidade: int = 1
):

    if quantidade < 1:

        await interaction.response.send_message(
            "❌ A quantidade precisa ser maior que zero.",
            ephemeral=True
        )

        return

    adicionar_kill(
        jogador.id,
        jogador.display_name,
        quantidade
    )

    registrar_auditoria(
        "ADICIONOU",
        jogador.id,
        jogador.display_name,
        quantidade,
        interaction.user.id,
        interaction.user.display_name
    )

    await atualizar_painel()

    await interaction.response.send_message(
        f"✅ **{quantidade}** Team Kill(s) adicionada(s) "
        f"para {jogador.mention}.",
        ephemeral=True
    )


# ============================================================
# /TK RANKING
# QUALQUER USUÁRIO PODE USAR
# ============================================================

@tk.command(
    name="ranking",
    description="Mostra o ranking de Team Kills."
)
async def tk_ranking(
    interaction: discord.Interaction
):

    await interaction.response.send_message(
        embed=criar_embed_ranking()
    )


# ============================================================
# /TK PAINEL
# SOMENTE ADMINISTRADORES
# ============================================================

@tk.command(
    name="painel",
    description="Cria e fixa um novo painel de Team Kills."
)
@app_commands.default_permissions(administrator=True)
async def tk_painel(
    interaction: discord.Interaction
):

    # SEGURANÇA
    # Verificação real da permissão Administrator
    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(
            "❌ Você precisa ser **Administrador** "
            "para criar um painel.",
            ephemeral=True
        )

        return

    await interaction.response.defer(
        ephemeral=True
    )

    embed = criar_embed_ranking()

    try:

        mensagem = await interaction.channel.send(
            embed=embed
        )

        salvar_painel(
            interaction.channel.id,
            mensagem.id
        )

        # Tenta fixar o painel
        try:

            await mensagem.pin()

            painel_status = "📌 Painel criado e fixado com sucesso!"

        except discord.Forbidden:

            painel_status = (
                "⚠️ Painel criado, mas não consegui fixá-lo. "
                "Verifique a permissão **Gerenciar Mensagens**."
            )

        await interaction.followup.send(
            f"✅ {painel_status}",
            ephemeral=True
        )

    except discord.Forbidden:

        await interaction.followup.send(
            "❌ Não tenho permissão para enviar mensagens "
            "neste canal.",
            ephemeral=True
        )

    except Exception as e:

        print(f"❌ Erro ao criar painel: {e}")

        await interaction.followup.send(
            "❌ Ocorreu um erro ao criar o painel.",
            ephemeral=True
        )


# ============================================================
# /TK REMOVER
# SOMENTE ADMINISTRADORES
# ============================================================

@tk.command(
    name="remover",
    description="Remove Team Kills de um jogador."
)
@app_commands.describe(
    jogador="Jogador que terá Team Kills removidas.",
    quantidade="Quantidade de Team Kills a remover."
)
@app_commands.default_permissions(administrator=True)
async def tk_remover(
    interaction: discord.Interaction,
    jogador: discord.Member,
    quantidade: int = 1
):

    # SEGURANÇA
    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(
            "❌ Você precisa ser **Administrador** "
            "para remover Team Kills.",
            ephemeral=True
        )

        return

    if quantidade < 1:

        await interaction.response.send_message(
            "❌ A quantidade precisa ser maior que zero.",
            ephemeral=True
        )

        return

    # Descobre quantos TKs realmente existiam antes da remoção.
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT kills FROM team_kills WHERE user_id = ?",
        (jogador.id,)
    )
    resultado_anterior = cursor.fetchone()
    conn.close()

    kills_antes = resultado_anterior[0] if resultado_anterior else 0
    quantidade_real_removida = min(quantidade, kills_antes)

    nova_quantidade = remover_kill(
        jogador.id,
        quantidade
    )

    # Só registra a quantidade que realmente foi removida.
    if quantidade_real_removida > 0:
        registrar_auditoria(
            "REMOVEU",
            jogador.id,
            jogador.display_name,
            quantidade_real_removida,
            interaction.user.id,
            interaction.user.display_name
        )

    await atualizar_painel()

    if quantidade_real_removida == 0:
        mensagem_remocao = (
            f"⚠️ {jogador.mention} não possui Team Kills para remover.\n\n"
            f"📊 Total atual: **{nova_quantidade}**"
        )
    elif quantidade_real_removida < quantidade:
        mensagem_remocao = (
            f"🗑️ Foram removidas **{quantidade_real_removida}** Team Kill(s) "
            f"de {jogador.mention}.\n\n"
            f"⚠️ Foram solicitadas **{quantidade}**, mas o jogador possuía "
            f"apenas **{quantidade_real_removida}**.\n\n"
            f"📊 Total atual: **{nova_quantidade}**"
        )
    else:
        mensagem_remocao = (
            f"🗑️ Foram removidas **{quantidade_real_removida}** Team Kill(s) "
            f"de {jogador.mention}.\n\n"
            f"📊 Total atual: **{nova_quantidade}**"
        )

    await interaction.response.send_message(
        mensagem_remocao,
        ephemeral=True
    )


# ============================================================
# /TK AUDITORIA
# SOMENTE ADMINISTRADORES
# ============================================================

@tk.command(
    name="auditoria",
    description="Mostra o histórico de adições e remoções de Team Kills."
)
@app_commands.default_permissions(administrator=True)
async def tk_auditoria(
    interaction: discord.Interaction
):
    # SEGURANÇA
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Você precisa ser **Administrador** para consultar a auditoria.",
            ephemeral=True
        )
        return

    registros = obter_auditoria(20)

    embed = discord.Embed(
        title="📋 AUDITORIA — TEAM KILLS",
        description="Últimas alterações registradas no sistema.",
        color=discord.Color.blurple()
    )

    if not registros:
        embed.add_field(
            name="📊 Histórico",
            value="Nenhuma adição ou remoção foi registrada ainda.",
            inline=False
        )
    else:
        linhas = []

        for (
            action,
            target_user_id,
            target_username,
            quantity,
            executor_user_id,
            executor_username,
            created_at
        ) in registros:
            if action == "ADICIONOU":
                icone = "🟢"
                sinal = "+"
            else:
                icone = "🔴"
                sinal = "-"

            linhas.append(
                f"{icone} **{action}** `{sinal}{quantity}` TK\n"
                f"🎯 Jogador: **{target_username}** "
                f"(<@{target_user_id}>)\n"
                f"👮 Responsável: **{executor_username}** "
                f"(<@{executor_user_id}>)\n"
                f"🕐 `{created_at}`"
            )

        embed.add_field(
            name="📜 Registros",
            value="\n\n".join(linhas),
            inline=False
        )

    embed.set_footer(
        text="Tatical Team • Auditoria de Team Kills • Últimos 20 registros"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# /TK RESET
# SOMENTE ADMINISTRADORES
# ============================================================

@tk.command(
    name="reset",
    description="Reseta todas as Team Kills."
)
@app_commands.default_permissions(administrator=True)
async def tk_reset(
    interaction: discord.Interaction
):

    # SEGURANÇA
    if not interaction.user.guild_permissions.administrator:

        await interaction.response.send_message(
            "❌ Você precisa ser **Administrador** "
            "para resetar o contador.",
            ephemeral=True
        )

        return

    resetar_kills()

    await atualizar_painel()

    await interaction.response.send_message(
        "♻️ **Todos os contadores de Team Kills foram resetados.**",
        ephemeral=True
    )


# ============================================================
# REGISTRA O GRUPO /TK
# ============================================================

bot.tree.add_command(tk)


# ============================================================
# SERVIDOR HTTP — RENDER / UPTIMEROBOT
# ============================================================

async def home(request):

    return web.Response(
        text="TaticalTeam está online!",
        status=200
    )


async def health(request):

    return web.Response(
        text="OK",
        status=200
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        home
    )

    app.router.add_get(
        "/health",
        health
    )

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(
        os.environ.get(
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

    print("======================================")
    print("🌐 SERVIDOR HTTP INICIADO")
    print(f"🔌 Porta: {port}")
    print("❤️ Health check: /health")
    print("======================================")


# ============================================================
# EVENTOS DO BOT
# ============================================================

@bot.event
async def on_ready():

    print("======================================")
    print("✅ BOT CONECTADO AO DISCORD")
    print(f"🤖 Nome: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🌐 Servidores: {len(bot.guilds)}")
    print("======================================")


@bot.event
async def on_disconnect():

    print("⚠️ Bot desconectado do Discord.")


@bot.event
async def on_resumed():

    print("🔄 Conexão com Discord restaurada.")


@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):

        return

    print(
        f"❌ Erro em comando prefixado: {error}"
    )


# ============================================================
# TRATAMENTO DE ERROS DOS SLASH COMMANDS
# ============================================================

@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):

    print(
        f"❌ Erro em slash command: {error}"
    )

    try:

        if interaction.response.is_done():

            await interaction.followup.send(
                "❌ Ocorreu um erro ao executar o comando.",
                ephemeral=True
            )

        else:

            await interaction.response.send_message(
                "❌ Ocorreu um erro ao executar o comando.",
                ephemeral=True
            )

    except Exception as e:

        print(
            f"❌ Não foi possível enviar mensagem de erro: {e}"
        )


# ============================================================
# INICIALIZAÇÃO
# ============================================================

async def main():

    print("======================================")
    print("🚀 INICIANDO TATICAL TEAM")
    print("======================================")

    # Banco
    iniciar_banco()

    print("🗄️ Banco de dados iniciado.")

    # Servidor HTTP
    await start_web_server()

    # Token
    token = os.environ.get(
        "DISCORD_TOKEN"
    )

    if not token:

        print("======================================")
        print("❌ ERRO CRÍTICO")
        print("❌ DISCORD_TOKEN não foi encontrada.")
        print("======================================")

        return

    print("🔐 Token do Discord encontrado.")
    print("🔄 Conectando ao Discord...")

    try:

        await bot.start(token)

    except discord.LoginFailure:

        print("❌ TOKEN DO DISCORD INVÁLIDO.")

    except Exception as e:

        print(
            f"❌ Erro inesperado: {e}"
        )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print("🛑 Bot encerrado manualmente.")

    except Exception as e:

        print(
            f"❌ ERRO FATAL: {e}"
        )
