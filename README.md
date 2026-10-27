# BobBOT

BobBOT é um bot de Discord escrito em Python com **discord.py 2.x** e **Pillow**.
Todos os comandos principais são **híbridos**: funcionam com o prefixo `?` e
também como slash `/` no servidor.

## Funcionalidades

- **Boas-vindas com imagem** — gera um cartão com avatar e nome quando alguém entra.
- **Novidades automáticas** — lê o `CHANGELOG.md` e publica sozinho no canal de novidades.
- **Automod** — bloqueia palavras da sua lista (guardada em `logs/automod.json`), compara sem acento e por palavra inteira.
- **Moderação** — ban, kick, mute temporário, fechar/abrir canal e limpeza em lote de mensagens.
- **Cargos** — organiza a hierarquia do servidor e dá/tira cargos por comando.
- **Diversão/utilidade** — dado, enquete, avatar, ping e cartão "posso falar?".

## Comandos

### Geral (qualquer membro)

| Comando | O que faz |
| --- | --- |
| `/ola` · `/ping` · `/ajuda` | Teste, latência e lista de comandos |
| `/avatar @membro` | Avatar do membro |
| `/dado` | Rola um dado |
| `/enquete pergunta \| opção1 \| opção2 …` | Enquete com até 5 opções |
| `/novidades` | Mostra as últimas mudanças do bot |
| `/oi_posso_falar` | Botões "Sim/Não" com imagem |

### Administração (dono do servidor ou cargo **ADM**)

| Comando | O que faz |
| --- | --- |
| `/ban` · `/unban` · `/kick` | Banir, desbanir (por ID) e expulsar |
| `/mute` · `/unmute` | Silenciar por N minutos / devolver a fala |
| `/lock` · `/unlock` | Fechar/abrir o canal para membros |
| `/clear 50` | Apaga até 1000 mensagens em lotes |
| `/organizar_cargos` | Reordena os cargos na hierarquia recomendada |
| `/role add @membro @cargo` · `/role remove …` | Dá ou tira um cargo |
| `/automod add\|remover\|listar` | Palavras censuradas |

> Cargos isentos do automod (dono/ADM) são configurados em `AUTOMOD_ISENTOS` no `.env`.

### Só com prefixo `?`

- `?teste` — teste rápido de conexão.
- `?enviar_embed` — envia um embed escrito na mão.

## Requisitos

- Python **3.10 ou superior** (testado em 3.14.8)
- `discord.py` 2.7.1 e `Pillow` 13.0.0 (ver `requirements.txt`)
- Um bot criado no [Discord Developer Portal](https://discord.com/developers/applications)

## Instalação

```bash
git clone https://github.com/MoraesProgramando/BobBOT.git
cd BobBOT

python -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env   # depois edite o .env e cole seu token
```

## Configuração (`.env`)

| Variável | Obrigatória | Descrição |
| --- | --- | --- |
| `DISCORD_TOKEN` | **sim** | Token do bot (Developer Portal → Bot) |
| `CANAL_BOAS_VINDAS` | não | ID do canal de boas-vindas (padrão embutido no código) |
| `CANAL_NOVIDADES` | não | ID do canal de novidades (padrão embutido no código) |
| `AUTOMOD_ISENTOS` | não | IDs dos cargos livres da censura, separados por vírgula |

> O `.env` está no `.gitignore` e **nunca** deve ser enviado ao repositório.

## Execução

```bash
.venv/bin/python main.py                            # primeiro plano (log na tela)
nohup .venv/bin/python main.py >> bot.log 2>&1 &   # em segundo plano
```

## Estrutura

```
main.py           bot inteiro (ponto de entrada)
imagens/          imagens enviadas pelo bot
logs/             saída do bot, automod.json e estado (gitignored)
.env.example      modelo das variáveis de ambiente
CHANGELOG.md      novidades (o /novidades lê este arquivo)
```

## Contribuindo

1. Abra uma **Issue** explicando o problema ou a ideia antes de codar.
2. Crie uma **branch** por tarefa (`git checkout -b feat/role-remove`).
3. Escreva mensagens de commit claras (`git commit -m "feat: ..."`) e envie com `git push`.
4. **Nunca** commite tokens, `.env`, logs ou dados de membros.