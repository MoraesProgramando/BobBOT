#!/usr/bin/env bash
# Recupera espaço com fstrim + balance do btrfs, medindo a cada tentativa.
# Antes: _defrag_v2.ps1 (Windows: defrag C: /X em loop até liberar 40 GiB).
#
# No Linux não há "consolidação de espaço livre" de partição: no btrfs o
# equivalente é o TRIM (fstrim) e o balanceamento de blocos. O alvo antigo
# (40960 MiB) agora é só informativo — aqui a meta é quantos GB a mais de
# espaço livre conseguimos.
#
# Precisa de sudo nas etapas de escrita. Confirma antes; use -y para pular.
set -u

GB() { awk -v b="${1:-0}" 'BEGIN { printf "%.2f", b / 1024 / 1024 / 1024 }'; }
livre_gb() { df --output=avail -B1 / | tail -n1; }
max_tentativas=3

if [ "$(id -u)" -ne 0 ] && ! sudo -n true 2>/dev/null; then
    echo "este script precisa de sudo (fstrim/balance) — rode com sudo"
    exit 1
fi

if [ "${1:-}" != "-y" ]; then
    read -r -p "fstrim + balance do btrfs (pode levar minutos). Continuar? [s/N] " resp
    case "$resp" in s|S|sim|SIM) ;; *) echo "cancelado."; exit 0 ;; esac
fi

LIVRES=$(livre_gb)
echo "=== espaco livre no inicio: $(GB "$LIVRES") GB ==="

echo
echo "=== processos que podem segurar espaco (antes: mmc/diskmgmt) ==="
pgrep -a 'timeshift|snapper|btrfsmaintenance' 2>/dev/null || echo "nenhum gerenciador de snapshot ativo"

tentativa=0
while [ "$tentativa" -lt "$max_tentativas" ]; do
    tentativa=$((tentativa + 1))
    echo
    echo "=== TENTATIVA $tentativa: fstrim ==="
    sudo fstrim -v / 2>&1 | tail -n 3

    echo
    echo "=== TENTATIVA $tentativa: balance de blocos (uso < 50%) ==="
    # -d/-m com usage limita o balance ao que está realmente fragmentado,
    # em vez de refazer o disco inteiro.
    sudo btrfs balance start -dusage=50 -musage=50 / 2>&1 | tail -n 4

    agora=$(livre_gb)
    echo "livre agora: $(GB "$agora") GB (+$(GB "$(( agora - LIVRES ))") GB)"
    [ "$agora" -gt "$LIVRES" ] && LIVRES=$agora

    if [ "$agora" -lt "$LIVRES" ]; then
        sleep 5
    fi
done

echo
echo "=== RESULTADO ==="
echo "espaco livre: $(GB "$LIVRES") GB no inicio -> $(GB "$(livre_gb)") GB no fim"
df -h / | tail -n 1
echo "btrfs balance deixou de rodar sozinho quando terminou (não mate o processo)."
