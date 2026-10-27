"""Bot de Discord: boas-vindas com imagem, botões e comandos híbridos."""

import hashlib
import io
import json
import math
import os
import re
import random
import unicodedata
from datetime import timedelta
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

# --------------------------------------------------------------- caminhos

BASE_DIR = Path(__file__).resolve().parent
PASTA_IMAGENS = BASE_DIR / "imagens"

IMAGEM_POSSO_FALAR = PASTA_IMAGENS / "eu vou fala.jpg"
IMAGEM_NAO_POSSO_FALAR = PASTA_IMAGENS / "nao me deixaram falar.jpg"

CANAL_BOAS_VINDAS_PADRAO = 1557946258973270117
CANAL_NOVIDADES_PADRAO = 1557946258973270120

CAMINHO_CHANGELOG = BASE_DIR / "CHANGELOG.md"
CAMINHO_ULTIMA_NOVIDADE = BASE_DIR / "logs" / "ultima_novidade.txt"
CAMINHO_AUTOMOD = BASE_DIR / "logs" / "automod.json"

CARGO_AUTOMOD = "automod"
MENSAGEM_AUTOMOD = "Ei! {mencao} você não pode falar isto!"

COR_FUNDO_INICIO = (28, 33, 74)
COR_FUNDO_FIM = (96, 45, 129)


def carregar_env(caminho: Path) -> None:
    """Lê o arquivo .env sem depender de biblioteca externa."""

    if not caminho.is_file():
        return

    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()

        if not linha or linha.startswith("#") or "=" not in linha:
            continue

        chave, _, valor = linha.partition("=")
        os.environ.setdefault(chave.strip(), valor.strip().strip("\"'"))


carregar_env(BASE_DIR / ".env")


def ler_canal_boas_vindas() -> int:
    valor = os.getenv("CANAL_BOAS_VINDAS", "").strip()

    if not valor:
        return CANAL_BOAS_VINDAS_PADRAO

    try:
        return int(valor)
    except ValueError:
        print(f"CANAL_BOAS_VINDAS inválido ({valor!r}); usando o padrão.")

    return CANAL_BOAS_VINDAS_PADRAO


def ler_canal_novidades() -> int:
    valor = os.getenv("CANAL_NOVIDADES", "").strip()

    if not valor:
        return CANAL_NOVIDADES_PADRAO

    try:
        return int(valor)
    except ValueError:
        print(f"CANAL_NOVIDADES inválido ({valor!r}); usando o padrão.")

    return CANAL_NOVIDADES_PADRAO


TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
CANAL_BOAS_VINDAS = ler_canal_boas_vindas()
CANAL_NOVIDADES = ler_canal_novidades()

# -------------------------------------------------------------------- bot

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents, help_command=None)


@bot.event
async def on_ready():
    try:
        sincronizados = await bot.tree.sync()
        print(f"Sincronizado {len(sincronizados)} comandos!")
    except discord.HTTPException as erro:
        print(f"Falha ao sincronizar os comandos: {erro}")

    print(f"{bot.user} está online!")

    _palavras_automod[:] = carregar_palavras_automod()
    print(f"Automod: {len(_palavras_automod)} palavra(s) bloqueada(s).")

    await enviar_novidades_automaticamente(bot)


# --------------------------------------------------------------- imagens


FONTES_CONHECIDAS = (
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
)

NOMES_DE_FONTE = (
    "DejaVuSans-Bold.ttf",
    "LiberationSans-Bold.ttf",
    "NotoSans-Bold.ttf",
)


def carregar_fonte(tamanho: int) -> ImageFont.ImageFont:
    """Carrega uma fonte do sistema e cai para a padrão se não encontrar."""

    for caminho in FONTES_CONHECIDAS:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except OSError:
            continue

    # Cada distro guarda as fontes num lugar: no Arch/CachyOS é
    # /usr/share/fonts/TTF, então o último recurso é procurar pelo nome.
    pasta_fontes = Path("/usr/share/fonts")

    if pasta_fontes.is_dir():
        for nome in NOMES_DE_FONTE:
            for achada in sorted(pasta_fontes.rglob(nome)):
                try:
                    return ImageFont.truetype(str(achada), tamanho)
                except OSError:
                    continue

    return ImageFont.load_default(size=tamanho)


def encurtar_texto(
    texto: str,
    fonte: ImageFont.ImageFont,
    largura_maxima: int
) -> str:
    """Corta o texto com reticências se ele passar da largura disponível."""

    if fonte.getlength(texto) <= largura_maxima:
        return texto

    while texto and fonte.getlength(texto + "…") > largura_maxima:
        texto = texto[:-1]

    return texto + "…"


def criar_fundo(largura: int, altura: int) -> Image.Image:
    """Fundo em degradê vertical do azul-escuro para o roxo."""

    fundo = Image.new("RGB", (largura, altura))
    desenho = ImageDraw.Draw(fundo)

    for y in range(altura):
        proporcao = y / max(altura - 1, 1)
        cor = tuple(
            int(c_inicio + (c_fim - c_inicio) * proporcao)
            for c_inicio, c_fim in zip(COR_FUNDO_INICIO, COR_FUNDO_FIM)
        )
        desenho.line(((0, y), (largura, y)), fill=cor)

    return fundo


async def carregar_avatar(member: discord.Member, tamanho: int):
    """Baixa o avatar do membro já cortado em círculo."""

    try:
        dados = await member.display_avatar.replace(
            size=256,
            format="png"
        ).read()
        avatar = Image.open(io.BytesIO(dados)).convert("RGBA")
        avatar = avatar.resize((tamanho, tamanho), Image.LANCZOS)
    except (discord.HTTPException, OSError):
        avatar = Image.new("RGBA", (tamanho, tamanho), (60, 60, 80, 255))

    mascara = Image.new("L", (tamanho, tamanho), 0)
    ImageDraw.Draw(mascara).ellipse(
        (0, 0, tamanho - 1, tamanho - 1),
        fill=255
    )

    return avatar, mascara


async def criar_imagem(member: discord.Member) -> Image.Image:
    """Monta o cartão de boas-vindas do membro."""

    largura, altura = 900, 320
    tamanho_avatar = 180
    x_avatar = 60
    y_avatar = (altura - tamanho_avatar) // 2

    imagem = criar_fundo(largura, altura)
    desenho = ImageDraw.Draw(imagem)

    avatar, mascara = await carregar_avatar(member, tamanho_avatar)

    desenho.ellipse(
        (
            x_avatar - 8,
            y_avatar - 8,
            x_avatar + tamanho_avatar + 8,
            y_avatar + tamanho_avatar + 8
        ),
        outline=(255, 255, 255),
        width=6
    )

    imagem.paste(avatar, (x_avatar, y_avatar), mascara)

    fonte_titulo = carregar_fonte(48)
    fonte_subtitulo = carregar_fonte(26)
    fonte_pequena = carregar_fonte(22)

    x_texto = x_avatar + tamanho_avatar + 45
    largura_texto = largura - x_texto - 40

    nome = encurtar_texto(member.display_name, fonte_titulo, largura_texto)

    membros = member.guild.member_count if member.guild else None

    if membros:
        linha_membros = f"Você é o membro nº {membros}"
    else:
        linha_membros = "Que bom ter você aqui!"

    desenho.text(
        (x_texto, 70),
        "BEM-VINDO(A)!",
        font=fonte_subtitulo,
        fill=(255, 215, 120)
    )

    desenho.text((x_texto, 108), nome, font=fonte_titulo, fill="white")

    desenho.text(
        (x_texto, 185),
        linha_membros,
        font=fonte_pequena,
        fill=(215, 215, 235)
    )

    desenho.text(
        (x_texto, 218),
        "Leia as regras e divirta-se!",
        font=fonte_pequena,
        fill=(215, 215, 235)
    )

    return imagem


