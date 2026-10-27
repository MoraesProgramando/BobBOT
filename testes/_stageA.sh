#!/usr/bin/env bash
# Etapa A: recuperação de espaço com log em _log_stageA.txt.
# Antes: _stageA.ps1 (Windows: fechava o mmc, rodava defrag C: /X e media o limite).
#
# No Linux não há Gerenciamento de Disco para fechar; o equivalente é garantir
# que nada esteja com o disco preso (balance em andamento) e rodar fstrim +
# balance, medindo antes e depois. Tudo é registrado em _log_stageA.txt.
set -u

logGeral="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/_log_stageA.txt"
GB() { awk -v b="${1:-0}" 'BEGIN { printf "%.2f", b / 1024 / 1024 / 1024 }'; }
livre_gb() { df --output=avail -B1 / | tail -n1; }

log() { printf '%s\n' "$1"; printf '%s\n' "$1" >>"$logGeral"; }

printf '=== ETAPA A %s ===\n' "$(date '+%d/%m/%Y %H:%M:%S')"

if ! sudo -n true 2>/dev/null; then
    log "sem sudo — fstrim/balance precisam de root. Abortando."
    exit 1
fi

# só a partir daqui o log é reescrito (um aborto não apaga o histórico)
printf '=== ETAPA A %s ===\n' "$(date '+%d/%m/%Y %H:%M:%S')" >"$logGeral"

log "=== Verificando processos com o disco ocupado ==="
ocupado=$(pgrep -a 'btrfs' 2>/dev/null | grep -v 'pgrep' || true)
if [ -n "$ocupado" ]; then
    log "$ocupado"
    log "-> já há operação btrfs em andamento; rodar outra em paralelo é inseguro."
    exit 1
fi
log "nenhuma operação btrfs em andamento"
sleep 2

LIVRES=$(livre_gb)
log "Espaço livre no início: $(GB "$LIVRES") GB"

log "=== fstrim / ==="
sudo fstrim -v / >>"$logGeral" 2>&1 || log "fstrim falhou"

agora=$(livre_gb)
log "Espaço livre após fstrim: $(GB "$agora") GB (+$(GB "$(( agora - LIVRES ))") GB)"
LIVRES=$agora

log "=== balance de blocos (uso < 50%) ==="
if sudo btrfs balance start -dusage=50 -musage=50 / >>"$logGeral" 2>&1; then
    log "balance concluído"
else
    log "balance falhou ou foi interrompido"
fi

agora=$(livre_gb)
log "Espaço livre após balance: $(GB "$agora") GB (+$(GB "$(( agora - LIVRES ))") GB)"

log "=== RESULTADO ETAPA A: $(GB "$agora") GB livres ==="
echo
df -h / | tail -n 1
echo "log completo em: $logGeral"
