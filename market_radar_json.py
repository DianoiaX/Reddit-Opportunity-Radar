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
# 1. Output Buffering'i devre dışı bırak
sys.stdout.reconfigure(line_buffering=True, encoding='utf-8')
warnings.filterwarnings("ignore")

# Çevresel değişkenleri yükle
load_dotenv()

# Gemini API Key'i .env dosyasından al
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Modeli Yapılandır
if not GEMINI_API_KEY:
    print("❌ GEMINI_API_KEY bulunamadı! .env dosyasını kontrol et.")
    sys.exit(1)

# Yeni google-genai client oluştur (GEMINI_API_KEY env var'dan otomatik alır)
client = genai.Client()

# Model Seçimi: 'gemini-1.5-flash' (Hızlı/Ucuz) veya 'gemini-1.5-pro' (Akıllı)
MODEL_NAME = "gemini-2.5-flash"

# Daha spesifik kelimeler kullan (API kullanımını azaltmak için)
TARGET_SUBREDDITS = ["SaaS", "Entrepreneur", "smallbusiness", "startups", "sideproject", "microsaas"]
KEYWORDS = ["how do i", "alternative to", "looking for", "wish there was", "need a tool", "pain in the"]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
}

seen_posts = set() 

def analyze_with_gemini(text):
    """Metni Gemini'ye gönderip iş fikri potansiyelini ölçer"""
    
    prompt = f"""
    Sen deneyimli bir yazılım girişimcisisin. Aşağıdaki Reddit gönderisini analiz et.
    
    Gönderi: "{text}"
    
    Eğer bu metinde NET bir SaaS, Mikro-SaaS veya yazılım iş fikri fırsatı (bir acı noktası, manuel yapılan bir iş, eksik bir araç) varsa JSON formatında yanıt ver.
    
    İstenen JSON Formatı:
    {{
        "is_opportunity": true,
        "pain_point": "Kısaca problemin ne olduğu",
        "target_audience": "Kimler bu sorunu yaşıyor",
        "suggested_solution": "Nasıl bir app/tool yapılabilir",
        "score": 8 (1-10 arası, sadece 7 ve üzeri ise true yap)
    }}
    
    Eğer sadece boş bir şikayet, alakasız bir soru veya yazılımla çözülemeyecek bir durumsa:
    {{ "is_opportunity": false }}
    
    Sadece JSON döndür, başka bir şey yazma.
    """

    try:
        # Yeni google-genai API kullanımı
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )
        
        # Gelen yanıtı JSON'a çevir
        return json.loads(response.text)
        
    except Exception as e:
        print(f"⚠️ Gemini Hatası: {e}", flush=True)
        return None

# --- CSV KAYIT FONKSİYONU ---
def save_to_csv(data):
    file_exists = os.path.isfile('firsatlar.csv')
    
    with open('firsatlar.csv', 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Tarih", "Puan", "Problem", "Fikir", "Hedef Kitle", "Link"])
        
        # Dosya yoksa önce başlıkları yaz
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
            
            # Rate limit: sadece 10 post al (API kullanımını azaltmak için)
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
                    
                    # Rate limit: API çağrıları arasında 5 saniye bekle
                    time.sleep(5)
                    
                    if analysis:  # Analysis null değilse
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
                            # TEST İÇİN: Düşük puanlıları da yazdıralım
                            print(f"   ❌ Pas Geçildi (Puan: {score}) - Sebep: {analysis.get('pain_point', 'Fırsat görülmedi')}", flush=True)
            
            print(f" Bitti. ({new_count} yeni)", flush=True)
            time.sleep(60) # 1 Dakika bekle
            
        except KeyboardInterrupt:
            print("\n👋 Tarama durduruldu.", flush=True)
            break
        except Exception as e:
            print(f"\n⚠️ Genel Hata: {e}", flush=True)
            time.sleep(60)

if __name__ == "__main__":
    scan_reddit_json()
