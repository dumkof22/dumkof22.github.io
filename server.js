// server.js
// Bu dosya küçük bir proxy sunucusu oluşturur
// Kurulum: npm install express cors axios

const express = require('express');
const cors = require('cors');
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const app = express();
const PORT = process.env.PORT || 3000;

// CORS middleware
app.use(cors());

// Statik dosyaları sunmak için
app.use(express.static('public'));

// Basit loglama için middleware
app.use((req, res, next) => {
    console.log(`[${new Date().toISOString()}] ${req.method} ${req.url}`);
    next();
});

// Kanal bilgileri dosyadan okunuyor
let channelData = { channels: [] };
let workerInfo = { domain: '' };

// Kanal bilgilerini yükle
function loadChannelData() {
    try {
        if (fs.existsSync('./channels.json')) {
            channelData = JSON.parse(fs.readFileSync('./channels.json', 'utf8'));
            console.log(`Kanal bilgileri yüklendi: ${channelData.channels.length} kanal bulundu.`);
        } else {
            console.log('channels.json dosyası bulunamadı, varsayılan boş liste kullanılacak.');
        }

        if (fs.existsSync('./worker_info.json')) {
            workerInfo = JSON.parse(fs.readFileSync('./worker_info.json', 'utf8'));
            console.log(`Worker bilgisi yüklendi: ${workerInfo.domain}`);
        }
    } catch (error) {
        console.error('Kanal bilgileri yüklenirken hata oluştu:', error);
    }
}

// Başlangıçta kanal bilgilerini yükle
loadChannelData();

// Ana sayfa
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

// Player sayfası
app.get('/player', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'player.html'));
});

// Kanal listesini getir
app.get('/api/channels', (req, res) => {
    // Yeniden yükle (isteğe bağlı refresh parametresi ile)
    if (req.query.refresh === 'true') {
        loadChannelData();
    }

    res.json({
        channels: channelData.channels,
        last_updated: channelData.last_updated || new Date().toISOString()
    });
});

// Proxy isteği
app.get('/proxy/:channelId', async (req, res) => {
    const channelId = req.params.channelId;

    // Kanal ID'sine göre kanal bilgisini bul
    const channel = channelData.channels.find(c => c.id === channelId);

    if (!channel) {
        return res.status(404).json({ error: 'Kanal bulunamadı' });
    }

    try {
        // M3U8 içeriğini al
        const response = await axios.get(channel.url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': channel.referrer || 'https://www.selcuksportshd.com/'
            }
        });

        // M3U8 içeriğini döndür
        res.set('Content-Type', 'application/vnd.apple.mpegurl');
        res.send(response.data);
    } catch (error) {
        console.error(`Proxy hatası (${channelId}):`, error.message);
        res.status(500).json({ error: 'Proxy isteği sırasında hata oluştu' });
    }
});

// M3U8 oynatma listesi oluştur
app.get('/playlist.m3u8', (req, res) => {
    if (channelData.channels.length === 0) {
        return res.status(404).send('Kanal listesi boş');
    }

    // M3U8 başlık
    let playlist = '#EXTM3U\n';

    // Her kanal için girdi oluştur
    channelData.channels.forEach(channel => {
        playlist += `#EXTINF:-1 tvg-id="${channel.id}" tvg-name="${channel.name}" group-title="Spor",${channel.name}\n`;
        playlist += `${req.protocol}://${req.get('host')}/proxy/${channel.id}\n`;
    });

    res.set('Content-Type', 'application/vnd.apple.mpegurl');
    res.send(playlist);
});

// Uygulama durumu
app.get('/api/status', (req, res) => {
    res.json({
        status: 'online',
        channels_count: channelData.channels.length,
        worker_domain: workerInfo.domain,
        last_updated: channelData.last_updated || null
    });
});

// Sunucuyu başlat
app.listen(PORT, () => {
    console.log(`Sunucu http://localhost:${PORT} adresinde çalışıyor`);
});
