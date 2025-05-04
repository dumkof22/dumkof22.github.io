import requests
from bs4 import BeautifulSoup
import time
import csv
import json
import re
from datetime import datetime
import os
import sys

def check_url(url, timeout=5, headers=None):
    """URL'yi kontrol eder ve başarılı olursa içeriğini döndürür."""
    try:
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Özel başlıklar sağlanmışsa, varsayılan başlıkları güncelle
        if headers:
            default_headers.update(headers)
            
        response = requests.get(url, headers=default_headers, timeout=timeout)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Hata: {str(e)}")
        return None

def extract_channel_links(html_content, base_url):
    """Ana sayfadan kanal linklerini çıkarır."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        channel_links = []
        
        # Menüdeki tüm linkleri bul
        menu_links = soup.find_all('a', href=True)
        for link in menu_links:
            href = link.get('href')
            
            # mailto: ve javascript: linkleri hariç tut
            if href and (href.startswith('mailto:') or href.startswith('javascript:') or href == '#'):
                continue
                
            # # işaretinden sonraki kısmı temizle
            if href and '#' in href:
                href = href.split('#')[0]
                
            # Tam URL'leri ekle
            if href and href.startswith(('http://', 'https://')):
                if base_url.split('//')[1].split('.')[0] in href:  # Sadece aynı domaine ait linkleri al
                    channel_links.append(href)
            # Site içi linkleri ekle
            elif href and href.startswith('/'):
                full_url = base_url + href
                channel_links.append(full_url)
            elif href:
                full_url = base_url + '/' + href.lstrip('/')
                channel_links.append(full_url)
        
        # Ayrıca div, li gibi elementlere bak, içlerinde "kanal" veya "canlı" gibi anahtar kelimeler olabilir
        potential_channel_elements = soup.find_all(['div', 'li', 'span', 'button'], 
                                                 class_=lambda c: c and isinstance(c, str) and ('kanal' in c.lower() or 'canli' in c.lower() or 'live' in c.lower() or 'channel' in c.lower()))
        
        for element in potential_channel_elements:
            # İçindeki linkleri kontrol et
            inner_links = element.find_all('a', href=True)
            for link in inner_links:
                href = link.get('href')
                if href and not href.startswith(('mailto:', 'javascript:', '#')):
                    # # işaretinden sonraki kısmı temizle
                    if '#' in href:
                        href = href.split('#')[0]
                        
                    if href.startswith(('http://', 'https://')):
                        if base_url.split('//')[1].split('.')[0] in href:
                            channel_links.append(href)
                    elif href.startswith('/'):
                        full_url = base_url + href
                        channel_links.append(full_url)
                    else:
                        full_url = base_url + '/' + href.lstrip('/')
                        channel_links.append(full_url)
        
        # Tekrarlanan linkleri kaldır
        return list(set(channel_links))
    except Exception as e:
        print(f"Kanal linkleri çıkarma hatası: {str(e)}")
        return []

def extract_channel_info(html_content, url):
    """HTML içeriğinden kanal adı ve link bilgisini çıkarır."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Kanal adını bulmaya çalış
        title_element = soup.find('title')
        channel_name = title_element.text.strip() if title_element else "Bilinmeyen Kanal"
        
        # Video kaynağını bulmaya çalış
        video_sources = []
        
        # 1. Video elementlerini kontrol et
        video_elements = soup.find_all('video')
        for video in video_elements:
            source_elements = video.find_all('source')
            for source in source_elements:
                if source.get('src'):
                    video_sources.append(source.get('src'))
            
            # Video elementinin kendisinde de src olabilir
            if video.get('src'):
                video_sources.append(video.get('src'))
        
        # 2. iframe elementlerini kontrol et
        iframe_elements = soup.find_all('iframe')
        for iframe in iframe_elements:
            if iframe.get('src'):
                iframe_src = iframe.get('src')
                video_sources.append(iframe_src)
        
        # 3. embed elementlerini kontrol et
        embed_elements = soup.find_all('embed')
        for embed in embed_elements:
            if embed.get('src'):
                embed_src = embed.get('src')
                video_sources.append(embed_src)
        
        # 4. object elementlerini kontrol et
        object_elements = soup.find_all('object')
        for obj in object_elements:
            if obj.get('data'):
                object_data = obj.get('data')
                video_sources.append(object_data)
        
        # 5. Script içindeki video URL'lerini ara
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # m3u8 uzantılı linkleri ara (HLS stream)
                m3u8_links = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', script.string)
                video_sources.extend(m3u8_links)
                
                # mp4 uzantılı linkleri ara
                mp4_links = re.findall(r'https?://[^\s\'"]+\.mp4[^\s\'"]*', script.string)
                video_sources.extend(mp4_links)
                
                # RTMP stream linkleri ara
                rtmp_links = re.findall(r'rtmp://[^\s\'"]+', script.string)
                video_sources.extend(rtmp_links)
                
                # source veya file parametrelerini ara
                source_links = re.findall(r'source\s*:\s*[\'"]([^\'"]+)[\'"]', script.string)
                video_sources.extend(source_links)
                
                file_links = re.findall(r'file\s*:\s*[\'"]([^\'"]+)[\'"]', script.string)
                video_sources.extend(file_links)
        
        # 6. Div elementlerinde data-src, data-url gibi özellikleri ara
        for tag in soup.find_all():
            for attr_name, attr_value in tag.attrs.items():
                # data- ile başlayan attribute'lar
                if attr_name.startswith('data-') and ('src' in attr_name or 'url' in attr_name):
                    if isinstance(attr_value, str) and ('http' in attr_value or '//' in attr_value):
                        video_sources.append(attr_value)
        
        # 7. Link elementlerini kontrol et - özellikle m3u8 ve benzeri formatlara sahip olanlar
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and any(ext in href for ext in ['.m3u8', '.mp4', '.ts', '.mpd', '.flv']):
                video_sources.append(href)
        
        # Benzersiz URL'leri al ve http veya // ile başlayanları filtrele
        filtered_sources = []
        for source in video_sources:
            if source.startswith('http') or source.startswith('//'):
                filtered_sources.append(source)
            elif source.startswith('/'):
                # Göreceli URL'leri mutlak URL'lere dönüştür
                base_domain = '/'.join(url.split('/')[:3])  # http(s)://domain.com
                filtered_sources.append(f"{base_domain}{source}")
        
        return {
            "channel_name": channel_name,
            "video_sources": list(set(filtered_sources)),  # Tekrarlanan URL'leri kaldır
            "page_url": url
        }
    except Exception as e:
        print(f"HTML ayrıştırma hatası: {str(e)}")
        return {"channel_name": "Hata Oluştu", "video_sources": [], "page_url": url}

