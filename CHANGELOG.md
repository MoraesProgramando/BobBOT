# Novidades do BOB BOT

## 26/10/2026 — Cargo em dois toques

### Novos comandos
- `?role add @membro @cargo` e `?role remove @membro @cargo` dão e tiram cargos (também no `/role add`).
- Só o **dono** ou o cargo **ADM** usa; o cargo fica abaixo de quem usou e do BobBOT.

## 25/10/2026 — Automod não pune quem manda

### Melhorias
- O automod não apaga mais a mensagem de quem tem os cargos **dono** ou **adm**.
- Agora dá para usar `?automod remover` sem a própria mensagem ser censurada.
- Tentar bloquear um cargo em vez de palavra é recusado com aviso.

## 24/10/2026 — Limpeza de mensagens

### Novos comandos
- `/clear` (ou `?clear`) — apaga de 1 a 1000 mensagens em lotes: `/clear 50`.
- Só o dono do servidor, administradores e o cargo **ADM** usam.

### Como usar
- Confirmação discreta: some sozinha no `?clear` e só você vê no `/clear`.
- Mensagens com mais de 14 dias saem uma por uma; se o canal tiver menos que o pedido, o bot diz quantas apagou de verdade.

## 23/10/2026 — Moderação e automod

### Novos comandos
- `/lock` e `/unlock` fecham e abrem um canal; `/kick`, `/ban` e `/unban` (desbanir é pelo ID); `/mute` e `/unmute` silenciam por alguns minutos.
- `/automod add`, `/automod remover` e `/automod listar` escolhem as palavras censuradas.

### Como usar
- Só o cargo **ADM** usa esses comandos.
- A mensagem com palavra bloqueada é apagada e o bot avisa: "Ei! @fulano você não pode falar isto!".
- Quem tem o cargo automod não é censurado.

## 22/10/2026 — Comando de cargos e novidades no canal

### Novos comandos
- `/organizar_cargos` (ou `?organizar_cargos`) — reorganiza os cargos na ordem recomendada: Dono e ADM em cima, identidade no meio, bots embaixo. Só o cargo **ADM**.

### Melhorias
- O comando avisa o que não foi movido e pede para arrastar na mão os cargos criados por outros bots (Loritta, Jockie Music…).
- O bot posta as novidades **sozinho** a cada atualização. Não precisa mais pedir `/novidades`.