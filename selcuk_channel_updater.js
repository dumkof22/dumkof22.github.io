// selcuk_channel_updater.js
// Bu script, selcuk_channel_finder.py tarafından oluşturulan JSON dosyasından 
// kanal bilgilerini alarak server.js için kullanılabilecek bir channels.json dosyası oluşturur

const fs = require('fs');
const path = require('path');

// Bugünün tarihini YYYY-MM-DD formatında al
function getTodayDate() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// En son oluşturulan JSON dosyasını bul
function findLatestJsonFile() {
    // Önce bugünün tarihiyle dosya var mı kontrol et
    const today = getTodayDate();
    const todayFileName = `selcuksports_kanallar_${today}.json`;

    if (fs.existsSync(todayFileName)) {
        console.log(`Bugünün JSON dosyası bulundu: ${todayFileName}`);
        return todayFileName;
    }

    // Bugünün dosyası yoksa, tüm JSON dosyalarını kontrol et ve en yeni olanı bul
    const files = fs.readdirSync('.');
    const jsonFiles = files.filter(file =>
        file.startsWith('selcuksports_kanallar_') && file.endsWith('.json')
    );

    if (jsonFiles.length === 0) {
        console.error('Hiç JSON dosyası bulunamadı. Önce selcuk_channel_finder.py çalıştırın.');
        return null;
    }

    // Dosyaları tarih sırasına göre sırala (en yeni en önce)
    jsonFiles.sort((a, b) => {
        // Dosya adından tarihi çıkar (selcuksports_kanallar_YYYY-MM-DD.json)
        const dateA = a.replace('selcuksports_kanallar_', '').replace('.json', '');
        const dateB = b.replace('selcuksports_kanallar_', '').replace('.json', '');
        return dateB.localeCompare(dateA); // Yeniden eskiye sırala
    });

    console.log(`En son JSON dosyası kullanılacak: ${jsonFiles[0]}`);
    return jsonFiles[0];
}

// Ana fonksiyon
function updateChannels() {
    try {
        // En son JSON dosyasını bul
        const jsonFile = findLatestJsonFile();
        if (!jsonFile) return;

        // JSON dosyasını oku ve parse et
        const jsonData = JSON.parse(fs.readFileSync(jsonFile, 'utf8'));

        // Kanal bilgilerini çıkar
        const channelMap = new Map(); // Tekrar eden kanalları önlemek için Map kullan

        jsonData.forEach(channel => {
            // Sadece gerçek stream URL'leri olan kanalları işle
            if (channel.real_stream_urls && channel.real_stream_urls.length > 0) {
                // Her gerçek URL için kanal oluştur
                channel.real_stream_urls.forEach(url => {
                    // URL'den kanal ID'sini çıkar
                    // Örnek: https://alpha.cf-worker-2fa2f308d0ef6e.workers.dev/live/selcukbeinsports1/playlist.m3u8

                    // URL'den kanal ID'sini çıkar (selcuk... kısmı)
                    const match = url.match(/\/live\/([^\/]+)\/playlist/);
                    if (match && match[1]) {
                        const channelId = match[1];

                        // Kanal adını formatla
                        let channelName = channelId.replace('selcuk', ''); // "selcuk" önekini kaldır

                        // İlk harfi büyük yap, diğerlerini ayır ve büyük başlat
                        channelName = channelName
                            .replace(/([A-Z])/g, ' $1') // Büyük harflerden önce boşluk ekle
                            .replace(/^./, str => str.toUpperCase()); // İlk harfi büyük yap

                        // Belirli özel durumları düzelt
                        channelName = channelName
                            .replace('Bein', 'beIN')
                            .replace('Tivibu', 'Tivibu')
                            .replace('Trt', 'TRT')
                            .replace('Nba', 'NBA')
                            .replace('Tivibuspor', 'Tivibu Spor')
                            .replace('Ssport', 'S Sport');

                        // ID'yi JavaScript için uygun formata dönüştür
                        const jsId = channelId.replace('selcuk', '')
                            .toLowerCase()
                            .replace(/([a-z])([A-Z])/g, '$1_$2'); // camelCase'den snake_case'e çevir

                        // Referrer olarak orijinal URL'yi kullan
                        const referrer = channel.page_url;

                        // Eğer aynı ID ile kanal zaten eklenmişse eklemez
                        if (!channelMap.has(jsId)) {
                            channelMap.set(jsId, {
                                id: jsId,
                                name: channelName.trim(),
                                url: url,
                                referrer: referrer
                            });
                        }
                    }
                });
            }
        });

        // Map'i Array'e dönüştür
        const channels = Array.from(channelMap.values());

        // JSON olarak dışa aktar
        if (channels.length > 0) {
            // Kanallara şu anki timestamp'i ekle
            const exportData = {
                channels: channels,
                last_updated: new Date().toISOString(),
                worker_domain: channels[0].url.split('/live/')[0]  // İlk kanaldan worker domain'i çıkar
            };

            // Dosyaya kaydet
            fs.writeFileSync('channels.json', JSON.stringify(exportData, null, 2));
            console.log(`Toplam ${channels.length} kanal channels.json dosyasına kaydedildi.`);

            // worker domain'i de ayrı dosyaya kaydet (server.js için kolay erişim)
            const workerInfo = {
                domain: exportData.worker_domain,
                updated_at: exportData.last_updated
            };
            fs.writeFileSync('worker_info.json', JSON.stringify(workerInfo, null, 2));
            console.log(`Worker bilgisi worker_info.json dosyasına kaydedildi: ${workerInfo.domain}`);

            return exportData;
        } else {
            console.error('Hiç çalışan kanal bulunamadı!');
            return null;
        }
    } catch (error) {
        console.error(`Hata oluştu: ${error.message}`);
        return null;
    }
}

// Script direkt çalıştırıldıysa güncelleme işlemini başlat
if (require.main === module) {
    console.log('Kanal bilgileri güncelleniyor...');
    const result = updateChannels();

    if (result) {
        console.log('İşlem başarıyla tamamlandı!');
        console.log(`Worker domain: ${result.worker_domain}`);
        console.log(`Kanal sayısı: ${result.channels.length}`);
    } else {
        console.log('İşlem başarısız oldu!');
    }
}

module.exports = { updateChannels }; 
