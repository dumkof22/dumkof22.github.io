#!/bin/bash

# Bu script systemd servisini kurar

# Root yetkisi kontrolü
if [ "$EUID" -ne 0 ]; then
    echo "Bu script root yetkisi ile çalıştırılmalıdır."
    echo "Lütfen 'sudo ./install_service.sh' komutu ile çalıştırın."
    exit 1
fi

# Script'in çalıştırılacağı yolu belirle
SCRIPT_PATH="$(readlink -f "$(dirname "$0")")"
SERVICE_FILE="$SCRIPT_PATH/selcuk-server.service"
SERVICE_NAME="selcuk-server.service"

# Mevcut kullanıcı adını al
CURRENT_USER=$(logname)

# Servis dosyasını düzenle (kullanıcı adı ve çalışma dizini)
sed -i "s|User=KULLANICI_ADINIZ|User=$CURRENT_USER|g" "$SERVICE_FILE"
sed -i "s|WorkingDirectory=/tam/yol/projeye|WorkingDirectory=$SCRIPT_PATH|g" "$SERVICE_FILE"

# Servis dosyasını systemd dizinine kopyala
cp "$SERVICE_FILE" /etc/systemd/system/

# Systemd'yi yeniden yükle
systemctl daemon-reload

# Servisi etkinleştir ve başlat
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo "Servis başarıyla kuruldu ve başlatıldı."
echo "Servis durumunu kontrol etmek için: sudo systemctl status $SERVICE_NAME"
echo "Servisi durdurmak için: sudo systemctl stop $SERVICE_NAME"
echo "Servisi yeniden başlatmak için: sudo systemctl restart $SERVICE_NAME" 