def criar_arquivo(caminho: Path, nome_arquivo: str) -> discord.File:
    """Cria o anexo a partir de um arquivo local."""

    return discord.File(caminho, filename=nome_arquivo)


@bot.event
async def on_member_join(member: discord.Member):
    canal = bot.get_channel(CANAL_BOAS_VINDAS)

    if not isinstance(canal, discord.abc.Messageable):
        print(f"Canal de boas-vindas {CANAL_BOAS_VINDAS} não encontrado.")
        return

    try:
        imagem = await criar_imagem(member)
        buffer = io.BytesIO()
        imagem.save(buffer, format="PNG")
        buffer.seek(0)

        await canal.send(
            f"Bem-vindo(a) {member.mention} ao servidor! "
            "Veja as regras e divirta-se!",
            file=discord.File(buffer, filename="bem-vindo.png")
        )
    except (discord.HTTPException, OSError) as erro:
        print(f"Falha ao enviar a mensagem de boas-vindas: {erro!r}")


# ------------------------------------------------- comandos com prefixo


@bot.command()
async def teste(ctx: commands.Context):
    await ctx.reply("Teste realizado com sucesso!")


@bot.command()
async def enviar_embed(ctx: commands.Context, *, texto: str = ""):
    embed = discord.Embed(
        title="📨 Embed de teste",
        description=texto or "Este é um embed enviado pelo bot!",
        color=discord.Color.purple()
    )

    embed.set_footer(text=f"Enviado por {ctx.author.display_name}")
    embed.timestamp = discord.utils.utcnow()

    await ctx.reply(embed=embed)


def montar_embed_novidades() -> discord.Embed:
    """Monta o embed de novidades a partir do CHANGELOG.md."""

    texto = CAMINHO_CHANGELOG.read_text(encoding="utf-8")

    titulo = "Novidades do bot"
    descricao = ""
    campos: list[tuple[str, str]] = []
    nome_campo = ""
    linhas_campo: list[str] = []

    def fechar_campo() -> None:
        if nome_campo and linhas_campo:
            campos.append((nome_campo[:256], "\n".join(linhas_campo)[:1024]))

    for linha in texto.splitlines():
        limpa = linha.strip()

        if limpa.startswith("# "):
            titulo = limpa[2:].strip()
        elif limpa.startswith("## "):
            if descricao:
                break  # só a atualização mais recente interessa

            descricao = limpa[3:].strip()
        elif limpa.startswith("### "):
            fechar_campo()
            nome_campo = limpa[4:].strip()
            linhas_campo = []
        elif limpa and limpa != "---" and nome_campo:
            linhas_campo.append(limpa)

    fechar_campo()

    embed = discord.Embed(
        title=titulo[:256],
        description=descricao[:4096],
        color=discord.Color.purple()
    )

    for nome, valor in campos[:25]:
        embed.add_field(name=nome, value=valor, inline=False)

    embed.set_footer(text="BOB BOT — use /ajuda para ver os comandos")

    return embed


def assinatura_ultima_atualizacao() -> str:
    """Resume a atualização mais recente do CHANGELOG.md num hash curto."""

    try:
        texto = CAMINHO_CHANGELOG.read_text(encoding="utf-8")
    except OSError:
        return ""

    linhas: list[str] = []
    achou_entrada = False

    for linha in texto.splitlines():
        if linha.strip().startswith("## "):
            if achou_entrada:
                break

            achou_entrada = True
            continue

        if achou_entrada:
            linhas.append(linha.strip())

    recorte = "\n".join(linhas).strip() if achou_entrada else texto.strip()

    if not recorte:
        return ""

    return hashlib.sha256(recorte.encode("utf-8")).hexdigest()


async def enviar_novidades_automaticamente(bot_instancia: commands.Bot) -> None:
    """Posta o /novidades quando a atualização mais recente do CHANGELOG muda."""

    assinatura = assinatura_ultima_atualizacao()

    if not assinatura:
        print("CHANGELOG.md vazio ou ausente; nada a enviar.")
        return

    try:
        anterior = CAMINHO_ULTIMA_NOVIDADE.read_text(encoding="utf-8").strip()
    except OSError:
        anterior = ""

    if anterior == assinatura:
        return

    canal = bot_instancia.get_channel(CANAL_NOVIDADES)

    if canal is None:
        print(
            f"Canal de novidades {CANAL_NOVIDADES} não encontrado; "
            "tento de novo na próxima vez que o bot iniciar."
        )
        return

    try:
        embed = montar_embed_novidades()
        await canal.send(embed=embed)
    except (OSError, discord.HTTPException) as erro:
        print(f"Falha ao enviar as novidades automáticas: {erro}")
        return

    try:
        CAMINHO_ULTIMA_NOVIDADE.parent.mkdir(parents=True, exist_ok=True)
        CAMINHO_ULTIMA_NOVIDADE.write_text(assinatura + "\n", encoding="utf-8")
    except OSError as erro:
        print(f"Não foi possível guardar o marcador das novidades: {erro}")

    print(f"Novidades enviadas no canal {CANAL_NOVIDADES}.")


# ------------------------------- comandos híbridos (slash e prefixo ?)


@bot.hybrid_command(name="ola", description="Comando de teste")
async def ola(ctx: commands.Context):
    await ctx.reply(
        f"Olá! Eu sou um bot de teste {ctx.author.name}!",
        ephemeral=True
    )

    await ctx.send(
        f"Olá novamente, {ctx.author.name}, "
        "seu comando foi executado!",
        ephemeral=True
    )


