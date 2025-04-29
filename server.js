// server.js
// Bu dosya küçük bir proxy sunucusu oluşturur
// Kurulum: npm install express cors axios

const express = require('express');
const cors = require('cors');
const axios = require('axios');
const app = express();
const port = 3000;

// CORS kısıtlamalarını kaldır
app.use(cors());
app.use(express.urlencoded({ extended: true }));

// Loglama middleware'i ekle
app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);
    next();
});

// Kanal listesini hazırla
const channels = [
    { id: "bein_sports_1", name: "Bein Sports 1", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukbeinsports1/playlist.m3u8" },
    { id: "bein_sports_2", name: "Bein Sports 2", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukbeinsports2/playlist.m3u8" },
    { id: "bein_sports_3", name: "Bein Sports 3", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukbeinsports3/playlist.m3u8" },
    { id: "bein_sports_4", name: "Bein Sports 4", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukbeinsports4/playlist.m3u8" },
    { id: "bein_sports_5", name: "Bein Sports 5", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukbeinsports5/playlist.m3u8" },
    { id: "s_sport", name: "S Sport", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukssport/playlist.m3u8" },
    { id: "s_sport_2", name: "S Sport 2", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukssport2/playlist.m3u8" },
    { id: "smart_spor", name: "Smart Spor", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcuksmartspor/playlist.m3u8" },
    { id: "trt_spor", name: "TRT Spor", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcuktrtspor/playlist.m3u8" },
    { id: "trt_spor_2", name: "TRT Spor 2", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcuktrtspor2/playlist.m3u8" },
    { id: "a_spor", name: "A Spor", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukaspor/playlist.m3u8" },
    { id: "tivibu_spor_1", name: "Tivibu Spor 1", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcuktivibuspor1/playlist.m3u8" },
    { id: "tivibu_spor_2", name: "Tivibu Spor 2", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcuktivibuspor2/playlist.m3u8" },
    { id: "tivibu_spor_3", name: "Tivibu Spor 3", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcuktivibuspor3/playlist.m3u8" },
    { id: "eurosport_1", name: "Eurosport 1", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukeurosport1/playlist.m3u8" },
    { id: "eurosport_2", name: "Eurosport 2", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukeurosport2/playlist.m3u8" },
    { id: "nba_tv", name: "NBA TV", url: "https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcuknbatv/playlist.m3u8" }
];

// Ana sayfa
app.get('/', (req, res) => {
    res.send(`
    <html>
      <head>
        <title>Canlı Yayın Proxy</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }
          h1 { color: #333; }
          .container { max-width: 800px; margin: 0 auto; }
          pre { background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }
          .channel-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin-top: 20px; }
          .channel { background: #f0f0f0; padding: 15px; border-radius: 5px; text-align: center; }
          .channel a { display: block; color: #1a73e8; text-decoration: none; font-weight: bold; }
          .channel a:hover { text-decoration: underline; }
          .player-container { margin-top: 30px; }
          .player-instructions { margin-top: 20px; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>Canlı Yayın Proxy</h1>
          <p>Aşağıdaki kanallardan birini seçerek izleyebilirsiniz:</p>
          
          <div class="channel-list">
            ${channels.map(channel => `
              <div class="channel">
                <a href="/player?channel=${channel.id}" target="_blank">${channel.name}</a>
              </div>
            `).join('')}
          </div>
          
          <div class="player-instructions">
            <h2>VLC ile Kullanım:</h2>
            <p>VLC'yi açın ve "Medya" > "Ağ Akışını Aç" seçeneğine tıklayın, ardından aşağıdaki URL'yi girin:</p>
            <pre>http://localhost:${port}/proxy?channel=KANAL_ID</pre>
            <p>KANAL_ID yerine istediğiniz kanalın ID'sini yazın (örneğin: bein_sports_1)</p>
            
            <h2>Özel M3U8 URL'si ile kullanım:</h2>
            <form action="/player" method="get">
              <input type="text" name="custom_url" placeholder="M3U8 URL'si girin" style="width: 70%; padding: 8px;">
              <button type="submit">Oynat</button>
            </form>
            
            <h2>Hazır Playlist:</h2>
            <p>Tüm kanalları içeren playlist:</p>
            <pre><a href="/get-playlist">http://localhost:${port}/get-playlist</a></pre>
          </div>
        </div>
      </body>
    </html>
  `);
});

// Oynatıcı sayfası
app.get('/player', (req, res) => {
    const channelId = req.query.channel;
    const customUrl = req.query.custom_url;

    let streamUrl = '';
    let channelName = 'Özel Kanal';

    if (channelId) {
        const channel = channels.find(c => c.id === channelId);
        if (channel) {
            streamUrl = `/proxy?channel=${channelId}`;
            channelName = channel.name;
        }
    } else if (customUrl) {
        streamUrl = `/proxy?url=${encodeURIComponent(customUrl)}`;
    }

    if (!streamUrl) {
        return res.redirect('/');
    }

    res.send(`
    <html>
      <head>
        <title>${channelName} - Canlı Yayın</title>
        <link href="https://vjs.zencdn.net/7.20.3/video-js.css" rel="stylesheet" />
        <script src="https://vjs.zencdn.net/7.20.3/video.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
        <style>
          body { margin: 0; padding: 0; background: #000; color: #fff; font-family: Arial, sans-serif; }
          .container { width: 100%; max-width: 1280px; margin: 0 auto; padding: 20px; }
          .player-container { width: 100%; aspect-ratio: 16/9; }
          h1 { text-align: center; margin-bottom: 20px; }
          .back-link { display: block; margin-top: 20px; color: #fff; text-decoration: none; }
          .back-link:hover { text-decoration: underline; }
          video { width: 100%; height: 100%; }
        </style>
      </head>
      <body>
        <div class="container">
          <h1>${channelName}</h1>
          <div class="player-container">
            <video id="player" class="video-js vjs-default-skin vjs-big-play-centered" controls>
              <source src="${streamUrl}" type="application/x-mpegURL">
            </video>
          </div>
          <a href="/" class="back-link">← Kanal Listesine Dön</a>
          <p>Doğrudan M3U8 bağlantısı: <a href="${streamUrl}" style="color: #fff;" target="_blank">${streamUrl}</a></p>
        </div>
        
        <script>
          var player = videojs('player');
          player.play();
        </script>
      </body>
    </html>
  `);
});

// Proxy istekleri
app.get('/proxy', async (req, res) => {
    try {
        let targetUrl;

        // Kanal ID'sine göre URL bul
        if (req.query.channel) {
            const channel = channels.find(c => c.id === req.query.channel);
            if (channel) {
                targetUrl = channel.url;
            } else {
                return res.status(404).send('Kanal bulunamadı');
            }
        } else {
            // Kullanıcı kendi m3u8 URL'sini belirtebilir
            targetUrl = req.query.url || 'https://alpha.cf-worker-5867c61e49ce10.workers.dev/live/selcukbeinsports1/playlist.m3u8';
        }

        console.log(`Kullanılacak M3U8 URL'si: ${targetUrl}`);

        // Header'ları ayarla
        const headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'Referer': 'https://main.uxsyplayer1a09531928c5.click/',
            'Origin': 'https://main.uxsyplayer1a09531928c5.click'
        };

        console.log(`Proxy isteği gönderiliyor: ${targetUrl}`);

        // İsteği yap
        const response = await axios.get(targetUrl, {
            headers: headers,
            responseType: 'text' // Stream yerine direkt metin alalım
        });

        // Content-Type header'ını ayarla
        res.set('Content-Type', 'application/vnd.apple.mpegurl');

        // İçerik Dönüştürme: m3u8 içindeki URL'leri düzelt
        let content = response.data;

        // M3U8 içeriğini satır satır analiz et
        const lines = content.split('\n');
        const processedLines = lines.map(line => {
            // Satır bir yorum (#) ile başlamıyorsa ve bir URL ise
            if (!line.startsWith('#') && line.trim().length > 0) {
                if (line.startsWith('https://')) {
                    console.log(`URL bulundu: ${line}`);
                    return `/proxy-segment?url=${encodeURIComponent(line)}`;
                }
            }
            return line;
        });

        const modifiedContent = processedLines.join('\n');
        console.log("Düzeltilmiş içerik:", modifiedContent);

        // Düzeltilmiş içeriği gönder
        res.send(modifiedContent);

    } catch (error) {
        console.error(`Proxy hatası: ${error.message}`);
        if (error.response) {
            console.error(`Sunucu yanıtı: ${error.response.status} ${error.response.statusText}`);
            console.error(`Yanıt içeriği:`, error.response.data);
        }
        res.status(500).send(`Proxy hatası: ${error.message}`);
    }
});

// Segment proxy endpoint'i
app.get('/proxy-segment', async (req, res) => {
    try {
        const url = req.query.url;
        if (!url) {
            return res.status(400).send('URL parametresi gerekli');
        }

        console.log(`Segment isteği: ${url}`);

        // Header'ları ayarla
        const headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
            'Referer': 'https://main.uxsyplayer1a09531928c5.click/',
            'Origin': 'https://main.uxsyplayer1a09531928c5.click',
            'Accept': '*/*',
            'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive'
        };

        // İsteği yap
        try {
            console.log(`Segment alınıyor: ${url}`);

            const response = await axios.get(url, {
                headers: headers,
                responseType: 'arraybuffer', // binary data için
                timeout: 10000, // 10 saniye timeout
                maxContentLength: 50 * 1024 * 1024 // 50MB max içerik
            });

            // Content-Type header'ını ayarla
            const contentType = response.headers['content-type'];
            if (contentType) {
                res.set('Content-Type', contentType);
            } else {
                // İçeriğe göre content-type belirle
                if (url.endsWith('.ts')) {
                    res.set('Content-Type', 'video/mp2t');
                } else if (url.endsWith('.m3u8')) {
                    res.set('Content-Type', 'application/vnd.apple.mpegurl');
                } else if (url.endsWith('.key')) {
                    res.set('Content-Type', 'application/octet-stream');
                } else {
                    // Çoğu video segment'i için varsayılan
                    res.set('Content-Type', 'video/mp2t');
                }
            }

            // Cevaba diğer başlıkları da ekle
            // CORS başlıkları ve caching için
            res.set('Access-Control-Allow-Origin', '*');
            res.set('Access-Control-Allow-Methods', 'GET');
            res.set('Access-Control-Allow-Headers', 'Origin, Content-Type, Accept');

            // Cache kontrolü
            res.set('Cache-Control', 'public, max-age=300'); // 5 dakika cache

            // Başarılı cevabı logla
            console.log(`Segment başarıyla alındı: ${url}, Boyut: ${response.data.length} bytes`);

            // İçeriği doğrudan gönder
            res.send(response.data);

        } catch (error) {
            console.error(`Segment hatası (${url}): ${error.message}`);
            if (error.response) {
                console.error(`Durum kodu: ${error.response.status}`);
                console.error(`Sunucu yanıtı:`, error.response.headers);
            }

            // Hata durumunda 502 Bad Gateway ile cevap ver
            res.status(502).send(`Segment alınamadı: ${error.message}`);
        }

    } catch (error) {
        console.error(`Genel hata: ${error.message}`);
        res.status(500).send(`Genel hata: ${error.message}`);
    }
});

// M3U8 dosyası oluştur - YENİ İSİM
app.get('/get-playlist', (req, res) => {
    console.log('Playlist isteği alındı');

    res.set('Content-Type', 'application/vnd.apple.mpegurl');

    // Sunucu adresini belirle
    const host = req.get('host') || `localhost:${port}`;
    const protocol = req.protocol || 'http';
    const baseUrl = `${protocol}://${host}`;

    console.log(`Playlist için kullanılacak baseUrl: ${baseUrl}`);

    let playlist = '#EXTM3U\n';

    channels.forEach(channel => {
        playlist += `#EXTINF:-1 tvg-id="${channel.id}" tvg-name="${channel.name}",${channel.name}\n`;
        playlist += `#EXTVLCOPT:http-referrer=https://main.uxsyplayer1a09531928c5.click/\n`;
        playlist += `${baseUrl}/proxy?channel=${channel.id}\n`;
    });

    console.log('Playlist oluşturuldu, gönderiliyor...');
    res.send(playlist);
});

// Test endpoint
app.get('/test', (req, res) => {
    res.send('Sunucu test başarılı, çalışıyor!');
});

// 404 handler - tüm rotalardan sonra tanımla
app.use((req, res) => {
    console.log(`404 Hatası: ${req.method} ${req.url}`);
    res.status(404).send(`
        <html>
            <head>
                <title>Sayfa bulunamadı</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    h1 { color: #f44336; }
                    a { color: #2196F3; text-decoration: none; }
                    a:hover { text-decoration: underline; }
                </style>
            </head>
            <body>
                <h1>404 - Sayfa Bulunamadı</h1>
                <p>İstediğiniz sayfa bulunamadı.</p>
                <p>URL: ${req.url}</p>
                <p><a href="/">Ana sayfaya dönün</a></p>
            </body>
        </html>
    `);
});

// Sunucuyu başlat
app.listen(port, () => {
    console.log(`Proxy sunucusu çalışıyor: http://localhost:${port}`);
    console.log(`Hazır M3U8 playlist: http://localhost:${port}/get-playlist`);
});
