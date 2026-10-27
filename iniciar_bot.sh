#!/usr/bin/env bash
# Sobe o BOB BOT em segundo plano, sem janela, gravando tudo em logs/bot.log.
# Versão Linux (CachyOS/Arch) do antigo iniciar_bot.vbs.
#
#   ./iniciar_bot.sh             sobe o bot e volta na hora
#   ./iniciar_bot.sh --esperar   espera 15s antes (rede subindo junto com o login)
#
# O bot roda uma vez só: se já existir instância viva, o script sai sem fazer nada.

set -u

pasta="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)" || exit 1
cd "$pasta" || exit 1

pasta_logs="$pasta/logs"
log="$pasta_logs/bot.log"
pidfile="$pasta_logs/bot.pid"
mkdir -p "$pasta_logs"

# ------------------------------------------------------- já tem um rodando?

rodando() {
    local antigo

    # PID que o próprio script guardou continua vivo e ainda é o bot?
    if [ -f "$pidfile" ]; then
        antigo="$(cat "$pidfile" 2>/dev/null)"

        if [ -n "$antigo" ] && kill -0 "$antigo" 2>/dev/null &&
            tr '\0' ' ' <"/proc/$antigo/cmdline" 2>/dev/null |
            grep -q 'main\.py'; then
            return 0
        fi
    fi

    # Instância subida por fora (systemd, terminal): confere pela linha de comando.
    if command -v pgrep >/dev/null 2>&1; then
        pgrep -u "$(id -u)" -f "python[0-9.]* .*main\.py" >/dev/null 2>&1 && return 0
    fi

    return 1
}

if rodando; then
    echo "O BOB BOT já está rodando. Nada a fazer."
    exit 0
fi

# ---------------------------------------------------------------- python

# No Arch o pip do sistema é bloqueado, então o normal é usar a venv do projeto.
if [ -x "$pasta/.venv/bin/python" ]; then
    python="$pasta/.venv/bin/python"
elif [ -n "${PYTHON:-}" ]; then
    python="$PYTHON"
elif command -v python3 >/dev/null 2>&1; then
    python="python3"
else
    python="python"
fi

if ! command -v "$python" >/dev/null 2>&1; then
    echo "Não achei o Python. Instale com: sudo pacman -S python"
    exit 1
fi

if ! "$python" -c "import discord, PIL" >/dev/null 2>&1; then
    echo "Faltam as dependências. Crie a venv e instale:"
    echo "  $python -m venv .venv"
    echo "  .venv/bin/python -m pip install -U discord.py pillow"
    exit 1
fi

if [ "${1:-}" = "--esperar" ]; then
    sleep 15
fi

# ---------------------------------------------------------------- sobe

# -u desliga o buffer: sem ele o log só aparece quando o bot termina.
PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8 \
    nohup "$python" -u "$pasta/main.py" >>"$log" 2>&1 &
pid=$!
echo "$pid" >"$pidfile"

# Se cair logo de cara (token errado, sem internet), mostra o motivo na hora.
sleep 2
if ! kill -0 "$pid" 2>/dev/null; then
    echo "O bot saiu logo depois de subir. Últimas linhas de $log:"
    tail -n 10 "$log"
    exit 1
fi

echo "BOB BOT rodando em segundo plano (pid $pid)."
echo "Log: $log"
