#!/usr/bin/env bash
# Layout de partições — CachyOS. Antes: _particionar.ps1 (Windows).
#
# O original encolhia o C: em 40 GiB para reservar espaço pro Linux.
# A migração JÁ ACABOU: o Windows não existe mais neste disco, então não há
# nada a encolher. Este script é SOMENTE LEITURA: mostra o layout e gera um
# backup do mapa de partições. Nenhuma partição é criada, redimensionada ou
# apagada aqui — para isso, use parted/sfdisk à mão e com backup.
set -u

GB() { awk -v b="${1:-0}" 'BEGIN { printf "%.2f", b / 1024 / 1024 / 1024 }'; }
tem_root() { [ "$(id -u)" -eq 0 ] || sudo -n true 2>/dev/null; }

echo "=== ESTADO ATUAL ==="
df -hT -x tmpfs -x devtmpfs -x squashfs
echo
lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,PTTYPE

echo
echo "=== MAPA DE PARTICOES (somente leitura) ==="
if tem_root; then
    sudo fdisk -l | grep -Ev '^$'
else
    echo "sem sudo — mapa completo exigiria: sudo fdisk -l"
fi

echo
echo "=== BACKUP DO MAPA (sfdisk -d) ==="
if tem_root; then
    bak="$HOME/sda_sfdisk_$(date +%Y%m%d).txt"
    if sudo sfdisk -d /dev/sda >"$bak" 2>/dev/null; then
        echo "mapa salvo em: $bak"
        echo "restore (emergência): sudo sfdisk /dev/sda < $bak"
    else
        echo "não foi possível ler o mapa de /dev/sda"
    fi
else
    echo "precisa de sudo: sudo sfdisk -d /dev/sda"
fi

echo
echo "=== ESPACO LIVRE NAO ALOCADO ==="
sudo -n sfdisk -l /dev/sda 2>/dev/null | grep -E 'Disk .* free space' \
    || echo "nenhuma faixa livre (disco inteiro usado por ESP + btrfs)"

echo
echo "=== SUBVOLUMES BTRFS (como o espaço está dividido) ==="
if ! btrfs subvolume list / 2>/dev/null; then
    echo "sem permissão (rode com sudo): btrfs subvolume list /"
fi

echo
echo "--- nada foi alterado ---"
echo "Se algum dia precisar redimensionar: faça snapshot/boot de emergência antes"
echo "e use 'sudo parted /dev/sda' (ou 'btrfs filesystem resize' para a subvol /)."
