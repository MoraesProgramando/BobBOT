"""Testa a lógica de `calcular_nova_ordem` sem conectar no Discord.

Rodar: python testes/teste_organizar_cargos.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from main import calcular_nova_ordem, tem_cargo_adm  # noqa: E402


class CargoFalso:
    """Objeto mínimo com os atributos usados pela função."""

    def __init__(self, id_cargo, nome, posicao, gerenciado=False):
        self.id = id_cargo
        self.name = nome
        self.position = posicao
        self.managed = gerenciado


def cenarios_do_servidor():
    """Cargos iguais aos da captura, de @everyone (0) para cima."""

    nomes = [
        "BobBOT", "Embed Generator", "Akinator", "Lord", "HornBot",
        "Jockie Music (1)", "Jockie Music", "Loritta", "Tropa da Escola",
        "Resenhudo", "Homem", "Membro", "Dono", "Outro/Prefiro não falar",
        "Mulher", "Bots", "ADM",
    ]

    return [
        CargoFalso(100 + i, nome, i + 1) for i, nome in enumerate(nomes)
    ]


def testar_cenario_normal():
    """BobBOT já subiu no ranking: tudo abaixo dele deve se mover."""

    cargos = cenarios_do_servidor()
    bobbot = cargos[0]  # posição 17 depois de arrastado para o topo
    bobbot.position = 18

    ordem, ignorados = calcular_nova_ordem(
        cargos,
        id_cargo_do_bot=bobbot.id,
        limite_bot=18,
        limite_autor=None
    )

    nomes = [cargo.name for cargo in ordem]

    esperado = [
        "Dono",                                    # liderança
        "ADM",                                     # staff
        "Membro",                                  # base
        "Mulher", "Outro/Prefiro não falar", "Homem",  # identidade
        "Resenhudo", "Tropa da Escola",            # social
        "Bots", "Loritta", "Jockie Music",         # integrações
        "Jockie Music (1)", "HornBot", "Lord",
        "Akinator", "Embed Generator",
    ]

    assert nomes == esperado, f"ordem errada: {nomes}"

    assert [c.name for c, _ in ignorados] == ["BobBOT"]
    assert "arraste" in ignorados[0][1]

    print("ok - cenario normal (BobBOT ja subiu no ranking)")


def testar_cenario_bot_no_fundo():
    """BobBOT no fundo (como na captura): não pode mover nada."""

    cargos = cenarios_do_servidor()
    bobbot = cargos[0]  # posição 1

    ordem, ignorados = calcular_nova_ordem(
        cargos,
        id_cargo_do_bot=bobbot.id,
        limite_bot=1,
        limite_autor=None
    )

    assert ordem == [], f"nada deveria se mover, veio: {ordem}"
    assert len(ignorados) == len(cargos)
    assert all("acima do cargo mais alto do bot" in m or "próprio bot" in m
               for _, m in ignorados)

    print("ok - cenario de alerta (BobBOT no fundo)")


def testar_cargo_integracao_e_nome_com_acento():
    """Cargo managed (integração) não move; nomes com acento casam."""

    cargos = [
        CargoFalso(1, "Dono", 5),
        CargoFalso(2, "Loritta", 4, gerenciado=True),
        CargoFalso(3, "Membro", 3),
        CargoFalso(4, "Outro/Prefiro não falar", 2),
        CargoFalso(5, "Cargo Surpresa", 1),
    ]

    ordem, ignorados = calcular_nova_ordem(
        cargos,
        id_cargo_do_bot=None,
        limite_bot=None,
        limite_autor=None
    )

    nomes = [cargo.name for cargo in ordem]

    assert nomes == [
        "Dono", "Membro", "Outro/Prefiro não falar", "Cargo Surpresa"
    ], f"ordem errada: {nomes}"

    assert [c.name for c, _ in ignorados] == ["Loritta"]
    assert "integração" in ignorados[0][1]

    print("ok - cargo de integracao e nome com acento")


def testar_cargo_adm():
    """Só quem tem o cargo ADM passa na checagem."""

    class MembroFalso:
        def __init__(self, nomes_cargos):
            self.roles = [
                CargoFalso(i, nome, 1) for i, nome in enumerate(nomes_cargos)
            ]

    assert tem_cargo_adm(MembroFalso(["Membro", "ADM"]))
    assert tem_cargo_adm(MembroFalso(["Adm"]))  # maiúscula não importa
    assert not tem_cargo_adm(MembroFalso(["Membro", "ADM da live"]))
    assert not tem_cargo_adm(MembroFalso(["Membro"]))

    print("ok - checagem do cargo ADM")


if __name__ == "__main__":
    testar_cenario_normal()
    testar_cenario_bot_no_fundo()
    testar_cargo_integracao_e_nome_com_acento()
    testar_cargo_adm()
    print("\nTodos os testes passaram!")
