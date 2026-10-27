#!/usr/bin/env bash
# Quanto espaço dá para recuperar — CachyOS + btrfs.
# Antes: _encolher.ps1 (Windows: Optimize-Volume -Analyze, Get-PartitionSupportedSize).
# No Linux não existe "encolhimento de partição": o espaço volta com limpeza
# de cache, snapshots antigos e balance do btrfs. Aqui é só o DIAGNÓSTICO.
set -u

GB() { awk -v b="${1:-0}" 'BEGIN { printf "%.2f", b / 1024 / 1024 / 1024 }'; }

echo "=== MEMORIA RAM ==="
free -h | sed -n '1,3p'

echo
echo "=== ESTADO DO SISTEMA DE ARQUIVOS ==="
df -hT -x tmpfs -x devtmpfs -x squashfs

echo
echo "=== BTRFS: espaco por bloco (data/metadata/system) ==="
sudo -n btrfs filesystem df / 2>/dev/null || echo "sem sudo (btrfs filesystem df precisa de root)"

echo
echo "=== SNAPSHOTS (antes: sombras/pontos de restauracao) ==="
if command -v timeshift >/dev/null 2>&1; then
    timeshift --list 2>/dev/null || true
elif command -v snapper >/dev/null 2>&1; then
    snapper list 2>/dev/null || true
else
    # snapshots btrfs criados à mão
    n=$(sudo -n btrfs subvolume list / 2>/dev/null | grep -ci 'snapshot' || echo 0)
    echo "sem timeshift/snapper; $n subvolume(s) com 'snapshot' no nome"
    sudo -n btrfs subvolume list / 2>/dev/null | head -n 15
fi

echo
echo "=== ARQUIVOS/CONDICOES QUE SEGURAM ESPACO ==="
for p in "$HOME/.cache/thumbnails" "$HOME/.local/share/Trash" /var/cache/pacman/pkg /var/log/journal; do
    [ -e "$p" ] || continue
    printf '%-42s %6s GB\n' "${p/#$HOME/\~}" "$(GB "$(du -sb "$p" 2>/dev/null | cut -f1)")"
done
echo "swap zram em uso: $(awk 'NR>1 {printf "%.1f GB de %.1f GB\n", $3/1024/1024, $4/1024/1024}' /proc/swaps)"

echo
echo "=== TRIM / DEFRAGMENTACAO (estado) ==="
if command -v btrfs >/dev/null 2>&1; then
    echo "fstrim do mês:"
    journalctl -u fstrim --no-pager -n 5 --output=short-iso 2>/dev/null | tail -n 5 || echo "(sem registro)"
fi

echo
echo "=== ESPACO RECUPERAVEL ESTIMADO ==="
total=0
for p in "$HOME/.cache" "$HOME/.local/share/Trash" /var/cache/pacman/pkg; do
    [ -d "$p" ] || continue
    b=$(du -sb "$p" 2>/dev/null | cut -f1)
    total=$((total + ${b:-0}))
done
jrn=$(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[GM]' | head -n1)
echo "caches do usuário + lixeira + cache pacman: $(GB "$total") GB"
echo "journal: ${jrn:-n/d}"
echo "(para liberar de verdade, rode: ./_fix_espaco.sh)"