class PossoFalarView(discord.ui.View):
    """Botões que respondem se o usuário pode falar."""

    def __init__(self, autor_id: int):
        super().__init__(timeout=120)
        self.autor_id = autor_id

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.user.id != self.autor_id:
            await interaction.response.send_message(
                "Só quem usou o comando pode escolher!",
                ephemeral=True
            )
            return False

        return True

    async def responder(
        self,
        interaction: discord.Interaction,
        caminho: Path,
        nome_arquivo: str,
        descricao: str,
        cor: discord.Color
    ):
        if not caminho.is_file():
            await interaction.response.send_message(
                f"Imagem não encontrada: `imagens/{caminho.name}`.",
                ephemeral=True
            )
            return

        embed = discord.Embed(description=descricao, color=cor)
        embed.set_image(url=f"attachment://{nome_arquivo}")

        await interaction.response.send_message(
            embed=embed,
            file=criar_arquivo(caminho, nome_arquivo)
        )

        if interaction.message is not None:
            # Tirar os botões é cortesia: a resposta acima já foi enviada,
            # então um recuso do Discord aqui (canal sem acesso, mensagem
            # apagada) não pode derrubar o clique nem virar erro no log.
            try:
                await interaction.message.edit(view=None)
            except discord.HTTPException as erro:
                print(f"Não consegui tirar os botões da mensagem: {erro}")

        self.stop()

    @discord.ui.button(
        label="Sim",
        style=discord.ButtonStyle.success,
        emoji="✅"
    )
    async def sim(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.responder(
            interaction,
            IMAGEM_POSSO_FALAR,
            "imagem_sim.jpg",
            "**me deixaram falar!**",
            discord.Color.green()
        )

    @discord.ui.button(
        label="Não",
        style=discord.ButtonStyle.danger,
        emoji="❌"
    )
    async def nao(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await self.responder(
            interaction,
            IMAGEM_NAO_POSSO_FALAR,
            "imagem_nao.jpg",
            "**não me deixaram falar!**",
            discord.Color.red()
        )


@bot.hybrid_command(
    name="oi_posso_falar",
    description="Pergunta se pode falar"
)
async def oi_posso_falar(ctx: commands.Context):
    await ctx.reply(
        f"Oi, posso falar, {ctx.author.mention}?",
        view=PossoFalarView(ctx.author.id)
    )


@bot.hybrid_command(name="ping", description="Mostra a latência do bot")
async def ping(ctx: commands.Context):
    latencia = bot.latency

    if math.isnan(latencia):
        await ctx.reply(
            "🏓 Pong! Ainda estou conectando, tente de novo em instantes."
        )
        return

    await ctx.reply(f"🏓 Pong! Latência: **{round(latencia * 1000)} ms**")


@bot.hybrid_command(
    name="avatar",
    description="Mostra o avatar de um membro"
)
@app_commands.describe(membro="Quem você quer ver (padrão: você)")
async def avatar(
    ctx: commands.Context,
    membro: discord.Member | None = None
):
    membro = membro or ctx.author

    embed = discord.Embed(
        title=f"Avatar de {membro.display_name}",
        color=discord.Color.blurple()
    )

    embed.set_image(url=membro.display_avatar.replace(size=1024).url)

    await ctx.reply(embed=embed)


@bot.hybrid_command(name="dado", description="Rola um dado")
@app_commands.describe(lados="Quantos lados o dado tem (padrão: 6)")
async def dado(ctx: commands.Context, lados: int = 6):
    if not 2 <= lados <= 1000:
        await ctx.reply(
            "Escolha um número de lados entre 2 e 1000.",
            ephemeral=True
        )
        return

    resultado = random.randint(1, lados)

    await ctx.reply(f"🎲 Você rolou um d{lados} e tirou **{resultado}**!")


@bot.hybrid_command(
    name="enquete",
    description="Cria uma enquete com até 5 opções"
)
@app_commands.describe(
    pergunta="A pergunta da enquete",
    opcao1="Primeira opção",
    opcao2="Segunda opção",
    opcao3="Terceira opção (opcional)",
    opcao4="Quarta opção (opcional)",
    opcao5="Quinta opção (opcional)"
)
async def enquete(
    ctx: commands.Context,
    pergunta: str,
    opcao1: str,
    opcao2: str,
    opcao3: str | None = None,
    opcao4: str | None = None,
    opcao5: str | None = None
):
    opcoes = [
        opcao for opcao in (opcao1, opcao2, opcao3, opcao4, opcao5)
        if opcao
    ]

    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    embed = discord.Embed(
        title=f"📊 {pergunta}",
        description="\n".join(
            f"{emojis[i]} {texto}" for i, texto in enumerate(opcoes)
        ),
        color=discord.Color.orange()
    )

    embed.set_footer(
        text=f"Enquete criada por {ctx.author.display_name}"
    )

    mensagem = await ctx.send(embed=embed)

    try:
        for i in range(len(opcoes)):
            await mensagem.add_reaction(emojis[i])
    except discord.HTTPException as erro:
        print(f"Não foi possível reagir à enquete: {erro}")


@bot.hybrid_command(
    name="novidades",
    description="Mostra as últimas mudanças do bot"
)
async def novidades(ctx: commands.Context):
    try:
        embed = montar_embed_novidades()
    except OSError:
        await ctx.reply(
            "Não encontrei o arquivo `CHANGELOG.md` no projeto.",
            ephemeral=True
        )
        return

    await ctx.reply(embed=embed)


@bot.hybrid_command(
    name="ajuda",
    description="Lista todos os comandos do bot"
)
async def ajuda(ctx: commands.Context):

    embed = discord.Embed(
        title="📚 Lista de comandos",
        description="Confira os comandos disponíveis do bot!",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="🌐 Comandos (funcionam com / e com ?)",
        value=(
            "`/ajuda` ou `?ajuda` — Mostra esta lista de comandos.\n"
            "`/novidades` ou `?novidades` — Mostra as últimas mudanças.\n"
            "`/ola` ou `?ola` — Envia mensagens de saudação.\n"
            "`/oi_posso_falar` ou `?oi_posso_falar` — Oi, posso falar?\n"
            "`/ping` ou `?ping` — Mostra a latência do bot.\n"
            "`/avatar` ou `?avatar` — Mostra o avatar de um membro.\n"
            "`/dado` ou `?dado` — Rola um dado.\n"
            "`/enquete` ou `?enquete` — Cria uma enquete com até 5 opções.\n"
            "`/organizar_cargos` ou `?organizar_cargos` — "
            "Reorganiza os cargos do servidor (só ADM)."
        ),
        inline=False
    )

    embed.add_field(
        name="🔧 Administração (só cargo ADM)",
        value=(
            "`/lock` — Fecha o canal para os membros.\n"
            "`/unlock` — Abre o canal de novo.\n"
            "`/kick` — Expulsa um membro.\n"
            "`/ban` — Bane um membro.\n"
            "`/unban` — Desbane pelo ID.\n"
            "`/mute` — Deixa um membro sem falar por X minutos.\n"
            "`/unmute` — Devolve a fala do membro.\n"
            "`/clear` — Apaga mensagens do canal (1 a 1000).\n"
            "`/automod add|remover|listar` — Palavras censuradas "
            "(cargos dono, adm e automod não são censurados)."
        ),
        inline=False
    )

    embed.add_field(
        name="⌨️ Somente com prefixo ?",
        value=(
            "`?teste` — Testa se o bot está funcionando.\n"
            "`?enviar_embed` — Envia um embed com uma mensagem sua."
        ),
        inline=False
    )

    embed.add_field(
        name="💡 Dica",
        value=(
            "Nos comandos com `?`, use aspas para textos com espaço:\n"
            "`?enquete \"Qual jogo?\" \"Minecraft\" \"Valorant\"`"
        ),
        inline=False
    )

    embed.set_footer(text=f"Solicitado por {ctx.author.name}")

    await ctx.reply(embed=embed, ephemeral=True)


# ------------------------------------------- organização de cargos

# Ordem desejada dos cargos, de cima para baixo. Cada lista é um grupo e a
# comparação dos nomes é feita sem acento e em minúsculas.
ORDEM_CARGOS = [
    ["dono"],
    ["adm", "admin", "administrador", "staff", "mod", "moderador"],
    ["bobbot", "bob bot"],
    ["membro", "membros"],
    [
        "homem", "homens", "mulher", "mulheres",
        "outro", "outro/prefiro nao falar"
    ],
    ["resenhudo", "tropa da escola"],
    [
        "bots", "loritta", "jockie music", "jockie music (1)",
        "hornbot", "lord", "akinator", "embed generator"
    ],
]


def normalizar_nome(nome: str) -> str:
    """Deixa um texto em minúsculas e sem acento, para comparar nomes."""
    sem_acento = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", nome)
        if not unicodedata.combining(caractere)
    )
    return " ".join(sem_acento.lower().split())


def tem_cargo_adm(membro) -> bool:
    """Diz se o membro tem o cargo ADM (nome comparado sem acento)."""
    return any(
        normalizar_nome(cargo.name) == "adm"
        for cargo in getattr(membro, "roles", ())
    )


def calcular_nova_ordem(cargos, id_cargo_do_bot, limite_bot, limite_autor):
    """Planeja a nova ordem dos cargos, sem tocar no Discord.

    ``cargos`` é a lista de cargos (objeto com id, name, position e managed),
    ordenada do mais alto para o mais baixo, sem o @everyone.
    ``id_cargo_do_bot`` é o cargo mais alto do próprio bot; ``limite_bot`` e
    ``limite_autor`` são as posições dos cargos mais altos do bot e de quem
    usou o comando (None = pode mexer em tudo).

    Devolve (ordem, ignorados): a ordem desejada de cima para baixo e a
    lista de (cargo, motivo) do que ficou de fora.
    """

    def grupo_do(cargo) -> int:
        if cargo.id == id_cargo_do_bot:
            return 2  # o cargo do próprio bot fica em 3º

        nome = normalizar_nome(cargo.name)

        for indice, nomes in enumerate(ORDEM_CARGOS):
            if nome in nomes:
                return indice

        if nome.startswith("outro"):
            return 4  # "Outro/Prefiro não falar" e variações do nome

        return len(ORDEM_CARGOS)  # cargo desconhecido: fica para o final

    def motivo_de_ficar_de_fora(cargo) -> str | None:
        if cargo.managed:
            return "foi criado por uma integração e não pode ser movido"

        if cargo.id == id_cargo_do_bot:
            return "é o cargo mais alto do próprio bot — arraste na mão"

        if limite_bot is not None and cargo.position >= limite_bot:
            return "está acima do cargo mais alto do bot"

        if limite_autor is not None and cargo.position >= limite_autor:
            return "está acima do seu cargo mais alto"

        return None

    desejados = sorted(cargos, key=lambda c: (grupo_do(c), -c.position))

    ordem = []
    ignorados = []

    for cargo in desejados:
        motivo = motivo_de_ficar_de_fora(cargo)

        if motivo:
            ignorados.append((cargo, motivo))
        else:
            ordem.append(cargo)

    return ordem, ignorados


@bot.hybrid_command(
    name="organizar_cargos",
    description="Reorganiza os cargos do servidor na ordem recomendada"
)
async def organizar_cargos(ctx: commands.Context):
    if ctx.guild is None:
        await ctx.reply(
            "Esse comando só funciona dentro de um servidor.",
            ephemeral=True
        )
        return

    guild = ctx.guild
    autor = ctx.author
    eu = guild.me

    if not isinstance(autor, discord.Member) or not tem_cargo_adm(autor):
        await ctx.reply(
            "Só o cargo **ADM** pode usar esse comando.",
            ephemeral=True
        )
        return

    if eu is None or not eu.guild_permissions.manage_roles:
        await ctx.reply(
            "Eu não tenho a permissão **Gerenciar cargos**. "
            "Dê esse cargo ao BobBOT e tente de novo.",
            ephemeral=True
        )
        return

    cargos = sorted(
        (cargo for cargo in guild.roles if cargo != guild.default_role),
        key=lambda cargo: cargo.position,
        reverse=True
    )

    limite_bot = eu.top_role.position if eu.top_role else None
    limite_autor = autor.top_role.position if autor.top_role else None

    if autor.id == guild.owner_id:
        limite_autor = None

    ordem, ignorados = calcular_nova_ordem(
        cargos,
        id_cargo_do_bot=eu.top_role.id if eu.top_role else None,
        limite_bot=limite_bot,
        limite_autor=limite_autor
    )

    if not ordem:
        await ctx.reply(
            "Não movi nada: todos os cargos estão acima do cargo mais "
            "alto do bot ou são de integração. Arraste o cargo **BobBOT** "
            "para perto do topo (abaixo de Dono e ADM) e rode o comando "
            "de novo.",
            ephemeral=True
        )
        return

    try:
        await guild.edit_role_positions(
            positions={
                cargo: indice
                for indice, cargo in enumerate(ordem, start=1)
            },
            reason=f"organizar_cargos usado por {autor}"
        )
    except discord.Forbidden:
        await ctx.reply(
            "O Discord recusou a reorganização. Confira se o cargo do "
            "bot está acima dos cargos que ele precisa mover.",
            ephemeral=True
        )
        return
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao reorganizar os cargos: `{erro.status}`.",
            ephemeral=True
        )
        return

    linhas = "\n".join(
        f"{indice}. {cargo.name}"
        for indice, cargo in enumerate(ordem, start=1)
    )

    embed = discord.Embed(
        title="🗂️ Cargos reorganizados",
        description=f"Ordem nova, de cima para baixo:\n{linhas}"[:4096],
        color=discord.Color.green()
    )

    if ignorados:
        embed.add_field(
            name="⚠️ Ficaram onde estavam",
            value="\n".join(
                f"**{cargo.name}** — {motivo}"
                for cargo, motivo in ignorados
            )[:1024],
            inline=False
        )

    embed.set_footer(text=f"Pedido por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


# -------------------------------------------- administração (só ADM)


async def exigir_adm(ctx: commands.Context) -> bool:
    """Confere servidor e cargo ADM; avisa e devolve False quando não pode."""

    if ctx.guild is None:
        await ctx.reply(
            "Esse comando só funciona dentro de um servidor.",
            ephemeral=True
        )
        return False

    autor = ctx.author

    if not tem_cargo_adm(autor):
        await ctx.reply(
            "Só o cargo **ADM** pode usar esse comando.",
            ephemeral=True
        )
        return False

    return True


def motivo_de_nao_punir(guild, autor, alvo) -> str | None:
    """Diz por que o autor não pode punir esse membro (None = pode)."""

    if alvo.id == autor.id:
        return "você não pode usar isso em si mesmo."

    if alvo.id == getattr(guild, "owner_id", None):
        return "o dono do servidor não pode ser punido."

    if alvo.top_role.position >= autor.top_role.position:
        return "esse membro está no mesmo nível ou acima de você."

    eu = getattr(guild, "me", None)

    if eu is not None and eu.top_role is not None:
        if alvo.top_role.position >= eu.top_role.position:
            return "esse membro está acima do meu cargo."

    return None


@bot.hybrid_command(
    name="lock",
    description="Fecha um canal para os membros falarem (só ADM)"
)
@app_commands.describe(canal="Canal a fechar (padrão: este canal)")
async def lock(
    ctx: commands.Context,
    canal: discord.TextChannel | None = None
):
    if not await exigir_adm(ctx):
        return

    alvo = canal or ctx.channel

    if not isinstance(alvo, discord.TextChannel):
        await ctx.reply(
            "Escolha um canal de texto para fechar.",
            ephemeral=True
        )
        return

    if not alvo.permissions_for(ctx.guild.me).manage_channels:
        await ctx.reply(
            "Eu não tenho a permissão **Gerenciar canais** nesse canal.",
            ephemeral=True
        )
        return

    permissao = alvo.overwrites_for(ctx.guild.default_role)
    permissao.send_messages = False

    try:
        await alvo.set_permissions(
            ctx.guild.default_role,
            overwrite=permissao,
            reason=f"lock por {ctx.author}"
        )
    except discord.Forbidden:
        await ctx.reply(
            "O Discord não me deixou mudar as permissões desse canal.",
            ephemeral=True
        )
        return
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao fechar o canal: `{erro.status}`.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔒 Canal fechado",
        description=(
            f"{alvo.mention} foi trancado. Só quem tem permissão "
            "de administrador consegue falar aqui agora."
        ),
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


@bot.hybrid_command(
    name="unlock",
    description="Abre um canal que estava fechado (só ADM)"
)
@app_commands.describe(canal="Canal a abrir (padrão: este canal)")
async def unlock(
    ctx: commands.Context,
    canal: discord.TextChannel | None = None
):
    if not await exigir_adm(ctx):
        return

    alvo = canal or ctx.channel

    if not isinstance(alvo, discord.TextChannel):
        await ctx.reply(
            "Escolha um canal de texto para abrir.",
            ephemeral=True
        )
        return

    if not alvo.permissions_for(ctx.guild.me).manage_channels:
        await ctx.reply(
            "Eu não tenho a permissão **Gerenciar canais** nesse canal.",
            ephemeral=True
        )
        return

    permissao = alvo.overwrites_for(ctx.guild.default_role)
    permissao.send_messages = None

    try:
        await alvo.set_permissions(
            ctx.guild.default_role,
            overwrite=permissao,
            reason=f"unlock por {ctx.author}"
        )
    except discord.Forbidden:
        await ctx.reply(
            "O Discord não me deixou mudar as permissões desse canal.",
            ephemeral=True
        )
        return
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao abrir o canal: `{erro.status}`.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔓 Canal aberto",
        description=f"{alvo.mention} voltou a aceitar mensagens.",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


@bot.hybrid_command(
    name="ban",
    description="Bane um membro do servidor (só ADM)"
)
@app_commands.describe(
    membro="Quem vai ser banido",
    motivo="Motivo do banimento"
)
async def ban(
    ctx: commands.Context,
    membro: discord.Member,
    *,
    motivo: str = "sem motivo informado"
):
    if not await exigir_adm(ctx):
        return

    problema = motivo_de_nao_punir(ctx.guild, ctx.author, membro)

    if problema:
        await ctx.reply(f"Não posso banir: {problema}", ephemeral=True)
        return

    try:
        await membro.ban(reason=f"{motivo} (por {ctx.author})")
    except discord.Forbidden:
        await ctx.reply(
            "O Discord não me deixou banir esse membro. Confira se eu "
            "tenho **Banir membros** e se meu cargo está acima do dele.",
            ephemeral=True
        )
        return
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao banir: `{erro.status}`.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔨 Membro banido",
        description=f"**{membro}** foi banido do servidor.\n**Motivo:** {motivo}",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


@bot.hybrid_command(
    name="unban",
    description="Desbane um usuário pelo ID (só ADM)"
)
@app_commands.describe(
    id_usuario="ID do usuário banido (clique com o botão direito → Copiar ID)",
    motivo="Motivo do desbanimento"
)
async def unban(
    ctx: commands.Context,
    id_usuario: str,
    *,
    motivo: str = "sem motivo informado"
):
    if not await exigir_adm(ctx):
        return

    try:
        identificador = int(id_usuario.strip())
    except ValueError:
        await ctx.reply(
            "Me passe o **ID** numérico do usuário banido.",
            ephemeral=True
        )
        return

    try:
        entrada = await ctx.guild.fetch_ban(discord.Object(id=identificador))
    except discord.NotFound:
        await ctx.reply(
            "Esse usuário não está banido neste servidor.",
            ephemeral=True
        )
        return
    except discord.Forbidden:
        await ctx.reply(
            "Eu preciso da permissão **Banir membros** para ver a lista "
            "de banidos.",
            ephemeral=True
        )
        return
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao consultar os banidos: `{erro.status}`.",
            ephemeral=True
        )
        return

    try:
        await ctx.guild.unban(
            entrada.user,
            reason=f"{motivo} (por {ctx.author})"
        )
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao desbanir: `{erro.status}`.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔓 Membro desbanido",
        description=(
            f"**{entrada.user}** pode voltar ao servidor.\n"
            f"**Motivo:** {motivo}"
        ),
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


