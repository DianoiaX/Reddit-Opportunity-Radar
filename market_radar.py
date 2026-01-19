import praw
import time
import os
import json
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Çıktı encoding'ini UTF-8'e zorla (Windows için)
sys.stdout.reconfigure(encoding='utf-8')

# Çevresel değişkenleri yükle
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Hedefler
TARGET_SUBREDDITS = ["SaaS", "Entrepreneur", "smallbusiness", "startups", "marketing", "sideproject"]
KEYWORDS = ["how do i", "alternative to", "pain in the ass", "hate when", "manual work", "too expensive", "wish there was"]

# API İstemcilerini Başlat
try:
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        print("❌ Reddit API bilgileri eksik! .env dosyasını kontrol et.")
    
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT
    )
except Exception as e:
    print(f"Reddit başlatma hatası: {e}")

try:
    if not GEMINI_API_KEY:
        print("❌ Gemini API anahtarı eksik! .env dosyasını kontrol et.")
    else:
        genai.configure(api_key=GEMINI_API_KEY)
        # Gemini modelini seç
        model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Gemini başlatma hatası: {e}")

def analyze_with_ai(text):
    """Metni Gemini'ye gönderip iş fikri potansiyelini ölçer"""
    if not GEMINI_API_KEY:
        return None

    prompt = f"""
    Aşağıdaki Reddit gönderisini bir yazılım girişimcisi gözüyle analiz et.
    Metin: "{text}"
    
    Eğer bu metinde bir SaaS veya yazılım iş fikri fırsatı varsa (bir problem, acı noktası, eksiklik), JSON formatında şu yanıtı ver:
    {{
        "is_opportunity": true,
        "pain_point": "Kısaca problemin ne olduğu",
        "target_audience": "Kimler bu sorunu yaşıyor",
        "suggested_solution": "Nasıl bir app/tool yapılabilir",
        "score": 1-10 arası puan (10 çok net bir fırsat demek)
    }}
    
    Eğer sadece boş bir şikayetse veya yazılımla çözülemezse sadece şunu döndür:
    {{ "is_opportunity": false }}
    
    Yanıtı sadece JSON olarak ver, markdown formatlama (```json ... ```) kullanma.
    """

    try:
        response = model.generate_content(prompt)
        # Markdown backtick'lerini temizle (Gemini bazen ekler)
        cleaned_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(cleaned_text)
    except Exception as e:
        print(f"AI Hatası: {e}")
        return None

def scan_reddit():
    print("🧠 AI Destekli Market Radar Başlatılıyor (Gemini)...")
    print(f"🎯 Hedef Subredditler: {', '.join(TARGET_SUBREDDITS)}")
    print(f"🔑 Anahtar Kelimeler: {', '.join(KEYWORDS)}\n")
    
    try:
        subreddit = reddit.subreddit("+".join(TARGET_SUBREDDITS))
        
        print("📡 Canlı akış dinleniyor... (Durdurmak için Ctrl+C)\n")
        
        # skip_existing=True yapıyoruz ki geçmişle boğulmayalım, yeni düşenleri yakalayalım
        for submission in subreddit.stream.submissions(skip_existing=True):
            
            try:
                full_text = (submission.title + " " + (submission.selftext or "")).lower()
                
                # 1. Filtre: Anahtar kelime var mı? (API maliyetini düşürmek için)
                found_keywords = [kw for kw in KEYWORDS if kw in full_text]
                
                if found_keywords:
                    # İçerik çok kısaysa atla
                    if len(submission.selftext) < 20: continue

                    print(f"🔎 İnceleniyor ({', '.join(found_keywords)}): {submission.title[:60]}...")
                    
                    # 2. Filtre: AI Analizi
                    analysis = analyze_with_ai(submission.title + "\n" + submission.selftext)
                    
                    if analysis and analysis.get("is_opportunity"):
                        score = analysis.get("score", 0)
                        if score >= 7: # Sadece yüksek puanlıları göster
                            print("\n" + "="*60)
                            print(f"🚀 YENİ FIRSAT TESPİT EDİLDİ (Puan: {score}/10)")
                            print(f"📌 Başlık: {submission.title}")
                            print(f"🔗 Link: https://reddit.com{submission.permalink}")
                            print(f"😭 Problem: {analysis.get('pain_point', 'Belirtilmedi')}")
                            print(f"🎯 Hedef Kitle: {analysis.get('target_audience', 'Belirtilmedi')}")
                            print(f"💡 Fikir: {analysis.get('suggested_solution', 'Belirtilmedi')}")
                            print("="*60 + "\n")
                        else:
                            print(f"❌ Düşük skor ({score}/10) - Pas geçildi.")
                    else:
                        print("❌ Fırsat bulunamadı.")
            except Exception as e:
                print(f"Post işleme hatası: {e}")
                continue
                
    except KeyboardInterrupt:
        print("\n👋 Tarama durduruldu.")
    except Exception as e:
        print(f"\n❌ Tarama hatası: {e}")

if __name__ == "__main__":
    scan_reddit()
