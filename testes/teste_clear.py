"""Testa o comando clear sem conectar ao Discord."""

import asyncio
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import discord  # noqa: E402
from discord.ext import commands  # noqa: E402

import main  # noqa: E402


# ---------------------------------------------------------------- objetos falsos


class PermissoesMembroFalso:
    def __init__(self, administrator=False):
        self.administrator = administrator


class MembroFalso:
    def __init__(self, nome, cargos=(), id=1, guild=None, admin=False):
        self.name = nome
        self.id = id
        self.guild = guild
        self.roles = [
            type("Cargo", (), {"name": nome_cargo, "position": posicao})()
            for nome_cargo, posicao in cargos
        ]
        self.guild_permissions = PermissoesMembroFalso(admin)


class GuildFalsa:
    def __init__(self, dono_id=None, eu=None):
        self.owner_id = dono_id
        self.me = eu


class PermissoesCanalFalso:
    def __init__(self, gerenciar=True, historico=True):
        self.manage_messages = gerenciar
        self.read_message_history = historico


class CanalTextoFalso(discord.TextChannel):
    """Canal de texto de mentira: não chama a API do Discord."""

    def __init__(self, apagadas=5, erro=None, gerenciar=True, historico=True):
        self.apagadas = apagadas
        self.erro = erro
        self.permissoes = PermissoesCanalFalso(gerenciar, historico)
        self.chamadas = []

    def permissions_for(self, membro):
        return self.permissoes

    async def purge(self, **kwargs):
        self.chamadas.append(kwargs)

        if self.erro is not None:
            raise self.erro

        return [object() for _ in range(self.apagadas)]


class ContextoFalso:
    def __init__(self, autor, guild=None, canal=None, interaction=None):
        self.author = autor
        self.guild = guild if guild is not None else GuildFalsa()
        self.channel = canal if canal is not None else CanalTextoFalso()
        self.interaction = interaction
        self.respostas = []
        self.opcoes = []

    async def reply(self, texto=None, **kwargs):
        self.respostas.append(texto)
        self.opcoes.append(kwargs)


def montar(dono_id=99, admin=False, cargos=(), canal=None):
    guild = GuildFalsa(dono_id=dono_id, eu=MembroFalso("bob", guild=None))
    autor = MembroFalso("quem pediu", cargos, guild=guild, admin=admin)
    return ContextoFalso(autor, guild=guild, canal=canal)


def rodar(ctx, quantidade):
    asyncio.run(main.clear.callback(ctx, quantidade))


# ------------------------------------------------------------------- testes


def testar_autorizacao() -> None:
    guild = GuildFalsa(dono_id=99, eu=MembroFalso("bob"))

    dono = MembroFalso("dono", id=99, guild=guild)
    assert main.tem_autorizacao_de_limpeza(dono)

    administrador = MembroFalso("adm do discord", guild=guild, admin=True)
    assert main.tem_autorizacao_de_limpeza(administrador)

    cargo_adm = MembroFalso("adm", [("ADM", 5)], guild=guild)
    assert main.tem_autorizacao_de_limpeza(cargo_adm)

    comum = MembroFalso("membro", [("Membro", 1)], guild=guild)
    assert not main.tem_autorizacao_de_limpeza(comum)
    assert not main.tem_autorizacao_de_limpeza(None)

    ctx = ContextoFalso(comum, guild=guild, canal=CanalTextoFalso())
    assert asyncio.run(main.pode_limpar(ctx)) is False

    ctx_do_dono_do_bot = ContextoFalso(
        MembroFalso("dono do bot", id=main.bot.owner_id, guild=guild),
        guild=guild,
        canal=CanalTextoFalso()
    )
    assert asyncio.run(main.pode_limpar(ctx_do_dono_do_bot)) is True

    print("ok - dono, administrador, cargo ADM e dono do bot são aceitos")


def testar_sem_permissao() -> None:
    ctx = montar(cargos=[("Membro", 1)])
    rodar(ctx, 10)

    assert "não tem permissão" in ctx.respostas[0], ctx.respostas
    assert not ctx.channel.chamadas

    print("ok - membro comum é barrado antes de apagar qualquer coisa")


