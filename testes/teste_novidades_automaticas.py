"""Testa o envio automático do /novidades sem conectar ao Discord."""

import asyncio
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import main  # noqa: E402


CHANGELOG_BASE = """# Novidades do BOB BOT

## 22/10/2026 — Comando para organizar os cargos

### Novos comandos
- `/organizar_cargos` — reorganiza os cargos.

## 21/10/2026 — Comandos antigos

### Melhorias
- Algo antigo.
"""

CHANGELOG_ANTIGO_EDITADO = CHANGELOG_BASE.replace(
    "Algo antigo.",
    "Algo antigo, com outro texto."
)

CHANGELOG_NOVO = """# Novidades do BOB BOT

## 23/10/2026 — Novidades automáticas

### Melhorias
- O bot posta as novidades sozinho.

## 22/10/2026 — Comando para organizar os cargos

### Novos comandos
- `/organizar_cargos` — reorganiza os cargos.
"""


class CanalFalso:
    def __init__(self):
        self.enviados = []

    async def send(self, **kwargs):
        self.enviados.append(kwargs)


class BotFalso:
    def __init__(self, canal):
        self.canal = canal

    def get_channel(self, _id):
        return self.canal


def preparar_arquivos(pasta: Path, conteudo: str) -> None:
    changelog = pasta / "CHANGELOG.md"
    changelog.write_text(conteudo, encoding="utf-8")
    main.CAMINHO_CHANGELOG = changelog
    main.CAMINHO_ULTIMA_NOVIDADE = pasta / "logs" / "ultima_novidade.txt"


def testar_assinatura(pasta: Path) -> None:
    preparar_arquivos(pasta, CHANGELOG_BASE)
    base = main.assinatura_ultima_atualizacao()

    preparar_arquivos(pasta, CHANGELOG_ANTIGO_EDITADO)
    antigo_editado = main.assinatura_ultima_atualizacao()

    preparar_arquivos(pasta, CHANGELOG_NOVO)
    novo = main.assinatura_ultima_atualizacao()

    assert base, "a assinatura não pode ser vazia"
    assert base == antigo_editado, "editar entrada antiga não pode mudar a assinatura"
    assert base != novo, "entrada nova precisa mudar a assinatura"
    print("ok: assinatura acompanha só a atualização mais recente")


def testar_envio(pasta: Path) -> None:
    canal = CanalFalso()
    bot_falso = BotFalso(canal)

    preparar_arquivos(pasta, CHANGELOG_BASE)
    asyncio.run(main.enviar_novidades_automaticamente(bot_falso))
    assert len(canal.enviados) == 1, "primeira vez deve enviar"

    asyncio.run(main.enviar_novidades_automaticamente(bot_falso))
    assert len(canal.enviados) == 1, "sem mudança não pode enviar de novo"

    preparar_arquivos(pasta, CHANGELOG_ANTIGO_EDITADO)
    asyncio.run(main.enviar_novidades_automaticamente(bot_falso))
    assert len(canal.enviados) == 1, "editar o histórico não reenvia"

    preparar_arquivos(pasta, CHANGELOG_NOVO)
    asyncio.run(main.enviar_novidades_automaticamente(bot_falso))
    assert len(canal.enviados) == 2, "atualização nova precisa enviar"

    embed = canal.enviados[-1]["embed"]
    assert "Novidades automáticas" in embed.description, (
        f"o embed deve trazer a atualização nova, veio: {embed.description!r}"
    )

    print("ok: envia uma vez por atualização e não duplica")


def main_teste() -> None:
    with tempfile.TemporaryDirectory() as temp:
        pasta = Path(temp)

        testar_assinatura(pasta)
        preparar_arquivos(pasta, CHANGELOG_BASE)
        (pasta / "logs").mkdir(exist_ok=True)
        testar_envio(pasta)


if __name__ == "__main__":
    main_teste()
