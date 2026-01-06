import requests
import time
import json
import sys
import warnings
import os
import csv
from dotenv import load_dotenv
from google import genai

# --- AYARLAR ---
sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')
warnings.filterwarnings("ignore")

# Çevresel değişkenleri yükle
load_dotenv()

# Gemini API Key'i .env dosyasından al
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY bulunamadı! .env dosyasını kontrol et.")
    sys.exit(1)

# Yeni google-genai client oluştur
client = genai.Client(api_key=GEMINI_API_KEY)

# Model Seçimi
# 'gemini-1.5-flash', 'gemini-2.0-flash-exp', 'gemini-1.5-pro' deneyebiliriz
MODEL_NAME = "gemini-2.0-flash-exp" 

# Hedef subredditler ve anahtar kelimeler
TARGET_SUBREDDITS = ["SaaS", "Entrepreneur", "smallbusiness", "startups", "sideproject", "microsaas"]
KEYWORDS = ["how do i", "alternative to", "looking for", "wish there was", "need a tool", "pain in the"]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}

seen_posts = set()

def analyze_with_gemini(text):
    """Metni Gemini'ye gönderir. 429 Hatası alırsa bekleyip tekrar dener."""
    
    max_retries = 5 
    base_wait_time = 20 # Free tier bazen uzun süre kilitliyor, 20sn ile başlayalım

    prompt = f"""
    Sen deneyimli bir yazılım girişimcisisin. Aşağıdaki Reddit gönderisini analiz et.
    Gönderi: "{text}"
    Eğer bu metinde NET bir SaaS, Mikro-SaaS veya yazılım iş fikri fırsatı varsa JSON formatında yanıt ver.
    İstenen JSON Formatı:
    {{
        "is_opportunity": true,
        "pain_point": "Kısaca problemin ne olduğu",
        "target_audience": "Kimler bu sorunu yaşıyor",
        "suggested_solution": "Nasıl bir app/tool yapılabilir",
        "score": 8
    }}
    Eğer fırsat yoksa: {{ "is_opportunity": false }}
    """

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            
            # Başarılı istekten sonra kotayı korumak için zorunlu bekleme
            time.sleep(5) 
            
            return json.loads(response.text)
            
        except Exception as e:
            error_msg = str(e)
            # Eğer hata 429 (Resource Exhausted) ise
            if "429" in error_msg or "Resource has been exhausted" in error_msg or "Quota exceeded" in error_msg:
                wait_time = base_wait_time * (attempt + 1)
                print(f"\n⚠️ Kota aşıldı (429). {wait_time} saniye soğutuluyor... (Deneme {attempt+1}/{max_retries})", flush=True)
                time.sleep(wait_time)
            else:
                print(f"⚠️ Kritik Gemini Hatası: {e}", flush=True)
                return None
    
    print("\n❌ Maksimum deneme sayısına ulaşıldı. Bu post atlanıyor.", flush=True)
    return None

# --- CSV KAYIT FONKSİYONU ---
def save_to_csv(data):
    file_exists = os.path.isfile('firsatlar.csv')
    
    with open('firsatlar.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Tarih", "Puan", "Problem", "Fikir", "Hedef Kitle", "Link"])
        
        if not file_exists:
            writer.writeheader()
            
        writer.writerow({
            "Tarih": time.strftime('%Y-%m-%d %H:%M:%S'),
            "Puan": data.get('score'),
            "Problem": data.get('pain_point'),
            "Fikir": data.get('suggested_solution'),
            "Hedef Kitle": data.get('target_audience'),
            "Link": f"https://www.reddit.com{data.get('permalink')}"
        })
    print("💾 Fırsat CSV dosyasına kaydedildi!", flush=True)

def scan_reddit_json():
    print(f"📡 Market Radar (Gemini: {MODEL_NAME}) Başlatılıyor...", flush=True)
    print(f"🎯 Hedefler: {TARGET_SUBREDDITS}", flush=True)
    print("-" * 50, flush=True)
    
    while True:
        try:
            print(f"🔄 [{time.strftime('%H:%M:%S')}] Reddit taranıyor...", end='', flush=True)
            
            url = f"https://www.reddit.com/r/{'+'.join(TARGET_SUBREDDITS)}/new.json?limit=10"
            response = requests.get(url, headers=HEADERS, timeout=10)
            
            if response.status_code != 200:
                print(f"\n❌ Bağlantı hatası: {response.status_code}. 30 sn bekleniyor...", flush=True)
                time.sleep(30)
                continue
                
            data = response.json()
            posts = data['data']['children']
            new_count = 0
            
            for post in posts:
                post_data = post['data']
                pid = post_data['id']
                
                if pid in seen_posts: continue
                seen_posts.add(pid)
                new_count += 1
                
                title = post_data.get('title', '')
                selftext = post_data.get('selftext', '')
                full_text = (title + " " + selftext).lower()
                
                # Keyword Kontrolü
                if any(kw in full_text for kw in KEYWORDS):
                    print(f"\n🔎 İnceleniyor: {title[:40]}...", flush=True)
                    
                    analysis = analyze_with_gemini(title + "\n" + selftext)
                    
                    if analysis:
                        score = analysis.get("score", 0)
                        
                        if analysis.get("is_opportunity") and score >= 7:
                            print("\n" + "★"*60)
                            print(f"🚀 YENİ FIRSAT (Puan: {score}/10)")
                            print(f"🔗 Link: https://www.reddit.com{post_data['permalink']}")
                            print(f"😭 Problem: {analysis.get('pain_point', 'N/A')}")
                            print(f"🎯 Hedef: {analysis.get('target_audience', 'N/A')}")
                            print(f"💡 Fikir: {analysis.get('suggested_solution', 'N/A')}")
                            print("★"*60 + "\n", flush=True)
                            
                            # CSV'ye kaydet
                            csv_data = analysis.copy()
                            csv_data['permalink'] = post_data['permalink']
                            save_to_csv(csv_data)
                        else:
                            print(f"   ❌ Pas Geçildi (Puan: {score})", flush=True)
            
            print(f" Bitti. ({new_count} yeni)", flush=True)
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n👋 Tarama durduruldu.", flush=True)
            break
        except Exception as e:
            print(f"\n⚠️ Genel Hata: {e}", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    scan_reddit_json()
