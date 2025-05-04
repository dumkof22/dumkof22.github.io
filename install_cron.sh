#!/bin/bash

# Bu script Ubuntu'da cronjob kurar

# Script'in çalıştırılacağı yolu belirle
SCRIPT_PATH="$(readlink -f "$(dirname "$0")")"
UPDATE_SCRIPT="$SCRIPT_PATH/update_channels.sh"

# Çalıştırma izni ver
chmod +x "$UPDATE_SCRIPT"

# Mevcut cron işlerini yedekle
crontab -l > cron_backup 2>/dev/null || echo "# Yeni crontab dosyası" > cron_backup

# Cron görevini ekle (her gün sabah 05:00'de çalışacak)
if ! grep -q "$UPDATE_SCRIPT" cron_backup; then
    echo "# Selçuk Spor kanallarını günlük güncelleme" >> cron_backup
    echo "0 5 * * * $UPDATE_SCRIPT" >> cron_backup
    
    # Crontab'ı güncelle
    crontab cron_backup
    echo "Cron görevi başarıyla eklendi! Her gün saat 05:00'de çalışacak."
else
    echo "Cron görevi zaten mevcut."
fi

# Geçici dosyayı sil
rm cron_backup

echo "Kurulum tamamlandı."

# Sistem başlangıcında server'ı başlatmak için (isteğe bağlı)
echo "Sistem başlangıcında server'ı otomatik başlatmak için /etc/rc.local dosyasına aşağıdaki satırı ekleyebilirsiniz:"
echo "cd $SCRIPT_PATH && node server.js &" 
