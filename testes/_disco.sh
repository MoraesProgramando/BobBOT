#!/usr/bin/env bash
# Diagnóstico de discos, partições e espaço — CachyOS + btrfs.
# Antes: _disco.ps1 (Windows: Get-Volume / Get-PhysicalDisk / Get-Partition).
# Somente leitura: nada é alterado.
set -u

GB() { awk -v b="${1:-0}" 'BEGIN { printf "%.1f", b / 1024 / 1024 / 1024 }'; }
tem_root() { [ "$(id -u)" -eq 0 ] || sudo -n true 2>/dev/null; }

echo "=== VOLUMES (df) ==="
df -hT -x tmpfs -x devtmpfs -x squashfs

echo
echo "=== DISCOS E PARTICOES (lsblk) ==="
lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,UUID,MOUNTPOINTS

echo
echo "=== TABELA DE PARTICOES ==="
if tem_root; then
    sudo fdisk -l 2>/dev/null | grep -Ev '^$'
else
    echo "sem sudo — rode de novo com sudo para ver a tabela completa"
    lsblk -o NAME,SIZE,PARTTYPENAME,FSTYPE,PARTUUID
fi

echo
echo "=== BTRFS: uso por subvolume ==="
if ! btrfs filesystem usage -T / 2>/dev/null; then
    echo "sem permissão (rode com sudo): btrfs filesystem usage -T /"
fi

echo
echo "=== SUBVOLUMES ==="
subs=$(btrfs subvolume list / 2>/dev/null)
if [ -n "$subs" ]; then
    echo "$subs"
elif subs=$(sudo -n btrfs subvolume list / 2>/dev/null) && [ -n "$subs" ]; then
    echo "$subs"
else
    echo "sem permissão para listar subvolumes (rode com sudo)"
fi

echo
echo "=== ESPACO LIVRE REAL (btrfs desconta metadados) ==="
sudo -n btrfs filesystem df / 2>/dev/null || echo "sem permissão"

echo
echo "=== SWAP / ZRAM (antes: pagefile do Windows) ==="
cat /proc/swaps
if [ -f /sys/module/zram/parameters/disksize ]; then
    echo "zram disksize = $(GB "$(cat /sys/module/zram/parameters/disksize)") GB"
fi
echo "hibernação disponível: $(cat /sys/power/state 2>/dev/null | tr -d '\n')"

echo
echo "=== TRIM / FSTRIM (antes: defrag /X) ==="
systemctl list-timers fstrim.timer --no-pager 2>/dev/null | head -n 3
echo "último fstrim:"
journalctl -u fstrim --no-pager -n 3 2>/dev/null || echo "(sem registro)"

echo
echo "=== SECURE BOOT / FIRMWARE (antes: Confirm-SecureBootUEFI) ==="
if [ -d /sys/firmware/efi ]; then
    echo "boot: UEFI"
else
    echo "boot: Legacy/BIOS"
fi
if command -v mokutil >/dev/null 2>&1; then
    mokutil --sb-state 2>/dev/null
elif [ -r /sys/firmware/efi/efivars/SecureBoot-* ]; then
    # último byte: 0 = desligado, 1 = ligado
    estado=$(for f in /sys/firmware/efi/efivars/SecureBoot-*; do od -An -tu1 -j4 -N1 "$f" 2>/dev/null; done | tr -d ' ')
    echo "SecureBoot efivar: ${estado:-desconhecido}"
fi
bootctl status 2>/dev/null | grep -E '^(Product|Secure Boot|EFI Variable)' || true

echo
echo "=== CRIPTOGRAFIA (antes: BitLocker) ==="
lsblk -o NAME,FSTYPE,PARTLABEL | grep -E 'crypto_LUKS|LUKS' && echo "-> há volume LUKS (use: cryptsetup status <nome>)" || echo "sem LUKS: disco em texto puro"
