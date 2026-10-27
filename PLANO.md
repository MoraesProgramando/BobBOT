# Plano — próximas atualizações do BOB BOT

Anotado em 21/10/2026, para a próxima sessão começar por aqui.

## Estado atual (24/10/2026)

- Bot online com 18 comandos híbridos (`/` e `?`): `ola`, `oi_posso_falar`, `ping`, `avatar`, `dado`, `enquete`, `ajuda`, `novidades`, `organizar_cargos` (staff; testado offline em `testes/teste_organizar_cargos.py`).
- Administração só para o cargo **ADM**: `lock`, `unlock`, `kick`, `ban`, `unban`, `mute`, `unmute` e o grupo `automod` (`add`, `remover`, `listar`). Testado offline em `testes/teste_admin.py`.
- `role` (`?role add @membro @cargo` e `?role remove @membro @cargo`, também no `/role add`): dá e tira cargos. Quem usa: **dono** ou **ADM**; trava de hierarquia igual à do `organizar_cargos` — cargo abaixo de quem usou e do bot, sem `@everyone` e sem cargo de integração. Feito em 26/10/2026.
- `clear`: de 1 a 1000 mensagens, em lotes de 100 (o `purge` do discord.py cuida disso) e com exclusão individual para mensagens com mais de 14 dias. Quem usa: dono do bot, dono do servidor, administradores e cargo **ADM**. Confirmação efêmera no slash e apagada em 10s no prefixo. Testado offline em `testes/teste_clear.py`.
- Automod: palavras ficam em `logs/automod.json`, comparação sem acento e por palavra inteira; quem tem o cargo **automod** não é censurado, e a mensagem barrada não vira comando.
- Boas-vindas com imagem pronta; `?teste` e `?enviar_embed` só com prefixo.
- Início automático: `iniciar_bot.sh` (log em `logs/bot.log`, PID em `logs/bot.pid`, uma instância só) e o serviço systemd de usuário `bob-bot.service` a cada login — troca feita em 25/10/2026 na migração para o CachyOS, substituindo o `iniciar_bot.vbs`.
- O código já é portável: caminhos saem de `BASE_DIR` e a fonte da imagem cai para a DejaVu Sans do Linux quando não acha a do Windows.
- Antes de mexer: `python main.py` não reflete mudança em processo já rodando — sempre reiniciar (`systemctl --user restart bob-bot`).
- Toda mudança percebida pelos membros entra no `CHANGELOG.md` (o `/novidades` lê esse arquivo).
- Ao iniciar, o bot compara a atualização mais recente do changelog com `logs/ultima_novidade.txt` e, se mudou, posta o embed no canal `1557946258973270120` (testado offline em `testes/teste_novidades_automaticas.py`).

## Migração para o Linux — concluída em 25/10/2026

- Raiz limpa: só `main.py`, `.env`, `.gitignore`, os documentos e os dois launchers Linux (`iniciar_bot.sh`, `bob-bot.service`). Acabaram as cópias sem ponto (`env`, `gitignore`) e o `iniciar_bot.vbs` já não existe.
- `iniciar_bot.sh` com permissão de execução (`chmod +x`); venv criada em `.venv/` com `discord.py` 2.7.1 + Pillow 13.0.0.
- `bob-bot.service` com os caminhos corrigidos para `~/Projetos/BOT-DISCORD` e **instalado** no systemd de usuário: sobe a cada login, log no `journalctl --user -u bob-bot`, reinício automático em caso de queda (`Restart=on-failure`).
- Os 10 scripts de manutenção do Windows (`testes/_*.ps1`) viraram `testes/_*.sh` para CachyOS + btrfs: `_disco`, `_uso`, `_encolher`, `_particionar`, `_fix_espaco`, `_appdata`, `_limpa_usuario`, `_defrag_v2`, `_stageA` e `_cripto_diag` (era `_bitlocker_diag`). O alvo antigo de "encolher o C: em 40 GiB" não existe mais — o Windows saiu do disco; agora é limpeza de cache + `fstrim` + `btrfs balance`.
- Só-leitura (`_disco`, `_uso`, `_encolher`, `_particionar`, `_appdata`, `_cripto_diag`) rodam sem sudo; os que alteram (`_fix_espaco`, `_limpa_usuario`, `_defrag_v2`, `_stageA`) pedem confirmação, aceitam `-y` e precisam de sudo.
- `CHANGELOG.md` não ganhou entrada na migração: nada disso é percebido pelos membros.
- **25/10/2026 — automod**: cargos **dono** e **adm** são isentos da censura. Os IDs ficam no `.env` (`AUTOMOD_ISENTOS`) e os nomes "dono"/"adm" valem mesmo sem o .env. Sem isso, o próprio `?automod remover <palavra>` era apagado pelo automod antes de virar comando — o staff não conseguia tirar nada da lista. Cargos também não podem mais ser adicionados à lista de palavras (era o `role <@&…>` que aparecia no `/automod`).

## Ambiente da máquina

