#!/usr/bin/env bash
# O que pesa no perfil do usuário — CachyOS + Hyprland.
# Antes: _appdata.ps1 (Windows: AppData\Local, AppData\Roaming, Documents).
# Equivalente Linux: ~/.cache, ~/.local/share, ~/.config e os caches conhecidos.
# Somente leitura.
set -u

GB() { awk -v b="${1:-0}" 'BEGIN { printf "%.2f", b / 1024 / 1024 / 1024 }'; }

pasta_gb() {
    [ -d "$1" ] || { echo "-"; return; }
    GB "$(du -sb "$1" 2>/dev/null | cut -f1)"
}

# $1 = raiz, $2 = quantas pastas mostrar
listar() {
    [ -d "$1" ] || { echo "(não existe: $1)"; return; }
    for p in "$1"/*/; do
        [ -d "$p" ] || continue
        printf '%-46s %6s GB\n' "${p/#$HOME/\~}" "$(pasta_gb "$p")"
    done | sort -k2 -nr | head -n "$2"
}

echo "=== ~/.cache (top 12) ==="
listar "$HOME/.cache" 12

echo
echo "=== ~/.local/share (top 8) ==="
listar "$HOME/.local/share" 8

echo
echo "=== home (pastas visíveis, top 8) ==="
listar "$HOME" 8

echo
echo "=== CACHES CONHECIDOS ==="
for p in \
    "$HOME/.cache/pip" \
    "$HOME/.npm/_cacache" \
    "$HOME/.cache/yay" \
    "$HOME/.cache/paru" \
    "$HOME/.bun/install/cache" \
    "$HOME/.cache/thumbnails" \
    "$HOME/.local/share/Trash" \
    "$HOME/.cache/mesa_shader_cache" \
    "$HOME/.cache/mesa_shader_cache_disk" \
    "$HOME/.vscode-server/.cache" \
    "$HOME/.cache/code" \
    "$HOME/.config/Code/Cache" \
    "$HOME/.cache/BraveSoftware" \
    "$HOME/.cache/google-chrome" \
    "$HOME/.mozilla/firefox" \
    "$HOME/.local/share/Steam" \
    "$HOME/.cache/hyprland" \
    "$HOME/.cache/rofi" \
    "$HOME/.cache/wayland"; do
    [ -e "$p" ] || continue
    printf '%-46s %6s GB\n' "${p/#$HOME/\~}" "$(pasta_gb "$p")"
done

echo
echo "=== PASTA DO PROJETO DO BOT ==="
echo "BOT-DISCORD = $(pasta_gb "$HOME/Projetos/BOT-DISCORD") GB"
