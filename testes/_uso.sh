#!/usr/bin/env bash
# Ocupação de disco — CachyOS. Antes: _uso.ps1 (Windows).
# Somente leitura: só mede, nunca apaga.
set -u

GB() { awk -v b="${1:-0}" 'BEGIN { printf "%.2f", b / 1024 / 1024 / 1024 }'; }

# Soma (em GB) do que existe dentro de um diretório.
pasta_gb() {
    [ -d "$1" ] || { echo "-"; return; }
    GB "$(du -sb "$1" 2>/dev/null | cut -f1)"
}

echo "=== DISCOS ==="
lsblk -d -o NAME,SIZE,ROTA,TRAN,MODEL 2>/dev/null
echo
df -hT -x tmpfs -x devtmpfs -x squashfs

echo
echo "=== TOPO DE / (tamanho por pasta) ==="
for p in /*; do
    [ -d "$p" ] || continue
    printf '%-28s %6s GB\n' "$p" "$(pasta_gb "$p")"
done | sort -k2 -nr

echo
echo "=== PERFIL DO USUARIO: $HOME (top 12) ==="
for p in "$HOME"/*/ "$HOME"/.[!.]*/; do
    [ -d "$p" ] || continue
    printf '%-40s %6s GB\n' "${p/#$HOME/\~}" "$(pasta_gb "$p")"
done | sort -k2 -nr | head -n 12

echo
echo "=== ARQUIVOS > 500 MB ==="
find / -xdev -type f -size +500M -printf '%s\t%p\n' 2>/dev/null \
    | sort -rn | head -n 30 \
    | awk -F'\t' '{ printf "%8.2f GB  %s\n", $1/1024/1024/1024, $2 }'

echo
echo "=== PASTAS DE SISTEMA GRANDES ==="
for p in /usr /opt /var/cache /var/log /var/lib /var/tmp /snap /var/lib/flatpak /var/lib/docker; do
    [ -d "$p" ] || continue
    printf '%-24s %6s GB\n' "$p" "$(pasta_gb "$p")"
done

echo
echo "=== LIXO POTENCIAL ==="
for p in "$HOME/.cache" "$HOME/.local/share/Trash" /tmp /var/cache/pacman/pkg /var/log/journal; do
    [ -e "$p" ] || continue
    printf '%-40s %6s GB\n' "${p/#$HOME/\~}" "$(pasta_gb "$p")"
done
if command -v journalctl >/dev/null 2>&1; then
    echo "journal: $(journalctl --disk-usage 2>/dev/null | sed 's/.*: //')"
fi
if command -v paccache >/dev/null 2>&1; then
    echo "cache do pacman: $(paccache -dk0 2>/dev/null | tail -n 1)"
fi
