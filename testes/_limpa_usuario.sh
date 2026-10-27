#!/usr/bin/env bash
# Limpeza só do usuário (sem sudo) — CachyOS. Antes: _limpa_usuario.ps1 (Windows).
# Apaga caches de app e mostra quanto foi liberado antes/depois.
# Confirmação obrigatória; use -y para não perguntar.
set -u

GB() { awk -v b="${1:-0}" 'BEGIN { printf "%.2f", b / 1024 / 1024 / 1024 }'; }
livre_gb() { df --output=avail -B1 / | tail -n1; }

# O que a versão Windows limpava          → equivalente Linux
alvos=(
    "$HOME/.cache/thumbnails"             # Explorer: cache de miniaturas
    "$HOME/.cache/pip"                     # pip cache
    "$HOME/.npm/_cacache"                  # npm cache
    "$HOME/.bun/install/cache"             # bun install cache
    "$HOME/.cache/Code/Cache"              # VSCode Cache
    "$HOME/.cache/Code/CachedData"         # VSCode CachedData
    "$HOME/.cache/Code/CachedExtensionVSIXs"
    "$HOME/.config/Code/Cache"
    "$HOME/.local/share/Trash"             # lixeira
    "$HOME/.cache/crash-reports"           # crash dumps
    "$HOME/.cache/mesa_shader_cache"
)

LIVRES_ANTES=$(livre_gb)
echo "ANTES: livres $(GB "$LIVRES_ANTES") GB"
df -h / | tail -n 1

if [ "${1:-}" != "-y" ]; then
    echo
    read -r -p "Vou apagar o conteúdo desses caches (nada fora deles). Continuar? [s/N] " resp
    case "$resp" in s|S|sim|SIM) ;; *) echo "cancelado."; exit 0 ;; esac
fi

echo
for p in "${alvos[@]}"; do
    if [ ! -d "$p" ]; then
        continue
    fi
    antes=$(du -sb "$p" 2>/dev/null | cut -f1)
    # limpa só o conteúdo, mantendo a pasta (alguns apps quebram sem ela)
    find "$p" -mindepth 1 -delete 2>/dev/null
    depois=$(du -sb "$p" 2>/dev/null | cut -f1)
    printf '%-46s -> liberado %6s GB\n' "${p/#$HOME/\~}" \
        "$(GB "$(( ${antes:-0} - ${depois:-0} ))")"
done

echo
LIVRES_DEPOIS=$(livre_gb)
echo "DEPOIS: livres $(GB "$LIVRES_DEPOIS") GB"
echo "liberado no total: $(GB "$(( LIVRES_DEPOIS - LIVRES_ANTES ))") GB"
