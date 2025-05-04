#!/bin/bash

# Log dosyası için dizin
LOG_DIR="$HOME/logs"
LOG_FILE="$LOG_DIR/channel_update_$(date +\%Y-\%m-\%d).log"

# Log dizinini oluştur
mkdir -p "$LOG_DIR"

# Çalışma dizinine git (bu dosyanın bulunduğu dizin)
cd "$(dirname "$0")"

echo "$(date): Kanal güncelleme başlatılıyor..." >> "$LOG_FILE"

# Python script'i çalıştır
echo "$(date): Selçuk Kanal Bulma script'i çalıştırılıyor..." >> "$LOG_FILE"
python3 selcuk_channel_finder.py >> "$LOG_FILE" 2>&1
PYTHON_EXIT_CODE=$?

if [ $PYTHON_EXIT_CODE -ne 0 ]; then
    echo "$(date): Python script'i hata verdi! (Çıkış kodu: $PYTHON_EXIT_CODE)" >> "$LOG_FILE"
else
    echo "$(date): Python script'i başarıyla tamamlandı." >> "$LOG_FILE"
    
    # Node.js script'i çalıştır
    echo "$(date): Node.js kanal güncelleyici çalıştırılıyor..." >> "$LOG_FILE"
    node selcuk_channel_updater.js >> "$LOG_FILE" 2>&1
    NODE_EXIT_CODE=$?
    
    if [ $NODE_EXIT_CODE -ne 0 ]; then
        echo "$(date): Node.js kanal güncelleyici hata verdi! (Çıkış kodu: $NODE_EXIT_CODE)" >> "$LOG_FILE"
    else
        echo "$(date): Node.js kanal güncelleyici başarıyla tamamlandı." >> "$LOG_FILE"
        
        # Server'ı yeniden başlat veya başlat
        # Eğer server zaten çalışıyorsa
        if pgrep -f "node server.js" > /dev/null; then
            echo "$(date): Server yeniden başlatılıyor..." >> "$LOG_FILE"
            pkill -f "node server.js"
            sleep 2
        else
            echo "$(date): Server başlatılıyor..." >> "$LOG_FILE"
        fi
        
        # Server'ı başlat
        node server.js >> "$LOG_FILE" 2>&1 &
        echo "$(date): Server başlatıldı (PID: $!)" >> "$LOG_FILE"
    fi
fi

echo "$(date): İşlem tamamlandı." >> "$LOG_FILE" 