def save_to_csv(channels):
    """Bulunan kanalları CSV dosyasına kaydeder."""
    now = datetime.now()
    filename = f"selcuksports_kanallar_{now.strftime('%Y-%m-%d')}.csv"
    
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Kanal Adı", "Video URL", "Gerçek Stream URL", "Sayfa URL"])
        
        for channel in channels:
            # Normal video kaynakları için satırlar
            for url in channel["video_sources"]:
                # Bu URL için gerçek stream URL'si var mı kontrol et
                real_url = ""
                if "real_stream_urls" in channel and channel["real_stream_urls"]:
                    # Aynı URL'nin birden fazla gerçek stream URL'si olabilir, bu yüzden boş bırakalım
                    real_url = ""
                
                writer.writerow([channel["channel_name"], url, real_url, channel["page_url"]])
            
            # Gerçek stream URL'leri için ek satırlar
            if "real_stream_urls" in channel and channel["real_stream_urls"]:
                for real_url in channel["real_stream_urls"]:
                    writer.writerow([channel["channel_name"], "", real_url, channel["page_url"]])
    
    print(f"Sonuçlar {filename} dosyasına kaydedildi.")
    return filename

def save_to_json(channels):
    """Bulunan kanalları JSON dosyasına kaydeder."""
    now = datetime.now()
    filename = f"selcuksports_kanallar_{now.strftime('%Y-%m-%d')}.json"
    
    # JSON serileştirmesi için kopyalama
    channels_copy = []
    for channel in channels:
        channel_copy = channel.copy()
        # Eğer real_stream_urls yoksa boş liste ekle
        if "real_stream_urls" not in channel_copy:
            channel_copy["real_stream_urls"] = []
        channels_copy.append(channel_copy)
    
    with open(filename, 'w', encoding='utf-8') as file:
        json.dump(channels_copy, file, ensure_ascii=False, indent=4)
    
    print(f"Sonuçlar {filename} dosyasına kaydedildi.")
    return filename