@bot.hybrid_command(
    name="kick",
    description="Expulsa um membro do servidor (só ADM)"
)
@app_commands.describe(
    membro="Quem vai ser expulso",
    motivo="Motivo da expulsão"
)
async def kick(
    ctx: commands.Context,
    membro: discord.Member,
    *,
    motivo: str = "sem motivo informado"
):
    if not await exigir_adm(ctx):
        return

    problema = motivo_de_nao_punir(ctx.guild, ctx.author, membro)

    if problema:
        await ctx.reply(f"Não posso expulsar: {problema}", ephemeral=True)
        return

    try:
        await membro.kick(reason=f"{motivo} (por {ctx.author})")
    except discord.Forbidden:
        await ctx.reply(
            "O Discord não me deixou expulsar esse membro. Confira se eu "
            "tenho **Expulsar membros** e se meu cargo está acima do dele.",
            ephemeral=True
        )
        return
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao expulsar: `{erro.status}`.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="👊 Membro expulso",
        description=f"**{membro}** saiu do servidor.\n**Motivo:** {motivo}",
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


@bot.hybrid_command(
    name="mute",
    description="Silencia um membro por um tempo (só ADM)"
)
@app_commands.describe(
    membro="Quem vai ficar sem falar",
    minutos="Quanto tempo em minutos (padrão 10, máximo 40320)",
    motivo="Motivo do silenciamento"
)
async def mute(
    ctx: commands.Context,
    membro: discord.Member,
    minutos: int = 10,
    *,
    motivo: str = "sem motivo informado"
):
    if not await exigir_adm(ctx):
        return

    problema = motivo_de_nao_punir(ctx.guild, ctx.author, membro)

    if problema:
        await ctx.reply(f"Não posso silenciar: {problema}", ephemeral=True)
        return

    minutos = max(1, min(minutos, 40320))

    try:
        await membro.timeout(
            timedelta(minutes=minutos),
            reason=f"{motivo} (por {ctx.author})"
        )
    except discord.Forbidden:
        await ctx.reply(
            "O Discord não me deixou silenciar esse membro. Confira se eu "
            "tenho **Moderar membros** e se meu cargo está acima do dele.",
            ephemeral=True
        )
        return
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao silenciar: `{erro.status}`.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🤐 Membro silenciado",
        description=(
            f"**{membro}** fica {minutos} minuto(s) sem falar "
            "e sem entrar em canais de voz.\n"
            f"**Motivo:** {motivo}"
        ),
        color=discord.Color.orange()
    )
    embed.set_footer(text=f"Por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


@bot.hybrid_command(
    name="unmute",
    description="Devolve a fala de um membro silenciado (só ADM)"
)
@app_commands.describe(membro="Quem vai poder falar de novo")
async def unmute(ctx: commands.Context, membro: discord.Member):
    if not await exigir_adm(ctx):
        return

    try:
        await membro.timeout(None, reason=f"unmute por {ctx.author}")
    except discord.Forbidden:
        await ctx.reply(
            "O Discord não me deixou tirar o silêncio. Confira se meu "
            "cargo está acima do dele.",
            ephemeral=True
        )
        return
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao tirar o silêncio: `{erro.status}`.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔊 Silêncio removido",
        description=f"**{membro}** pode falar de novo.",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


# ------------------------------------------- dar e tirar cargos (dono/ADM)


async def exigir_dono_ou_adm(ctx: commands.Context) -> bool:
    """Confere servidor e quem pode dar ou tirar cargos: dono ou ADM."""

    if ctx.guild is None:
        await ctx.reply(
            "Esse comando só funciona dentro de um servidor.",
            ephemeral=True
        )
        return False

    autor = ctx.author

    if autor.id == ctx.guild.owner_id or tem_cargo_adm(autor):
        return True

    await ctx.reply(
        "Só o **dono** do servidor ou o cargo **ADM** pode usar esse comando.",
        ephemeral=True
    )
    return False


async def cargo_liberado(ctx: commands.Context, cargo: discord.Role) -> bool:
    """Confere se o bot e quem usou o comando podem mexer nesse cargo."""

    guild = ctx.guild
    eu = guild.me

    if cargo.is_default():
        await ctx.reply(
            "O cargo **@everyone** não pode ser dado nem tirado.",
            ephemeral=True
        )
        return False

    if cargo.managed:
        await ctx.reply(
            f"O cargo **{cargo.name}** vem de uma integração (bot ou boost) "
            "e não pode ser mexido.",
            ephemeral=True
        )
        return False

    if eu is None or not eu.guild_permissions.manage_roles:
        await ctx.reply(
            "Eu não tenho a permissão **Gerenciar cargos**. "
            "Dê esse cargo ao BobBOT e tente de novo.",
            ephemeral=True
        )
        return False

    if eu.top_role is not None and cargo.position >= eu.top_role.position:
        await ctx.reply(
            f"O cargo **{cargo.name}** está no nível do meu cargo ou acima. "
            "Suba o cargo do BobBOT na hierarquia antes de usar isso.",
            ephemeral=True
        )
        return False

    autor = ctx.author

    if (
        autor.id != guild.owner_id
        and autor.top_role is not None
        and cargo.position >= autor.top_role.position
    ):
        await ctx.reply(
            f"Você não pode mexer no cargo **{cargo.name}**: ele está no "
            "nível do seu cargo ou acima. Esse papel é do dono do servidor.",
            ephemeral=True
        )
        return False

    return True


@bot.hybrid_group(
    name="role",
    description="Dá ou tira um cargo de um membro (dono e ADM)",
    invoke_without_command=True
)
async def role(ctx: commands.Context):
    await ctx.reply(
        "Use `?role add @membro @cargo` para dar um cargo e "
        "`?role remove @membro @cargo` para tirar.\n"
        "Exemplo: `?role add @fulano homem` — nome de cargo com espaço "
        "precisa de aspas: `?role add @fulano \"Outro/Prefiro não falar\"`.",
        ephemeral=True
    )


@role.command(name="add", description="Dá um cargo para um membro")
@app_commands.describe(
    membro="Quem vai receber o cargo",
    cargo="Cargo que será dado"
)
async def role_add(
    ctx: commands.Context,
    membro: discord.Member,
    *,
    cargo: discord.Role
):
    if not await exigir_dono_ou_adm(ctx):
        return

    if not await cargo_liberado(ctx, cargo):
        return

    if cargo in membro.roles:
        await ctx.reply(
            f"**{membro}** já tem o cargo **{cargo.name}**.",
            ephemeral=True
        )
        return

    try:
        await membro.add_roles(
            cargo,
            reason=f"role add por {ctx.author}"
        )
    except discord.Forbidden:
        await ctx.reply(
            "O Discord não me deixou dar esse cargo. Confira se eu tenho "
            "**Gerenciar cargos** e se meu cargo está acima dele.",
            ephemeral=True
        )
        return
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao dar o cargo: `{erro.status}`.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🎖️ Cargo adicionado",
        description=f"**{membro}** agora tem o cargo **{cargo.name}**.",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


@role.command(name="remove", description="Tira um cargo de um membro")
@app_commands.describe(
    membro="De quem o cargo será tirado",
    cargo="Cargo que será removido"
)
async def role_remove(
    ctx: commands.Context,
    membro: discord.Member,
    *,
    cargo: discord.Role
):
    if not await exigir_dono_ou_adm(ctx):
        return

    if not await cargo_liberado(ctx, cargo):
        return

    if cargo not in membro.roles:
        await ctx.reply(
            f"**{membro}** não tem o cargo **{cargo.name}**.",
            ephemeral=True
        )
        return

    try:
        await membro.remove_roles(
            cargo,
            reason=f"role remove por {ctx.author}"
        )
    except discord.Forbidden:
        await ctx.reply(
            "O Discord não me deixou tirar esse cargo. Confira se eu tenho "
            "**Gerenciar cargos** e se meu cargo está acima dele.",
            ephemeral=True
        )
        return
    except discord.HTTPException as erro:
        await ctx.reply(
            f"Deu erro ao tirar o cargo: `{erro.status}`.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🔻 Cargo removido",
        description=f"**{membro}** não tem mais o cargo **{cargo.name}**.",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


# --------------------------------------------------------------- clear

LIMPAR_MAXIMO = 1000
LIMPAR_SEGUNDOS_AVISO = 10


def tem_autorizacao_de_limpeza(membro) -> bool:
    """Diz se o membro pode limpar mensagens: dono, admin ou cargo ADM."""

    if membro is None:
        return False

    guild = getattr(membro, "guild", None)

    if guild is not None and membro.id == getattr(guild, "owner_id", None):
        return True

    if getattr(membro.guild_permissions, "administrator", False):
        return True

    return tem_cargo_adm(membro)


async def pode_limpar(ctx: commands.Context) -> bool:
    """Valida quem pediu a limpeza, incluindo o dono do próprio bot."""

    if await bot.is_owner(ctx.author):
        return True

    return tem_autorizacao_de_limpeza(ctx.author)


async def responder_rapido(ctx: commands.Context, texto: str) -> None:
    """Responde sem poluir o chat: efêmero no slash, apagado sozinho no ?."""

    try:
        if ctx.interaction is not None:
            await ctx.reply(texto, ephemeral=True)
        else:
            await ctx.reply(texto, delete_after=LIMPAR_SEGUNDOS_AVISO)
    except discord.HTTPException as erro:
        print(f"Não foi possível responder ao clear: {erro}")


@bot.hybrid_command(
    name="clear",
    description="Apaga mensagens do canal (só administração)"
)
@app_commands.describe(
    quantidade=f"Quantas mensagens apagar (1 a {LIMPAR_MAXIMO})"
)
@app_commands.default_permissions(manage_messages=True)
async def clear(ctx: commands.Context, quantidade: int):
    if ctx.guild is None:
        await responder_rapido(
            ctx,
            "Esse comando só funciona dentro de um servidor."
        )
        return

    if not await pode_limpar(ctx):
        await responder_rapido(
            ctx,
            "❌ Você não tem permissão para utilizar este comando."
        )
        return

    if quantidade <= 0:
        await responder_rapido(
            ctx,
            "Escolha uma quantidade maior que zero. Exemplo: `/clear 10`."
        )
        return

    if quantidade > LIMPAR_MAXIMO:
        await responder_rapido(
            ctx,
            f"O máximo que apago de uma vez é **{LIMPAR_MAXIMO}** "
            "mensagens. Tente um número menor."
        )
        return

    canal = ctx.channel

    if not isinstance(canal, (discord.TextChannel, discord.Thread)):
        await responder_rapido(
            ctx,
            "Não consigo limpar mensagens neste tipo de canal."
        )
        return

    permissoes = canal.permissions_for(ctx.guild.me)

    if not permissoes.manage_messages:
        await responder_rapido(
            ctx,
            "Eu preciso da permissão **Gerenciar mensagens** neste canal."
        )
        return

    if not permissoes.read_message_history:
        await responder_rapido(
            ctx,
            "Eu preciso da permissão **Ver histórico de mensagens** "
            "neste canal."
        )
        return

    try:
        apagadas = len(await canal.purge(
            limit=quantidade,
            bulk=True,
            reason=f"clear por {ctx.author}"
        ))
    except discord.Forbidden:
        await responder_rapido(
            ctx,
            "O Discord não me deixou apagar as mensagens. Confira minhas "
            "permissões e se meu cargo está acima das que vou apagar."
        )
        return
    except discord.HTTPException as erro:
        await responder_rapido(
            ctx,
            f"Deu erro ao apagar as mensagens (`{erro.status}`). "
            "Tente de novo em alguns segundos."
        )
        return

    if apagadas == 0:
        await responder_rapido(
            ctx,
            "Não encontrei mensagens para apagar neste canal."
        )
        return

    await responder_rapido(
        ctx,
        f"🧹 Foram apagadas {apagadas} mensagem(ns) com sucesso!"
    )


# ------------------------------------------------------------- automod

_palavras_automod: list[str] = []

# Cargos que o automod nunca apaga: os IDs estão no .env (AUTOMOD_ISENTOS)
# e os nomes abaixo valem mesmo sem o .env configurado.
CARGOS_ISENTOS_NOME = ("dono", "adm")


def ler_cargos_isentos() -> set[int]:
    """Lê do .env os IDs de cargos isentos da censura (AUTOMOD_ISENTOS)."""

    bruto = os.getenv("AUTOMOD_ISENTOS", "")
    return {
        int(pedaco)
        for pedaco in re.split(r"[^\d]+", bruto)
        if pedaco.isdigit()
    }


_cargos_isentos = ler_cargos_isentos()


def tem_cargo_isento(membro) -> bool:
    """Diz se o membro está fora da censura (cargo dono/adm)."""

    cargos = list(getattr(membro, "roles", ()))

    if any(cargo.id in _cargos_isentos for cargo in cargos):
        return True

    return any(
        normalizar_nome(cargo.name) in CARGOS_ISENTOS_NOME
        for cargo in cargos
    )


def carregar_palavras_automod() -> list[str]:
    """Lê do disco as palavras censuradas pelo automod."""

    try:
        dados = json.loads(CAMINHO_AUTOMOD.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []

    if isinstance(dados, dict):
        palavras = dados.get("palavras", [])
    elif isinstance(dados, list):
        palavras = dados
    else:
        return []

    return [str(palavra).strip() for palavra in palavras if str(palavra).strip()]


def salvar_palavras_automod(palavras) -> None:
    """Grava a lista de palavras censuradas no disco."""

    CAMINHO_AUTOMOD.parent.mkdir(parents=True, exist_ok=True)

    lista = sorted(
        {palavra.strip() for palavra in palavras if palavra.strip()},
        key=normalizar_nome
    )

    CAMINHO_AUTOMOD.write_text(
        json.dumps({"palavras": lista}, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def texto_tem_palavra_bloqueada(texto: str, palavras) -> str | None:
    """Devolve a palavra bloqueada encontrada no texto (ou None).

    Compara sem acento, em minúsculas e por palavra inteira, então "cu"
    não é encontrado dentro de "curioso".
    """

    if not texto:
        return None

    normalizado = normalizar_nome(texto)

    for palavra in palavras:
        chave = normalizar_nome(palavra)

        if not chave:
            continue

        padrao = rf"(?<!\w){re.escape(chave)}(?:s|es)?(?!\w)"

        if re.search(padrao, normalizado):
            return palavra

    return None


def tem_cargo_automod(membro) -> bool:
    """Diz se o membro tem o cargo que passa por fora da censura."""

    return any(
        normalizar_nome(cargo.name) == CARGO_AUTOMOD
        for cargo in getattr(membro, "roles", ())
    )


async def aplicar_automod(mensagem: discord.Message) -> bool:
    """Apaga a mensagem com palavra bloqueada e avisa o autor.

    Devolve True quando a mensagem foi barrada (e não deve virar comando).
    """

    autor = mensagem.author

    if autor.bot or mensagem.guild is None or not mensagem.content:
        return False

    if not _palavras_automod:
        return False

    if tem_cargo_automod(autor):
        return False

    if tem_cargo_isento(autor):
        return False

    if texto_tem_palavra_bloqueada(mensagem.content, _palavras_automod) is None:
        return False

    try:
        await mensagem.delete()
    except discord.HTTPException as erro:
        print(f"Não consegui apagar a mensagem do automod: {erro}")

    try:
        await mensagem.channel.send(
            MENSAGEM_AUTOMOD.format(mencao=autor.mention)
        )
    except discord.HTTPException as erro:
        print(f"Não consegui avisar o automod: {erro}")

    return True


@bot.event
async def on_message(mensagem: discord.Message):
    barrada = await aplicar_automod(mensagem)

    if not barrada:
        await bot.process_commands(mensagem)


@bot.hybrid_group(
    name="automod",
    description="Palavras censuradas pelo automod (só ADM)",
    invoke_without_command=True
)
async def automod(ctx: commands.Context):
    await listar_palavras_automod(ctx)


async def listar_palavras_automod(ctx: commands.Context) -> None:
    if not await exigir_adm(ctx):
        return

    if not _palavras_automod:
        await ctx.reply(
            "Nenhuma palavra bloqueada ainda. Use `/automod add <palavra>`.",
            ephemeral=True
        )
        return

    lista = "\n".join(f"• `{palavra}`" for palavra in _palavras_automod)

    embed = discord.Embed(
        title="🛡️ Palavras bloqueadas",
        description=lista[:4096],
        color=discord.Color.blurple()
    )
    embed.set_footer(
        text="Cargos dono, adm e automod não são censurados"
    )

    await ctx.reply(embed=embed, ephemeral=True)


@automod.command(name="add", description="Bloqueia uma palavra nova")
@app_commands.describe(palavra="Palavra ou frase que será censurada")
async def automod_add(ctx: commands.Context, *, palavra: str):
    if not await exigir_adm(ctx):
        return

    palavra = palavra.strip()

    if not palavra:
        await ctx.reply(
            "Me diga a palavra que quer bloquear.",
            ephemeral=True
        )
        return

    if re.search(r"<@&\d+>", palavra):
        await ctx.reply(
            "Isso é um **cargo**, não uma palavra — cargo não entra na "
            "censura. Escreva só o texto que quer bloquear.",
            ephemeral=True
        )
        return

    chave = normalizar_nome(palavra)

    for existente in _palavras_automod:
        if normalizar_nome(existente) == chave:
            await ctx.reply(
                f"`{existente}` já está na lista.",
                ephemeral=True
            )
            return

    _palavras_automod.append(palavra)
    salvar_palavras_automod(_palavras_automod)

    embed = discord.Embed(
        title="🛡️ Palavra bloqueada",
        description=f"`{palavra}` agora é censurada no servidor.",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Por {ctx.author.display_name}")

    await ctx.reply(embed=embed)


@automod.command(name="remover", description="Tira uma palavra da lista")
@app_commands.describe(palavra="Palavra que vai sair da censura")
async def automod_remover(ctx: commands.Context, *, palavra: str):
    if not await exigir_adm(ctx):
        return

    chave = normalizar_nome(palavra)

    for existente in list(_palavras_automod):
        if normalizar_nome(existente) == chave:
            _palavras_automod.remove(existente)
            salvar_palavras_automod(_palavras_automod)

            embed = discord.Embed(
                title="🛡️ Palavra liberada",
                description=f"`{existente}` não é mais censurada.",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Por {ctx.author.display_name}")

            await ctx.reply(embed=embed)
            return

    await ctx.reply(
        f"`{palavra}` não está na lista. Use `/automod` para ver todas.",
        ephemeral=True
    )


@automod.command(name="listar", description="Mostra as palavras bloqueadas")
async def automod_listar(ctx: commands.Context):
    await listar_palavras_automod(ctx)


# ------------------------------------------------ tratamento de erros


@bot.event
async def on_command_error(
    ctx: commands.Context,
    erro: commands.CommandError
):
    if isinstance(erro, commands.CommandNotFound):
        return

    if isinstance(erro, commands.MissingRequiredArgument):
        if ctx.command is clear:
            await ctx.reply(
                "Me diga quantas mensagens apagar. Exemplo: `?clear 10`.",
                delete_after=LIMPAR_SEGUNDOS_AVISO
            )
            return

        await ctx.reply(
            f"Faltou o argumento `{erro.param.name}` nesse comando."
        )
        return

    if isinstance(erro, commands.BadArgument):
        if ctx.command is clear:
            await ctx.reply(
                "A quantidade precisa ser um número inteiro. "
                "Exemplo: `?clear 10`.",
                delete_after=LIMPAR_SEGUNDOS_AVISO
            )
            return

        await ctx.reply(
            "Valor inválido para esse comando. "
            "Confira os parâmetros e tente de novo."
        )
        return

    # Em comando híbrido, a falha de conversão do slash chega embrulhada em
    # HybridCommandError; o motivo de verdade está em `.original`. Sem isso o
    # usuário só via "Deu erro" sem saber o que ele digitou errado.
    original = getattr(erro, "original", None)

    if isinstance(original, app_commands.TransformerError):
        valor = str(original.value).strip().replace("`", "'")[:60]

        if original.type == discord.AppCommandOptionType.user:
            await ctx.reply(
                f"Não consegui identificar o membro `{valor}`. Use a menção "
                "**@** ou escolha a pessoa na lista do Discord."
            )
        elif original.type == discord.AppCommandOptionType.role:
            await ctx.reply(
                f"Não consegui identificar o cargo `{valor}`. Use a menção "
                "do cargo ou escolha na lista do Discord."
            )
        else:
            await ctx.reply(
                f"Não consegui entender o valor `{valor}` que você enviou."
            )
        return

    print(f"Erro no comando {ctx.command}: {erro!r}")
    await ctx.reply(
        "Deu erro ao executar esse comando. Tente de novo mais tarde."
    )


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction,
    erro: discord.app_commands.AppCommandError
):
    print(f"Erro no comando {interaction.command}: {erro!r}")

    mensagem = "Deu erro ao executar esse comando. Tente de novo mais tarde."

    if interaction.response.is_done():
        await interaction.followup.send(mensagem, ephemeral=True)
    else:
        await interaction.response.send_message(mensagem, ephemeral=True)


# ------------------------------------------------------------- inicialização

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit(
            "Token não configurado.\n"
            "Crie um arquivo .env nesta pasta com a linha:\n"
            "DISCORD_TOKEN=seu_token_aqui"
        )

    bot.run(TOKEN)
