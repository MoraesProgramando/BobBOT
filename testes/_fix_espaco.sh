#!/usr/bin/env bash
# Libera espaço de verdade — CachyOS + btrfs. Antes: _fix_espaco.ps1 (Windows).
#
# Equivalente Linux do "limpar $WinREAgent + Windows Update + defrag /X":
#   1) cache antigo do pacman        2) journal do systemd
#   3) cache de miniaturas/lixeira   4) fstrim (btrfs/SSD)
#
# Pede confirmação antes de apagar qualquer coisa. Use -y para não perguntar.
set -u

GB() { awk -v b="${1:-0}" 'BEGIN { printf "%.2f", b / 1024 / 1024 / 1024 }'; }
livre_gb() { df --output=avail -B1 / | tail -n1; }
tem_root() { [ "$(id -u)" -eq 0 ] || sudo -n true 2>/dev/null; }

TEMPO_JOURNAL="7d"
LIVRES_ANTES=$(livre_gb)

echo "=== ANTES ==="
df -h / | tail -n 1
echo "livre: $(GB "$LIVRES_ANTES") GB"

if [ "${1:-}" != "-y" ]; then
    echo
    read -r -p "Isso apaga caches (pacman, journal, miniaturas, lixeira). Continuar? [s/N] " resp
    case "$resp" in s|S|sim|SIM) ;; *) echo "cancelado."; exit 0 ;; esac
fi

echo
echo "=== 1) Cache antigo do pacman (mantém as 2 últimas versoes) ==="
if command -v paccache >/dev/null 2>&1 && tem_root; then
    sudo paccache -rk2 2>&1 | tail -n 5
else
    echo "paccache ausente ou sem sudo — pulando"
fi

echo
echo "=== 2) Journal do systemd (fica com os últimos $TEMPO_JOURNAL) ==="
if tem_root; then
    sudo journalctl --vacuum-time="$TEMPO_JOURNAL" 2>&1 | tail -n 3
else
    echo "sem sudo — pulando (seria: sudo journalctl --vacuum-time=$TEMPO_JOURNAL)"
fi

echo
echo "=== 3) Cache de usuario: miniaturas, lixeira e /tmp do usuario ==="
for p in "$HOME/.cache/thumbnails" "$HOME/.local/share/Trash/files" "/tmp"; do
    [ -d "$p" ] || continue
    antes=$(du -sb "$p" 2>/dev/null | cut -f1)
    find "$p" -mindepth 1 -delete 2>/dev/null || true
    depois=$(du -sb "$p" 2>/dev/null | cut -f1)
    echo "${p/#$HOME/\~} -> liberado $(GB "$(( ${antes:-0} - ${depois:-0} ))") GB"
done

echo
echo "=== 4) fstrim (recupera espaço em SSD/btrfs) ==="
if tem_root; then
    sudo fstrim -v / 2>&1 | tail -n 2
else
    echo "sem sudo — pulando (seria: sudo fstrim -v /)"
fi

echo
echo "=== DEPOIS ==="
df -h / | tail -n 1
LIVRES_DEPOIS=$(livre_gb)
echo "liberado: $(GB "$(( LIVRES_DEPOIS - LIVRES_ANTES ))") GB"