def extract_real_stream_url(url):
    """URL'den gerçek stream URL'sini çıkarmaya çalışır."""
    try:
        print(f"URL inceleniyor: {url[:60]}..." if len(url) > 60 else f"URL inceleniyor: {url}")
        
        # # işaretinden sonraki kısmı temizle
        if '#' in url:
            url = url.split('#')[0]
            
        # Eğer URL zaten bir video stream formatı ise doğrudan döndür
        if url.endswith('.m3u8') or url.endswith('.mp4') or '.m3u8?' in url:
            print(f" ✓ URL zaten stream formatında: {url[:60]}...")
            return url
        
        # Index.php linklerini özel olarak işle (Selçuk player linkleri)
        if 'main.uxsyplayer' in url.lower() and 'index.php' in url.lower():
            print(f" ⟳ Selçuk player sayfası işleniyor: {url}")
            
            # Player ID'sini çıkar
            player_id = None
            match = re.search(r'id=([^&#]+)', url)
            if match:
                player_id = match.group(1)
                print(f" ✓ Player ID: {player_id}")
            else:
                print(f" ✗ Player ID bulunamadı")
                return None
            
            # Referrer başlığı olarak orijinal URL'yi kullan
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Referer': url,
                'Origin': 'https://main.uxsyplayer1a09531928c5.click',
                'Accept': '*/*',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Dest': 'empty',
                'Accept-Language': 'tr,en-US;q=0.9,en;q=0.8'
            }
            
            # Gerçek stream URL'sini oluşturmak için worker-id parametresini bulmaya çalış
            try:
                # İlk olarak index.php sayfasını getir
                print(f" ⟳ Player sayfası indiriliyor...")
                index_content = check_url(url, timeout=5)
                if not index_content:
                    print(f" ✗ Player sayfası indirilemedi")
                    return None
                
                print(f" ✓ Player sayfası indirildi, worker-id aranıyor...")
                
                # İlk olarak doğrudan bir worker-id aramaya çalış
                worker_id_match = re.search(r'(alpha\.cf-worker-[a-zA-Z0-9]+\.workers\.dev)', index_content)
                if worker_id_match:
                    worker_domain = worker_id_match.group(1)
                    stream_url = f"https://{worker_domain}/live/{player_id}/playlist.m3u8"
                    print(f" ✓ Worker domain bulundu: {worker_domain}")
                    print(f" ✓ Gerçek stream URL oluşturuldu: {stream_url}")
                    
                    # Stream URL'nin çalışıp çalışmadığını kontrol et
                    try:
                        response = requests.head(stream_url, headers=headers, timeout=5)
                        if response.status_code == 200:
                            print(f" ✓ Stream URL doğrulandı ve çalışıyor")
                            return stream_url
                        else:
                            print(f" ⚠ Stream URL çalışmıyor olabilir - HTTP {response.status_code}")
                            # Yine de URL'yi döndür, belki çalışır
                            return stream_url
                    except Exception as e:
                        print(f" ⚠ Stream URL kontrolü sırasında hata: {str(e)}")
                        # Yine de URL'yi döndür, belki çalışır
                        return stream_url
                
                # Alternatif olarak, iframe URL'yi bulmaya çalış
                iframe_match = re.search(r'<iframe[^>]*src=[\'"](https?://[^\'"]*/player/[^\'"]*)[\'"]', index_content)
                if iframe_match:
                    iframe_url = iframe_match.group(1)
                    print(f" ✓ iframe URL bulundu: {iframe_url}")
                    
                    # iframe içeriğini al
                    iframe_content = check_url(iframe_url, timeout=5)
                    if iframe_content:
                        # iframe içinde worker domain'i ara
                        worker_id_match = re.search(r'(alpha\.cf-worker-[a-zA-Z0-9]+\.workers\.dev)', iframe_content)
                        if worker_id_match:
                            worker_domain = worker_id_match.group(1)
                            stream_url = f"https://{worker_domain}/live/{player_id}/playlist.m3u8"
                            print(f" ✓ iframe içinde worker domain bulundu: {worker_domain}")
                            print(f" ✓ Gerçek stream URL oluşturuldu: {stream_url}")
                            return stream_url
                
                # Son çare olarak, link türetmeyi dene (en büyük tahmin)
                # En sık kullanılan worker ID'leri bir liste olarak tut (son X kalan ID)
                common_worker_ids = [
                    "2fa2f308d0ef6e",
                    "fce5a308d0ef6e",
                    "3bdfa308d0ef6e", 
                    "aa82c308d0ef6e",
                    "9a6b9408d0ef6e"
                ]
                
                print(f" ⚠ Worker ID bulunamadı, yaygın worker ID'leri deneniyor...")
                working_url = None
                
                for worker_id in common_worker_ids:
                    test_url = f"https://alpha.cf-worker-{worker_id}.workers.dev/live/{player_id}/playlist.m3u8"
                    try:
                        print(f" ⟳ Deneniyor: {test_url}")
                        response = requests.head(test_url, headers=headers, timeout=3)
                        if response.status_code == 200:
                            print(f" ✓ Çalışan worker ID bulundu: {worker_id}")
                            working_url = test_url
                            break
                    except Exception as e:
                        print(f" ✗ Test başarısız: {str(e)}")
                
                if working_url:
                    print(f" ✓ Gerçek stream URL bulundu: {working_url}")
                    return working_url
                
                print(f" ✗ Gerçek stream URL bulunamadı")
                return None
                
            except Exception as e:
                print(f" ✗ Stream URL oluşturma hatası: {str(e)}")
                return None
        
        # Eğer URL bir player sayfasına işaret ediyorsa, içeriğini kontrol et
        if 'player' in url.lower() or 'index.php' in url.lower():
            print(f" ⟳ Player sayfası indiriliyor...")
            content = check_url(url, timeout=5)  # Daha uzun timeout süresi
            if not content:
                print(f" ✗ Player sayfası açılamadı")
                return None
            
            print(f" ✓ Player sayfası indirildi, stream URL'si aranıyor...")
                
            # m3u8 uzantılı stream linkleri ara
            m3u8_links = re.findall(r'https?://[^\s\'"]+\.m3u8[^\s\'"]*', content)
            if m3u8_links:
                # # işaretinden sonraki kısmı temizle
                clean_link = m3u8_links[0].split('#')[0] if '#' in m3u8_links[0] else m3u8_links[0]
                print(f" ✓ m3u8 stream URL'si bulundu: {clean_link[:60]}...")
                return clean_link  # İlk m3u8 linkini döndür
            
            # Farklı stream formatları için kontrol
            stream_links = re.findall(r'source\s*:\s*[\'"]([^\'"]+)[\'"]', content)
            if stream_links:
                for link in stream_links:
                    if '.m3u8' in link or '.mp4' in link:
                        # # işaretinden sonraki kısmı temizle
                        link = link.split('#')[0] if '#' in link else link
                        
                        # Göreceli URL'leri mutlak URL'lere dönüştür
                        if not link.startswith(('http://', 'https://')):
                            base_domain = '/'.join(url.split('/')[:3])  # http(s)://domain.com
                            link = f"{base_domain}{link if link.startswith('/') else '/' + link}"
                        
                        print(f" ✓ source parametresinden stream URL'si bulundu: {link[:60]}...")
                        return link
            
            # file parametresi ara
            file_links = re.findall(r'file\s*:\s*[\'"]([^\'"]+)[\'"]', content)
            if file_links:
                for link in file_links:
                    if '.m3u8' in link or '.mp4' in link or 'stream' in link.lower():
                        # # işaretinden sonraki kısmı temizle
                        link = link.split('#')[0] if '#' in link else link
                        
                        # Göreceli URL'leri mutlak URL'lere dönüştür
                        if not link.startswith(('http://', 'https://')):
                            base_domain = '/'.join(url.split('/')[:3])  # http(s)://domain.com
                            link = f"{base_domain}{link if link.startswith('/') else '/' + link}"
                        
                        print(f" ✓ file parametresinden stream URL'si bulundu: {link[:60]}...")
                        return link
            
            print(f" ✗ Stream URL'si bulunamadı")
        else:
            print(f" ✗ URL player sayfası formatında değil")
            
        return None
    except Exception as e:
        print(f" ✗ Stream URL çıkarma hatası: {str(e)}")
        return None