- CachyOS, kernel 7.3.0-4-cachyos, Hyprland (Wayland).
- Disco único: `sda` 465,8 GB — `sda1` ESP 512 MB + `sda2` btrfs com `@`, `@home`, `@root`, `@var/log`; swap só em `zram0` (7,5 GB), sem arquivo de swap.
- Sem `yay`, sem `timeshift`/`snapper` — os scripts tratam a ausência como caso normal.

## 1. Mensagem de saída

Espelho do boas-vindas, disparado por `on_member_remove`.

- Cartão com avatar, nome e uma frase de despedida; cor diferente da entrada (hoje o fundo é azul→roxo).
- Reaproveitar `criar_fundo`, `carregar_avatar`, `carregar_fonte`, `encurtar_texto` e `criar_arquivo`.
- Mostrar a contagem de membros atualizada (`member.guild.member_count` já vem decrementado no evento).
- Mesmo tratamento de falha do boas-vindas: canal ausente não pode derrubar o handler.
- Opcional: usar `CANAL_BOAS_VINDAS` ou criar `CANAL_DESPEDIDAS` no `.env`.

## 2. Comandos de administração

Pares de ação e reverso, todos híbridos, com checagem de permissão:

- ~~`/clear [quantidade]` — apagar mensagens (2 a 100). Decidir se preserva fixadas.~~ Feito em 24/10/2026: 1 a 1000, em lotes, sem preservar fixadas.
- `/ban` + `/unban` — por ID ou menção; `unban` precisa do ID do usuário, não do membro.
- `/mute` + `/unmute` — ver decisão sobre timeout x cargo.
- `/lock` + `/unlock` — negar `send_messages` no canal via overwrite, e restaurar depois.
- `/kick`.

Cuidados obrigatórios:

- **Hierarquia**: não agir sobre o dono do servidor, sobre o próprio bot, nem sobre cargo igual/superior ao do bot (`member.top_role`).
- **Permissão do bot**: conferir se ele tem a permissão necessária antes de tentar, e responder com instrução clara se não tiver.
- Ações destrutivas (`ban`, `kick`, `clear`) com confirmação por botão.
- Registrar quem aplicou, em quem e por quê (mensagem no canal ou em canal de log).

## 3. `/embed` customizável

Substituir/evoluir o `?enviar_embed` por um comando com formulário (`discord.ui.Modal`) e prévia antes de enviar:

- Campos: título, descrição, cor (hex), autor, imagem, rodapé.
- Limites do Discord: título 256, descrição 4096, autor/rodapé 256, 25 campos — validar antes de enviar.
- **Restrito**: só quem estiver acima das permissões padrão (definir qual permissão; ver decisões).

## 4. `/perfil`

Exibir do membro: nome, avatar, banner, cargos, data de entrada no servidor, data de criação da conta e status.

E os campos que dependem de dado externo:

- **Bio não é acessível** pela API de bots — o Discord não expõe o "sobre mim". Não prometer esse campo.
- **Banner** só existe se a pessoa tiver um definido, e exige `fetch_user` (chamada extra). Sem banner, mostrar o cartão sem essa área.
- **Gênero, estado civil e idade** não vêm do Discord. Duas opções:
  - **por cargos** (ex.: "Ele/Dele", "Solteiro", "18+"): só ler o que o servidor já tem;
  - **por cadastro** (`/perfil definir`): guardar num arquivo local (JSON), com validação e opção de apagar.

## Decisões pendentes

- [ ] **`clear` apagando sem parar (relatado em 25/10/2026)**: o usuário viu mensagens sendo apagadas "infinitamente" depois do fim do comando. Investigar antes de mexer em mais nada de moderação — pode ser o `purge` com `limit` e mensagens antigas, ou duas instâncias rodando ao mesmo tempo.

- [ ] `/mute`: timeout nativo do Discord (expira sozinho) ou cargo "Mudo"?
- [x] Quem usa admin: permissão de servidor (`manage_guild`/`administrator`) ou cargo específico? Em `organizar_cargos`: só o cargo **ADM** (decidido 21/10/2026). No `clear`: dono do bot, dono do servidor, administradores e cargo **ADM** (decidido 24/10/2026).
- [x] Quem usa o `?role add`/`?role remove`: **dono** ou cargo **ADM**, e o cargo alvo precisa ficar abaixo de quem usou (decidido 26/10/2026).
- [ ] Quem usa `/embed`: qual permissão exatamente ("acima das padrões")?
- [x] `/clear` preserva mensagens fixadas? Não (decidido 24/10/2026: apaga fixadas também).
- [ ] Confirmação por botão nas ações destrutivas: sim ou direto?
- [ ] Gênero/estado civil/idade: cargos ou cadastro próprio?
- [ ] Canal de despedidas: reaproveitar o de boas-vindas ou separar no `.env`?

## Ordem sugerida

1. Mensagem de saída (menor, reaproveita quase tudo).
2. Administração (maior volume de código e de casos de erro).
3. `/embed` (modal + validação + permissão).
4. `/perfil` (depende da decisão sobre cargos ou cadastro).
