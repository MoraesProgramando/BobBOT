"""Testa os comandos de administração e o automod sem conectar ao Discord."""

import asyncio
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import main  # noqa: E402


# ---------------------------------------------------------------- objetos falsos


class CargoFalso:
    def __init__(self, nome, posicao):
        self.name = nome
        self.position = posicao


class MembroFalso:
    def __init__(self, nome, cargos=(), posicao=0, bot=False, id=1):
        self.name = nome
        self.id = id
        self.bot = bot
        self.roles = [
            CargoFalso(nome_cargo, posicao_cargo)
            for nome_cargo, posicao_cargo in cargos
        ]
        self.top_role = CargoFalso("topo", posicao)
        self.mention = f"@{nome}"


class CanalFalso:
    def __init__(self):
        self.enviados = []

    async def send(self, texto):
        self.enviados.append(texto)


class MensagemFalsa:
    def __init__(self, autor, conteudo, guild=None):
        self.author = autor
        self.content = conteudo
        self.guild = guild if guild is not None else object()
        self.channel = CanalFalso()
        self.apagada = False

    async def delete(self):
        self.apagada = True


class GuildFalsa:
    def __init__(self, dono_id=None, eu=None):
        self.owner_id = dono_id
        self.me = eu


class ContextoFalso:
    def __init__(self, autor, guild=None):
        self.author = autor
        self.guild = guild if guild is not None else GuildFalsa()
        self.respostas = []

    async def reply(self, texto=None, **kwargs):
        self.respostas.append(texto)


# ---------------------------------------------------------------- automod


def testar_palavras_bloqueadas() -> None:
    palavras = ["idiota", "cu", "Merda"]

    assert main.texto_tem_palavra_bloqueada("seu IDIOTA", palavras) == "idiota"
    assert main.texto_tem_palavra_bloqueada("que idiotas", palavras) == "idiota"
    assert main.texto_tem_palavra_bloqueada("merda!", palavras) == "Merda"
    assert main.texto_tem_palavra_bloqueada("curioso demais", palavras) is None
    assert main.texto_tem_palavra_bloqueada("tudo certo aqui", palavras) is None
    assert main.texto_tem_palavra_bloqueada("", palavras) is None

    print("ok - censura acha a palavra, ignora acento/caixa e não pega pedaço")


def testar_isencao_automod() -> None:
    assert main.tem_cargo_automod(MembroFalso("a", [("Automod", 1)]))
    assert main.tem_cargo_automod(MembroFalso("a", [("AUTOMOD", 1)]))
    assert not main.tem_cargo_automod(MembroFalso("a", [("ADM", 5)]))
    assert not main.tem_cargo_automod(MembroFalso("a"))

    print("ok - só o cargo automod fica de fora da censura")


def testar_arquivo_automod(pasta: Path) -> None:
    main.CAMINHO_AUTOMOD = pasta / "logs" / "automod.json"

    main.salvar_palavras_automod(["Merda", "idiota", " idiota ", ""])
    lidas = main.carregar_palavras_automod()

    assert lidas == ["idiota", "Merda"], lidas
    assert main.carregar_palavras_automod() == lidas

    print("ok - lista de palavras sai e volta do disco sem repetir")


def testar_aplicar_automod() -> None:
    main._palavras_automod[:] = ["idiota"]

    bot_mensagem = MensagemFalsa(MembroFalso("bot", bot=True), "idiota")
    assert not asyncio.run(main.aplicar_automod(bot_mensagem))
    assert not bot_mensagem.apagada

    isento = MensagemFalsa(
        MembroFalso("adm", [("automod", 3)]),
        "idiota"
    )
    assert not asyncio.run(main.aplicar_automod(isento))
    assert not isento.apagada

    limpa = MensagemFalsa(MembroFalso("membro"), "bom dia a todos")
    assert not asyncio.run(main.aplicar_automod(limpa))
    assert not limpa.apagada

    barrada = MensagemFalsa(MembroFalso("membro"), "seu idiota")
    assert asyncio.run(main.aplicar_automod(barrada))
    assert barrada.apagada
    assert barrada.channel.enviados == [
        "Ei! @membro você não pode falar isto!"
    ], barrada.channel.enviados

    print("ok - apaga a mensagem, avisa e respeita bots e o cargo automod")

    main._palavras_automod[:] = []


# ---------------------------------------------------------------- punições


def testar_motivo_de_nao_punir() -> None:
    guild = GuildFalsa(dono_id=99, eu=MembroFalso("bot", posicao=50))
    autor = MembroFalso("adm", [("ADM", 40)], posicao=40)

    assert "si mesmo" in main.motivo_de_nao_punir(guild, autor, autor)

    dono = MembroFalso("dono", posicao=100, id=99)
    assert "dono" in main.motivo_de_nao_punir(guild, autor, dono)

    igual = MembroFalso("outro adm", posicao=40, id=7)
    assert "mesmo nível" in main.motivo_de_nao_punir(guild, autor, igual)

    guild_baixa = GuildFalsa(dono_id=99, eu=MembroFalso("bot", posicao=30))
    acima_do_bot = MembroFalso("cargo alto", posicao=35, id=8)
    assert "acima do meu cargo" in main.motivo_de_nao_punir(
        guild_baixa, autor, acima_do_bot
    )

    comum = MembroFalso("membro", posicao=5, id=9)
    assert main.motivo_de_nao_punir(guild, autor, comum) is None

    print("ok - hierarquia barra dono, empate e cargos acima do bot")


def testar_exigir_adm() -> None:
    guild = GuildFalsa()

    sem_adm = ContextoFalso(MembroFalso("membro", [("Membro", 1)]), guild)
    assert asyncio.run(main.exigir_adm(sem_adm)) is False
    assert "ADM" in sem_adm.respostas[0]

    com_adm = ContextoFalso(MembroFalso("adm", [("ADM", 9)]), guild)
    assert asyncio.run(main.exigir_adm(com_adm)) is True

    fora_do_servidor = ContextoFalso(MembroFalso("adm", [("ADM", 9)]))
    fora_do_servidor.guild = None
    assert asyncio.run(main.exigir_adm(fora_do_servidor)) is False

    print("ok - comando administrativo exige o cargo ADM")


def main_teste() -> None:
    with tempfile.TemporaryDirectory() as temp:
        pasta = Path(temp)

        testar_palavras_bloqueadas()
        testar_isencao_automod()
        testar_arquivo_automod(pasta)
        testar_aplicar_automod()
        testar_motivo_de_nao_punir()
        testar_exigir_adm()

    print("\nTodos os testes administrativos passaram!")


if __name__ == "__main__":
    main_teste()