def generate_html_report(channels, csv_file, json_file):
    """Bulunan kanalları HTML sayfasında gösterir."""
    now = datetime.now()
    filename = f"selcuksports_kanallar_{now.strftime('%Y-%m-%d')}.html"
    
    html_content = f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Selçuk Sports Kanal Listesi</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
        }}
        .stats {{
            background-color: #e9f7ef;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .channel-card {{
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: white;
        }}
        .channel-name {{
            font-size: 18px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 10px;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }}
        .source-link {{
            margin: 5px 0;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
        }}
        .source-link a {{
            color: #3498db;
            text-decoration: none;
            word-break: break-all;
            margin-left: 10px;
            flex: 1;
        }}
        .source-link .url-preview {{
            font-family: monospace;
            background-color: #f8f9fa;
            padding: 5px;
            border-radius: 3px;
            border: 1px solid #ddd;
            margin-top: 5px;
            max-width: 100%;
            overflow-x: auto;
            font-size: 12px;
        }}
        .source-link a:hover {{
            text-decoration: underline;
        }}
        .footer {{
            margin-top: 30px;
            text-align: center;
            color: #7f8c8d;
            font-size: 14px;
        }}
        .download-links {{
            text-align: center;
            margin: 20px 0;
        }}
        .download-links a {{
            display: inline-block;
            margin: 0 10px;
            padding: 8px 15px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }}
        .download-links a:hover {{
            background-color: #2980b9;
        }}
        .video-container {{
            margin-top: 10px;
        }}
        .play-button {{
            display: inline-block;
            padding: 5px 10px;
            background-color: #27ae60;
            color: white;
            text-decoration: none;
            border-radius: 3px;
            font-size: 14px;
        }}
        .play-button:hover {{
            background-color: #219653;
        }}
        .stream-button {{
            display: inline-block;
            padding: 5px 10px;
            background-color: #e74c3c;
            color: white;
            text-decoration: none;
            border-radius: 3px;
            font-size: 14px;
            margin-left: 5px;
        }}
        .stream-button:hover {{
            background-color: #c0392b;
        }}
        .page-link {{
            font-size: 14px;
            margin-top: 5px;
        }}
        .page-link a {{
            color: #7f8c8d;
        }}
        .tabs {{
            display: flex;
            border-bottom: 1px solid #ddd;
            margin-bottom: 20px;
        }}
        .tab {{
            padding: 10px 15px;
            cursor: pointer;
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-bottom: none;
            border-radius: 5px 5px 0 0;
            margin-right: 5px;
        }}
        .tab.active {{
            background-color: white;
            border-bottom: 1px solid white;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        .real-stream {{
            margin-top: 10px;
            padding: 8px;
            background-color: #fef9e7;
            border-radius: 5px;
            border: 1px solid #f9e79f;
        }}
        .real-stream-title {{
            font-weight: bold;
            color: #d35400;
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Selçuk Sports Kanal Listesi</h1>
        
        <div class="stats">
            <h3>İstatistikler</h3>
            <p>Toplam Bulunan Kanal Sayısı: <strong>{len(channels)}</strong></p>
            <p>Tarama Tarihi: <strong>{now.strftime('%d.%m.%Y %H:%M')}</strong></p>
        </div>
        
        <div class="download-links">
            <a href="{csv_file}" download>CSV Olarak İndir</a>
            <a href="{json_file}" download>JSON Olarak İndir</a>
        </div>
        
        <div class="tabs">
            <div class="tab active" onclick="changeTab(event, 'channels-tab')">Kanallar</div>
            <div class="tab" onclick="changeTab(event, 'direct-streams-tab')">Doğrudan Stream Linkleri</div>
            <div class="tab" onclick="changeTab(event, 'real-streams-tab')">Gerçek Stream URL'leri</div>
        </div>
        
        <div id="channels-tab" class="tab-content active">
            <h2>Bulunan Kanallar</h2>
            
            <div class="channels-list">
"""
    
    # Her kanal için kart oluştur
    for channel in channels:
        html_content += f"""
                <div class="channel-card">
                    <div class="channel-name">{channel["channel_name"]}</div>
                    <div class="page-link">Sayfa: <a href="{channel["page_url"].split('#')[0] if '#' in channel["page_url"] else channel["page_url"]}" target="_blank">{channel["page_url"].split('#')[0] if '#' in channel["page_url"] else channel["page_url"]}</a></div>
                    <div class="video-container">
        """
        
        # Her video kaynağı için link ekle
        for i, source in enumerate(channel["video_sources"]):
            # # işaretinden sonraki kısmı temizle
            clean_source = source.split('#')[0] if '#' in source else source
            
            # URL'yi kısaltarak göster
            short_url = clean_source[:50] + "..." if len(clean_source) > 50 else clean_source
            
            html_content += f"""
                        <div class="source-link">
                            <span class="play-button" onclick="playVideo('{clean_source}')">▶ Oynat</span>
                            <a href="{clean_source}" target="_blank">Video Kaynağı {i+1}</a>
                            <div class="url-preview">{short_url}</div>
                        </div>
            """
        
        # Gerçek stream URL'lerini ekle
        if "real_stream_urls" in channel and channel["real_stream_urls"]:
            html_content += """
                    <div class="real-stream">
                        <div class="real-stream-title">Gerçek Stream URL'leri:</div>
            """
            
            for i, real_url in enumerate(channel["real_stream_urls"]):
                clean_real_url = real_url.split('#')[0] if '#' in real_url else real_url
                short_real_url = clean_real_url[:50] + "..." if len(clean_real_url) > 50 else clean_real_url
                
                html_content += f"""
                        <div class="source-link">
                            <span class="play-button" onclick="playVideo('{clean_real_url}')">▶ Oynat</span>
                            <span class="stream-button" onclick="copyToClipboard('{clean_real_url}')">📋 Kopyala</span>
                            <a href="{clean_real_url}" target="_blank">Gerçek URL {i+1}</a>
                            <div class="url-preview">{short_real_url}</div>
                        </div>
                """
            
            html_content += """
                    </div>
            """
        
        html_content += """
                    </div>
                </div>
        """
    
    # Stream URL'leri için ayrı bir sekme
    html_content += """
        </div>
        </div>
        
        <div id="direct-streams-tab" class="tab-content">
            <h2>Doğrudan Stream Linkleri</h2>
            <p>Bu listede sadece doğrudan stream URL'leri (m3u8, mp4, vb.) gösterilmektedir.</p>
            
            <div class="streams-list">
    """
    
    # Stream URL'leri biriktirme
    stream_urls = []
    for source in [source for channel in channels for source in channel["video_sources"]]:
        # # işaretinden sonraki kısmı temizle
        clean_source = source.split('#')[0] if '#' in source else source
        if '.m3u8' in clean_source or '.mp4' in clean_source:
            stream_urls.append(clean_source)
    
    # Benzersiz stream URL'leri listele
    unique_stream_urls = list(set(stream_urls))
    
    if unique_stream_urls:
        for i, stream_url in enumerate(unique_stream_urls, 1):
            # # işaretinden sonraki kısmı temizle
            clean_stream_url = stream_url.split('#')[0] if '#' in stream_url else stream_url
            short_url = clean_stream_url[:50] + "..." if len(clean_stream_url) > 50 else clean_stream_url
            
            html_content += f"""
                    <div class="channel-card">
                        <div class="channel-name">Stream URL {i}</div>
                        <div class="source-link">
                            <span class="play-button" onclick="playVideo('{clean_stream_url}')">▶ Oynat</span>
                            <span class="stream-button" onclick="copyToClipboard('{clean_stream_url}')">📋 Kopyala</span>
                            <a href="{clean_stream_url}" target="_blank">{short_url}</a>
                            <div class="url-preview">{clean_stream_url}</div>
                        </div>
                    </div>
            """
    else:
        html_content += """
                <p>Doğrudan stream linki bulunamadı.</p>
        """
    
    # Gerçek Stream URL'leri için ayrı bir sekme
    html_content += """
            </div>
        </div>
        
        <div id="real-streams-tab" class="tab-content">
            <h2>Gerçek Stream URL'leri</h2>
            <p>Bu listede oynatıcı sayfaları analiz edilerek bulunan gerçek stream URL'leri gösterilmektedir.</p>
            
            <div class="streams-list">
    """
    
    # Gerçek Stream URL'leri biriktirme
    real_stream_urls = []
    for channel in channels:
        if "real_stream_urls" in channel:
            for url in channel["real_stream_urls"]:
                real_stream_urls.append(url)
    
    # Benzersiz gerçek stream URL'leri listele
    unique_real_stream_urls = list(set(real_stream_urls))
    
    if unique_real_stream_urls:
        for i, real_url in enumerate(unique_real_stream_urls, 1):
            # # işaretinden sonraki kısmı temizle
            clean_real_url = real_url.split('#')[0] if '#' in real_url else real_url
            short_url = clean_real_url[:50] + "..." if len(clean_real_url) > 50 else clean_real_url
            
            html_content += f"""
                    <div class="channel-card">
                        <div class="channel-name">Gerçek Stream URL {i}</div>
                        <div class="source-link">
                            <span class="play-button" onclick="playVideo('{clean_real_url}')">▶ Oynat</span>
                            <span class="stream-button" onclick="copyToClipboard('{clean_real_url}')">📋 Kopyala</span>
                            <a href="{clean_real_url}" target="_blank">{short_url}</a>
                            <div class="url-preview">{clean_real_url}</div>
                        </div>
                    </div>
            """
    else:
        html_content += """
                <p>Gerçek stream linki bulunamadı.</p>
        """
    
    # HTML'yi tamamla
    html_content += """
            </div>
        </div>
        
        <div class="footer">
            <p>Bu rapor otomatik olarak oluşturulmuştur.</p>
        </div>
    </div>
    
    <script>
        function playVideo(videoUrl) {
            // Basit bir video oynatıcı açar
            let playerWindow = window.open('', '_blank', 'width=800,height=600');
            playerWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Video Oynatıcı</title>
                    <style>
                        body { margin: 0; background-color: #000; }
                        video { width: 100%; height: 100vh; }
                    </style>
                </head>
                <body>
                    <video controls autoplay>
                        <source src="${videoUrl}" type="application/x-mpegURL">
                        Tarayıcınız video oynatmayı desteklemiyor.
                    </video>
                </body>
                </html>
            `);
        }
        
        function changeTab(event, tabId) {
            // Tüm sekmeleri pasif yap
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Tüm içerikleri gizle
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Tıklanan sekmeyi aktif yap
            event.currentTarget.classList.add('active');
            
            // İlgili içeriği göster
            document.getElementById(tabId).classList.add('active');
        }
        
        function copyToClipboard(text) {
            // Metni panoya kopyala
            navigator.clipboard.writeText(text).then(() => {
                alert('URL panoya kopyalandı!');
            }).catch(err => {
                console.error('Kopyalama işlemi başarısız oldu: ', err);
            });
        }
    </script>
</body>
</html>
"""
    
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(html_content)
    
    print(f"HTML raporu {filename} dosyasına kaydedildi.")
    return filename

def find_working_url():
    """Çalışan URL'yi bulur ve döndürür"""
    base_url = "https://www.selcuksportshd"
    start_number = 1783
    max_attempts = 20
    
    print("Çalışan URL aranıyor...")
    
    for i in range(start_number, start_number + max_attempts):
        url = f"{base_url}{i}.xyz"
        print(f"URL kontrol ediliyor: {url}", end="\r")
        
        html_content = check_url(url)
        if html_content:
            print(f"\nÇalışan URL bulundu: {url}")
            return url, html_content
            
        # Kısa bir bekleme
        time.sleep(0.5)
    
    # Alternatif domainleri kontrol et
    alternative_domains = [
        f"https://www.selcuksportshd.com",
        f"https://www.selcuksports.com",
        f"https://www.selcuksports.xyz",
        f"https://www.selcuksports.live",
        f"https://www.selcuksport.xyz"
    ]
    
    print("\nAlternatif domainler kontrol ediliyor...")
    for domain in alternative_domains:
        print(f"URL kontrol ediliyor: {domain}", end="\r")
        html_content = check_url(domain)
        if html_content:
            print(f"\nÇalışan URL bulundu: {domain}")
            return domain, html_content
        time.sleep(0.5)
    
    return None, None

def main():
    print("Selçuk Sports kanal taraması başlatılıyor...\n")
    
    # Çalışan URL'yi bul
    working_url, html_content = find_working_url()
    
    if not working_url or not html_content:
        print("\nHiç çalışan URL bulunamadı. Program sonlandırılıyor.")
        return
    
    print(f"Ana sayfa URL: {working_url}")
    
    # Ana sayfayı da bir kanal olarak değerlendir
    main_page_info = extract_channel_info(html_content, working_url)
    working_channels = []
    
    # Ana sayfada video kaynağı varsa ekle
    if main_page_info["video_sources"]:
        print(f"Ana sayfada video kaynağı bulundu: {main_page_info['channel_name']}")
        for source in main_page_info["video_sources"][:5]:  # İlk 5 kaynağı göster
            print(f" - {source}")
        if len(main_page_info["video_sources"]) > 5:
            print(f" - ... ve {len(main_page_info['video_sources']) - 5} kaynak daha")
        working_channels.append(main_page_info)
    else:
        print("Ana sayfada video kaynağı bulunamadı.")
    
    # Ana sayfadan kanal linklerini çıkar
    print("\nAna sayfadan kanal linkleri çıkarılıyor...")
    channel_links = extract_channel_links(html_content, working_url)
    
    if not channel_links:
        print("Kanal linkleri bulunamadı. Sadece ana sayfa bilgileri kullanılacak.")
    else:
        print(f"Toplam {len(channel_links)} kanal linki bulundu.")
        
        # Her kanal için bilgileri topla
        processed = 0
        
        for link in channel_links:
            # Ana sayfayı tekrar işlemeye gerek yok
            if link == working_url:
                continue
                
            processed += 1
            print(f"\r{processed}/{len(channel_links)} kanal işleniyor: {link}", end="")
            
            # Sayfa içeriğini al
            channel_html = check_url(link)
            if not channel_html:
                print(f"\nBağlantı hatası: {link}")
                continue
            
            # Kanal bilgilerini çıkar
            channel_info = extract_channel_info(channel_html, link)
            
            # Eğer video kaynakları bulunursa listeye ekle
            if channel_info["video_sources"]:
                print(f"\nKanal bulundu: {channel_info['channel_name']}")
                for source in channel_info["video_sources"][:3]:  # İlk 3 kaynağı göster
                    print(f" - {source}")
                if len(channel_info["video_sources"]) > 3:
                    print(f" - ... ve {len(channel_info['video_sources']) - 3} kaynak daha")
                working_channels.append(channel_info)
            
            # Siteyi yormamak için kısa bir bekleme
            time.sleep(0.5)
    
    # Benzersiz kanalları belirle (eğer aynı URL'ye sahip kanallar varsa)
    unique_channels = []
    seen_urls = set()
    
    for channel in working_channels:
        if channel["page_url"] not in seen_urls:
            seen_urls.add(channel["page_url"])
            unique_channels.append(channel)
    
    print(f"\n\nToplam {len(unique_channels)} benzersiz kanal bulundu!")
    
    if not unique_channels:
        print("Hiç çalışan kanal bulunamadı. Program sonlandırılıyor.")
        return

    # Gerçek stream URL'lerini çıkar
    print("\nGerçek stream URL'leri çıkarılıyor...")
    for i, channel in enumerate(unique_channels, 1):
        print(f"Kanal {i}/{len(unique_channels)}: {channel['channel_name']}")
        real_stream_sources = []
        
        total_sources = len(channel["video_sources"])
        for j, source in enumerate(channel["video_sources"], 1):
            print(f"\n[{j}/{total_sources}] Kaynak inceleniyor...")
            real_url = extract_real_stream_url(source)
            if real_url:
                real_stream_sources.append(real_url)
                print(f"✅ Gerçek stream URL'si eklendi!")
            else:
                print(f"❌ Bu kaynaktan gerçek stream URL'si çıkarılamadı")
        
        # Bulunan gerçek stream URL'lerini ekle
        if real_stream_sources:
            print(f"\n✅ Toplam {len(real_stream_sources)} gerçek stream URL'si bulundu!")
            channel["real_stream_urls"] = list(set(real_stream_sources))
        else:
            print(f"\n❌ Bu kanaldan hiç gerçek stream URL'si bulunamadı")
            channel["real_stream_urls"] = []
        
        # Kısa bir bekleme ekleyelim, siteleri çok yormamak için
        if i < len(unique_channels):
            print(f"\nSonraki kanala geçiliyor, lütfen bekleyin...")
            time.sleep(2)
    
    # Kanalları listele
    print("\nBulunan kanallar:")
    for i, channel in enumerate(unique_channels, 1):
        print(f"{i}. {channel['channel_name']} - {channel['page_url']}")
        sources_text = ', '.join(channel['video_sources'])
        if len(sources_text) > 100:
            sources_text = sources_text[:100] + "..."
        print(f"   Video Kaynakları: {sources_text}")
        
        # Gerçek Stream URL'lerini göster
        if "real_stream_urls" in channel and channel["real_stream_urls"]:
            real_urls_text = ', '.join(channel['real_stream_urls'])
            if len(real_urls_text) > 100:
                real_urls_text = real_urls_text[:100] + "..."
            print(f"   Gerçek Stream URL'leri: {real_urls_text}")
        
        print("-" * 50)
    
    # Sonuçları farklı formatlarda kaydet
    csv_file = save_to_csv(unique_channels)
    json_file = save_to_json(unique_channels)
    html_file = generate_html_report(unique_channels, csv_file, json_file)
    
    # HTML dosyasını aç
    try:
        os.system(f'start {html_file}')
        print(f"HTML raporu tarayıcıda açıldı: {html_file}")
    except Exception as e:
        print(f"HTML raporu oluşturuldu, ancak otomatik açılamadı: {html_file}")
        print(f"Hata: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram kullanıcı tarafından durduruldu.")
        sys.exit(0)
    except Exception as e:
        print(f"\nBeklenmedik bir hata oluştu: {str(e)}")
        sys.exit(1) 