def testar_quantidade_invalida() -> None:
    for quantidade in (0, -5):
        ctx = montar(admin=True)
        rodar(ctx, quantidade)

        assert "maior que zero" in ctx.respostas[0], ctx.respostas
        assert not ctx.channel.chamadas

    ctx = montar(admin=True)
    rodar(ctx, main.LIMPAR_MAXIMO + 1)

    assert "máximo" in ctx.respostas[0], ctx.respostas
    assert not ctx.channel.chamadas

    print("ok - zero, negativo e acima do máximo são recusados")


def testar_permissoes_do_bot() -> None:
    ctx = montar(admin=True, canal=CanalTextoFalso(gerenciar=False))
    rodar(ctx, 10)

    assert "Gerenciar mensagens" in ctx.respostas[0], ctx.respostas
    assert not ctx.channel.chamadas

    ctx = montar(admin=True, canal=CanalTextoFalso(historico=False))
    rodar(ctx, 10)

    assert "histórico" in ctx.respostas[0], ctx.respostas
    assert not ctx.channel.chamadas

    print("ok - confere as permissões do bot antes de tentar apagar")


def testar_canal_incompativel() -> None:
    ctx = montar(admin=True)
    ctx.channel = object()
    rodar(ctx, 10)

    assert "tipo de canal" in ctx.respostas[0], ctx.respostas

    print("ok - canal incompatível recebe aviso claro")


def testar_sucesso() -> None:
    ctx = montar(admin=True, canal=CanalTextoFalso(apagadas=7))
    rodar(ctx, 50)

    assert ctx.channel.chamadas == [{
        "limit": 50,
        "bulk": True,
        "reason": f"clear por {ctx.author}"
    }], ctx.channel.chamadas
    assert "Foram apagadas 7" in ctx.respostas[0], ctx.respostas
    assert "delete_after" in ctx.opcoes[0], ctx.opcoes

    print("ok - apaga no lote certo e informa o total real")

    ctx_slash = montar(
        admin=True,
        canal=CanalTextoFalso(apagadas=3)
    )
    ctx_slash.interaction = object()
    rodar(ctx_slash, 3)

    assert ctx_slash.opcoes[0] == {"ephemeral": True}, ctx_slash.opcoes
    assert "Foram apagadas 3" in ctx_slash.respostas[0]

    print("ok - no slash a resposta é efêmera")


def testar_falhas() -> None:
    ctx = montar(admin=True, canal=CanalTextoFalso(apagadas=0))
    rodar(ctx, 10)

    assert "Não encontrei mensagens" in ctx.respostas[0], ctx.respostas

    ctx = montar(
        admin=True,
        canal=CanalTextoFalso(erro=discord.Forbidden.__new__(discord.Forbidden))
    )
    rodar(ctx, 10)

    assert "não me deixou apagar" in ctx.respostas[0], ctx.respostas

    class ErroHTTPFalso(discord.HTTPException):
        def __init__(self):
            self.status = 500

    ctx = montar(admin=True, canal=CanalTextoFalso(erro=ErroHTTPFalso()))
    rodar(ctx, 10)

    assert "500" in ctx.respostas[0], ctx.respostas

    print("ok - sem mensagens, sem permissão e erro da API têm avisos próprios")


def testar_erros_de_prefixo() -> None:
    ctx = montar(admin=True)
    ctx.command = main.clear
    parametro = type(
        "Parametro",
        (),
        {"name": "quantidade", "displayed_name": "quantidade"}
    )()
    asyncio.run(main.on_command_error(
        ctx, commands.MissingRequiredArgument(parametro)
    ))

    assert "quantas mensagens" in ctx.respostas[0], ctx.respostas

    ctx = montar(admin=True)
    ctx.command = main.clear
    asyncio.run(main.on_command_error(ctx, commands.BadArgument("abc")))

    assert "número inteiro" in ctx.respostas[0], ctx.respostas

    print("ok - ?clear sem número ou com texto recebe uma dica amigável")


def main_teste() -> None:
    main.bot.owner_id = 424242

    testar_autorizacao()
    testar_sem_permissao()
    testar_quantidade_invalida()
    testar_permissoes_do_bot()
    testar_canal_incompativel()
    testar_sucesso()
    testar_falhas()
    testar_erros_de_prefixo()

    print("\nTodos os testes do clear passaram!")


if __name__ == "__main__":
    main_teste()
