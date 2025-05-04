#!/bin/bash

# Selçuk Sports otomasyon kurulum scripti

echo "Selçuk Sports Otomasyon Kurulumu Başlatılıyor..."

# Scriptlere çalıştırma izni ver
chmod +x update_channels.sh
chmod +x install_cron.sh
chmod +x install_service.sh

echo "Gereksinimler kontrol ediliyor..."

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo "Python 3 yüklü değil. Lütfen yükleyin:"
    echo "sudo apt install python3 python3-pip"
    exit 1
fi

# Node.js kontrolü
if ! command -v node &> /dev/null; then
    echo "Node.js yüklü değil. Lütfen yükleyin:"
    echo "curl -fsSL https://deb.nodesource.com/setup_16.x | sudo -E bash -"
    echo "sudo apt-get install -y nodejs"
    exit 1
fi

echo "Gerekli Python paketleri yükleniyor..."
pip3 install requests beautifulsoup4 --user

echo "Gerekli Node.js paketleri yükleniyor..."
npm install

echo "Otomasyon sistemi kuruldu."
echo ""
echo "Şimdi cron görevini kurmak için:"
echo "./install_cron.sh"
echo ""
echo "Systemd servisi kurmak için (isteğe bağlı):"
echo "sudo ./install_service.sh" 
