#!/usr/bin/env bash
# Diagnóstico de criptografia, TPM e filesystem — CachyOS.
# Antes: _bitlocker_diag.ps1 (Windows: manage-bde, Get-BitLockerVolume, Get-Tpm).
# Somente leitura: nada é alterado.
set -u

GB() { awk -v b="${1:-0}" 'BEGIN { printf "%.2f", b / 1024 / 1024 / 1024 }'; }

echo "=== DISCO / FILESYSTEM (antes: fsutil ntfsinfo) ==="
lsblk -o NAME,SIZE,FSTYPE,LABEL,UUID,MOUNTPOINTS
echo
stat -f -c 'tipo=%T bloco=%S blocos livres=%f blocos usados=%c' /
echo
df -hT -x tmpfs -x devtmpfs -x squashfs

echo
echo "=== BTRFS ==="
btrfs filesystem show 2>/dev/null || echo "sem permissão para 'btrfs filesystem show'"
sudo -n btrfs filesystem usage -T / 2>/dev/null || echo "sem sudo para 'btrfs filesystem usage'"

echo
echo "=== CRIPTOGRAFIA (antes: manage-bde -status) ==="
if lsblk -o FSTYPE | grep -qi 'crypto_LUKS'; then
    echo "há volume LUKS no disco:"
    lsblk -o NAME,FSTYPE,SIZE | grep -i -B1 crypto_LUKS
    for v in /dev/mapper/*; do
        [ -e "$v" ] || continue
        sudo -n cryptsetup status "$v" 2>/dev/null && echo
    done
    echo "para abrir: sudo cryptsetup open /dev/sdaX <nome>"
else
    echo "sem LUKS: o conteúdo do disco está em texto puro (sem criptografia)."
fi

echo
echo "=== TPM (antes: Get-Tpm) ==="
if [ -d /sys/class/tpm/tpm0 ]; then
    echo "TPM presente: $(cat /sys/class/tpm/tpm0/tpm_version_major 2>/dev/null | tr -d '\n').x"
    if command -v tpm2_getcap >/dev/null 2>&1; then
        sudo -n tpm2_getcap properties-fixed 2>/dev/null | head -n 12 || true
    fi
else
    echo "nenhum TPM visível em /sys/class/tpm"
fi

echo
echo "=== SECURE BOOT ==="
if command -v mokutil >/dev/null 2>&1; then
    mokutil --sb-state 2>/dev/null || echo "não foi possível consultar"
elif [ -d /sys/firmware/efi ]; then
    echo "UEEFI presente; Secure Boot: $(for f in /sys/firmware/efi/efivars/SecureBoot-*; do od -An -tu1 -j4 -N1 "$f" 2>/dev/null; done | tr -d ' ')"
else
    echo "boot Legacy/BIOS (sem variáveis UEFI)"
fi

echo
echo "=== ESPACO / LIMITE DE OCUPACAO (antes: Get-PartitionSupportedSize) ==="
df -h / | tail -n 1
echo "livre: $(df --output=avail -B1 / | tail -n1 | awk '{printf "%.2f GB", $1/1024/1024/1024}')"
sudo -n btrfs filesystem df / 2>/dev/null || echo "(btrfs filesystem df precisa de sudo)"

echo
echo "=== ÚLTIMOS EVENTOS DE fstrim (antes: evento de defrag) ==="
journalctl -u fstrim --no-pager -n 5 --output=short-iso 2>/dev/null || echo "(sem registro)"
