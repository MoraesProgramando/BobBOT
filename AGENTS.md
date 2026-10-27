# Convenções do projeto

## Sempre atualizar o CHANGELOG.md

Toda mudança no bot — comando novo, mudança de comportamento, correção que os membros percebem — precisa de uma entrada no [CHANGELOG.md](CHANGELOG.md), no topo, com a data.

O comando `/novidades` monta o embed lendo esse arquivo, então ele é a fonte única: changelog atualizado é o que os membros veem no Discord. Ao iniciar, o bot compara a atualização mais recente do arquivo com `logs/ultima_novidade.txt` e posta o embed sozinho no canal `1557946258973270120` quando ela mudou — não precisa mandar na mão. Escreva pensando em quem só usa o bot (sem token, caminho de arquivo ou nome de função) e mantenha o arquivo abaixo de 2000 caracteres para caber numa mensagem do Discord.

## Estrutura do CHANGELOG.md

- `#` título do documento;
- `##` uma entrada por atualização, no formato `data — resumo`;
- `###` cada seção (Novos comandos, Melhorias, Correções...), que vira um campo do embed.

## Estrutura de pastas

- `main.py` — o bot inteiro (raiz, porque é o ponto de entrada).
- `imagens/` — as imagens que o bot envia; o código as procura em `BASE_DIR / "imagens"`.
- `logs/` — saída do bot quando roda em segundo plano (ignorada pelo Git).
- `testes/` — scripts e imagens soltas de teste (não afetam o bot).
- Na raiz ficam só o código, o `.env`, os documentos (`AGENTS.md`, `CHANGELOG.md`, `PLANO.md`) e os launchers: `iniciar_bot.sh` com o `bob-bot.service` no Linux, e o `iniciar_bot.vbs` do Windows (descartar depois da migração).
- `PLANO.md` guarda o que está planejado para as próximas sessões; atualize-o quando uma tarefa for concluída ou uma decisão for tomada.

## Como rodar

- `./iniciar_bot.sh` (ou `python main.py` em primeiro plano, para ver o log ao vivo).
- Token e canal ficam no `.env` (nunca no código). O `.env` está no `.gitignore`.
- Dependências: `discord.py` 2.x e `Pillow`. No Arch/CachyOS o pip do sistema é bloqueado, então use uma venv — e o `iniciar_bot.sh` já a encontra sozinho em `.venv/`:
  `python -m venv .venv && .venv/bin/python -m pip install -U discord.py pillow`

## Início automático (Linux / CachyOS)

- `iniciar_bot.sh` sobe o bot em segundo plano, grava a saída em `logs/bot.log`, anota o PID em `logs/bot.pid` e sai sem fazer nada se já houver uma instância rodando. Com `--esperar` ele adia 15s, para o caso de a rede ainda estar subindo no login.
- `bob-bot.service` é a unidade systemd de usuário que sobe o bot junto com o login — o equivalente ao atalho que ficava na pasta Inicializar do Windows. Instalar: copiar para `~/.config/systemd/user/`, rodar `systemctl --user daemon-reload` e `systemctl --user enable --now bob-bot`. Se a pasta do projeto não for `~/bob-bot`, ajustar os caminhos do arquivo.
- Para parar: `systemctl --user stop bob-bot` (se veio do serviço) ou `kill $(cat logs/bot.pid)` (se veio do script).
- Para reiniciar: `systemctl --user restart bob-bot` ou rodar o script de novo — ele espera e sobe uma única instância.
- Log: `journalctl --user -u bob-bot -f` quando roda pelo serviço; `logs/bot.log` quando roda pelo script.

## Ao alterar o código

- Testar sem conectar ao Discord quando possível (importar o módulo e chamar os callbacks com objetos falsos).
- **Reiniciar o bot** depois de qualquer mudança: editar o arquivo não afeta o processo que já está rodando.
- Conferir se há mais de uma instância rodando antes de subir outra — duplicada, o bot responde tudo em dobro.
