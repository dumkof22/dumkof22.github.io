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
            const rawData = fs.readFileSync('./channels.json', 'utf8');
            try {
                channelData = JSON.parse(rawData);
                console.log(`Kanal bilgileri yüklendi: ${channelData.channels.length} kanal bulundu.`);

                // Channels.json doğru yüklendi mi kontrol et
                if (channelData.channels && Array.isArray(channelData.channels)) {
                    // Tüm kanalları konsola yazdır
                    console.log("Kanal ID'leri:");
                    channelData.channels.forEach(channel => {
                        console.log(`- ${channel.id}: ${channel.name}`);
                    });
                } else {
                    console.error('Kanal verisi yanlış formatta. "channels" dizisi bulunamadı veya dizi değil.');
                }
            } catch (parseError) {
                console.error('Kanal JSON verisi ayrıştırılamadı:', parseError);
                channelData = { channels: [] };
            }
        } else {
            console.log('channels.json dosyası bulunamadı, varsayılan boş liste kullanılacak.');
            channelData = { channels: [] };
        }

        if (fs.existsSync('./worker_info.json')) {
            workerInfo = JSON.parse(fs.readFileSync('./worker_info.json', 'utf8'));
            console.log(`Worker bilgisi yüklendi: ${workerInfo.domain}`);
        }
    } catch (error) {
        console.error('Kanal bilgileri yüklenirken hata oluştu:', error);
        channelData = { channels: [] };
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

// M3U8 içeriğindeki segment URL'lerini düzenle
function rewriteM3U8Content(m3u8Content, baseUrl, channelId, originalUrl) {
    // İçerikte URL olmayan satırları koru
    let lines = m3u8Content.split('\n');
    let rewrittenLines = [];

    const urlPattern = /^(https?:\/\/|\/)/;

    for (let line of lines) {
        // Satır URL içeriyorsa ve yorum değilse
        if (line.trim() && !line.startsWith('#') && urlPattern.test(line)) {
            let fullUrl;

            if (line.startsWith('/')) {
                // Göreceli URL'yi mutlak URL'ye çevir
                const parsedUrl = new URL(originalUrl);
                fullUrl = `${parsedUrl.protocol}//${parsedUrl.host}${line}`;
            } else if (!line.startsWith('http')) {
                // URL protokolsüzse, protokol ekle
                fullUrl = baseUrl + line;
            } else {
                // Mutlak URL
                fullUrl = line;
            }

            // Segment dosyasını proxy üzerinden sunmak için URL'yi değiştir
            rewrittenLines.push(`/segment/${channelId}?url=${encodeURIComponent(fullUrl)}`);
        } else {
            rewrittenLines.push(line);
        }
    }

    return rewrittenLines.join('\n');
}

// Doğrudan indirme için M3U8 içeriğini düzenle (tüm URL'ler mutlak olmalı)
function rewriteM3U8ContentForDownload(m3u8Content, baseUrl, channelId, originalUrl, hostUrl) {
    // İçerikte URL olmayan satırları koru
    let lines = m3u8Content.split('\n');
    let rewrittenLines = [];

    const urlPattern = /^(https?:\/\/|\/)/;

    for (let line of lines) {
        // Satır URL içeriyorsa ve yorum değilse
        if (line.trim() && !line.startsWith('#') && urlPattern.test(line)) {
            let fullUrl;

            if (line.startsWith('/')) {
                // Göreceli URL'yi mutlak URL'ye çevir
                const parsedUrl = new URL(originalUrl);
                fullUrl = `${parsedUrl.protocol}//${parsedUrl.host}${line}`;
            } else if (!line.startsWith('http')) {
                // URL protokolsüzse, protokol ekle
                fullUrl = baseUrl + line;
            } else {
                // Mutlak URL
                fullUrl = line;
            }

            // Segment dosyası için tam URL oluştur
            const segmentUrl = `${hostUrl}/segment/${channelId}?url=${encodeURIComponent(fullUrl)}`;
            rewrittenLines.push(segmentUrl);
        } else {
            rewrittenLines.push(line);
        }
    }

    return rewrittenLines.join('\n');
}

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
                'Referer': 'https://main.uxsyplayer1a09531928c5.click'
            }
        });

        // Base URL'yi belirle
        const urlObj = new URL(channel.url);
        const baseUrl = `${urlObj.protocol}//${urlObj.host}`;

        // M3U8 içeriğini düzenle
        const rewrittenContent = rewriteM3U8Content(response.data, baseUrl, channelId, channel.url);

        // M3U8 içeriğini döndür
        res.set('Content-Type', 'application/vnd.apple.mpegurl');
        res.send(rewrittenContent);
    } catch (error) {
        console.error(`Proxy hatası (${channelId}):`, error.message);
        res.status(500).json({ error: 'Proxy isteği sırasında hata oluştu' });
    }
});

// Video segmentleri için proxy
app.get('/segment/:channelId', async (req, res) => {
    const channelId = req.params.channelId;
    const segmentUrl = req.query.url;

    if (!segmentUrl) {
        return res.status(400).json({ error: 'Segment URL belirtilmedi' });
    }

    // Kanal ID'sine göre kanal bilgisini bul
    const channel = channelData.channels.find(c => c.id === channelId);

    if (!channel) {
        return res.status(404).json({ error: 'Kanal bulunamadı' });
    }

    try {
        // Segment dosyasını indir
        const response = await axios.get(segmentUrl, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://main.uxsyplayer1a09531928c5.click'
            },
            responseType: 'arraybuffer'
        });

        // İçerik tipini belirle
        const contentType = response.headers['content-type'];
        if (contentType) {
            res.set('Content-Type', contentType);
        }

        // Dosyayı gönder
        res.send(response.data);
    } catch (error) {
        console.error(`Segment proxy hatası (${channelId}):`, error.message);
        res.status(500).json({ error: 'Segment indirme hatası' });
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

// Doğrudan m3u8 yönlendirmesi (VLC gibi oynatıcılar için)
app.get('/direct/:channelId', async (req, res) => {
    const channelId = req.params.channelId;

    // Kanal ID'sine göre kanal bilgisini bul
    const channel = channelData.channels.find(c => c.id === channelId);

    if (!channel) {
        return res.status(404).json({ error: 'Kanal bulunamadı' });
    }

    try {
        // Host URL
        const hostUrl = `${req.protocol}://${req.get('host')}`;

        // M3U8 içeriğini al
        const response = await axios.get(channel.url, {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': 'https://main.uxsyplayer1a09531928c5.click'
            }
        });

        // Base URL'yi belirle
        const urlObj = new URL(channel.url);
        const baseUrl = `${urlObj.protocol}//${urlObj.host}`;

        // M3U8 içeriğini indirme için düzenle (mutlak URL'ler)
        const rewrittenContent = rewriteM3U8ContentForDownload(response.data, baseUrl, channelId, channel.url, hostUrl);

        // İndirme için başlıkları ayarla
        res.setHeader('Content-Type', 'application/vnd.apple.mpegurl');
        res.setHeader('Content-Disposition', `attachment; filename="${channelId}.m3u8"`);

        // İçeriği gönder
        res.send(rewrittenContent);
    } catch (error) {
        console.error(`Doğrudan yönlendirme hatası (${channelId}):`, error.message);
        res.status(500).json({ error: 'Stream URL alınırken hata oluştu' });
    }
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
