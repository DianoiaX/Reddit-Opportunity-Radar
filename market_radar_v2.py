"""
Reddit Market Radar v2.0
-------------------------
Reddit'ten iş fırsatlarını AI ile tarayan gelişmiş bot.

Özellikler:
- OpenAI veya Gemini desteği (seçilebilir)
- Batch analiz modu (5'li paketler)
- CSV kayıt sistemi
- .env ile güvenli API key yönetimi
- Gelişmiş hata yönetimi
- Rate limiting koruması
"""

import requests
import time
import json
import sys
import os
import csv
from datetime import datetime
from dotenv import load_dotenv

# Çıktı encoding'ini UTF-8'e zorla (Windows için)
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)

# .env'den API anahtarlarını yükle
load_dotenv()

# --- YAPILANDIRMA ---
class Config:
    # API Seçimi: "openai" veya "gemini"
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'openai').lower()
    
    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
    
    # Gemini
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-lite')
    
    # Batch Ayarları
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '5'))
    MIN_SCORE = int(os.getenv('MIN_SCORE', '7'))
    
    # Tarama Ayarları
    SCAN_INTERVAL = int(os.getenv('SCAN_INTERVAL', '60'))  # saniye
    API_COOLDOWN = int(os.getenv('API_COOLDOWN', '5'))  # API istekleri arası bekleme
    
    # Hedef Subredditler
    TARGET_SUBREDDITS = [
        "SaaS", "Entrepreneur", "smallbusiness", 
        "startups", "sideproject", "microsaas", "marketing"
    ]
    
    # Tetikleyici Kelimeler
    KEYWORDS = [
        "how do i", "alternative to", "pain", "hate", "manual", 
        "expensive", "looking for", "wish", "help", "need tool", 
        "idea", "frustrated", "recommend", "suggestion", "advice"
    ]
    
    # HTTP Header
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # Çıktı dosyası
    OUTPUT_FILE = 'firsatlar.csv'


class AIAnalyzer:
    """AI analiz sınıfı - OpenAI ve Gemini desteği"""
    
    def __init__(self):
        self.provider = Config.AI_PROVIDER
        self._setup_client()
    
    def _setup_client(self):
        """AI istemcisini başlat"""
        if self.provider == 'openai':
            try:
                from openai import OpenAI
                if not Config.OPENAI_API_KEY:
                    raise ValueError("OPENAI_API_KEY bulunamadı!")
                self.client = OpenAI(api_key=Config.OPENAI_API_KEY)
                self.model = Config.OPENAI_MODEL
                print(f"✅ OpenAI bağlantısı kuruldu (Model: {self.model})")
            except ImportError:
                print("❌ openai paketi yüklü değil! 'pip install openai' çalıştırın.")
                sys.exit(1)
        
        elif self.provider == 'gemini':
            try:
                from google import genai
                if not Config.GEMINI_API_KEY:
                    raise ValueError("GEMINI_API_KEY bulunamadı!")
                self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
                self.model = Config.GEMINI_MODEL
                print(f"✅ Gemini bağlantısı kuruldu (Model: {self.model})")
            except ImportError:
                print("❌ google-genai paketi yüklü değil! 'pip install google-genai' çalıştırın.")
                sys.exit(1)
        else:
            raise ValueError(f"Geçersiz AI sağlayıcı: {self.provider}")
    
    def analyze_batch(self, posts_buffer):
        """Biriken postları topluca analiz et"""
        if not posts_buffer:
            return []
        
        print(f"\n⚡ {len(posts_buffer)} adet post AI'ya gönderiliyor...", flush=True)
        
        # Postları formatla
        formatted_text = self._format_posts(posts_buffer)
        prompt = self._create_prompt(len(posts_buffer), formatted_text)
        
        try:
            if self.provider == 'openai':
                return self._analyze_with_openai(prompt)
            else:
                return self._analyze_with_gemini(prompt)
        except Exception as e:
            print(f"⚠️ AI Analiz Hatası: {e}")
            time.sleep(10)
            return []
    
    def _format_posts(self, posts_buffer):
        """Postları metin formatına dönüştür"""
        formatted = ""
        for i, post in enumerate(posts_buffer):
            formatted += f"""
--- POST ID {i} ---
Link: {post['permalink']}
Content: {post['text'][:1500]}
-------------------
"""
        return formatted
    
    def _create_prompt(self, count, formatted_text):
        """AI için prompt oluştur"""
        return f"""
Aşağıda {count} adet Reddit gönderisi var. Hepsini tek tek analiz et.
Sen deneyimli bir yazılım girişimcisisin. NET bir yazılım/SaaS fırsatı sunanları bul.

Girdiler:
{formatted_text}

Yanıtın SADECE geçerli bir JSON listesi (array) olmalı. Başka hiçbir şey ekleme.
Her bir post için şu yapıyı kullan:

[
  {{
    "post_id": 0,
    "is_opportunity": true,
    "pain_point": "Problem tanımı (1-2 cümle)",
    "target_audience": "Hedef kitle",
    "suggested_solution": "Çözüm önerisi (kısa)",
    "score": 8
  }},
  {{
    "post_id": 1,
    "is_opportunity": false
  }}
]

Kurallar:
- Sadece skoru {Config.MIN_SCORE} ve üzeri olanları is_opportunity: true yap
- Yazılımla çözülemeyecek sorunları false olarak işaretle
- Belirsiz veya genel şikayetleri false olarak işaretle
- JSON dışında HİÇBİR ŞEY yazma
"""
    
    def _analyze_with_openai(self, prompt):
        """OpenAI ile analiz"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Sen bir JSON API'sisin. Sadece geçerli JSON döndür."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        time.sleep(Config.API_COOLDOWN)
        
        result = json.loads(response.choices[0].message.content)
        # OpenAI bazen {"results": [...]} formatında dönebilir
        if isinstance(result, dict) and "results" in result:
            return result["results"]
        elif isinstance(result, list):
            return result
        else:
            # Tek obje döndüyse listeye çevir
            return [result] if result else []
    
    def _analyze_with_gemini(self, prompt):
        """Gemini ile analiz (yeni google-genai SDK)"""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.3
            }
        )
        time.sleep(Config.API_COOLDOWN)
        
        # JSON parse
        text = response.text.strip()
        if text.startswith('```'):
            text = text.replace('```json', '').replace('```', '').strip()
        
        return json.loads(text)


class CSVWriter:
    """CSV kayıt yöneticisi"""
    
    FIELDNAMES = ["Tarih", "Puan", "Problem", "Fikir", "Hedef", "Link"]
    
    @staticmethod
    def save(opportunities):
        """Fırsatları CSV'ye kaydet"""
        if not opportunities:
            return
        
        file_exists = os.path.isfile(Config.OUTPUT_FILE)
        
        with open(Config.OUTPUT_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSVWriter.FIELDNAMES)
            
            if not file_exists:
                writer.writeheader()
            
            for opp in opportunities:
                writer.writerow({
                    "Tarih": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "Puan": opp.get('score', 'N/A'),
                    "Problem": opp.get('pain_point', 'N/A'),
                    "Fikir": opp.get('suggested_solution', 'N/A'),
                    "Hedef": opp.get('target_audience', 'N/A'),
                    "Link": opp.get('permalink', 'N/A')
                })
        
        print(f"💾 {len(opportunities)} fırsat CSV'ye kaydedildi.", flush=True)


class MarketRadar:
    """Ana tarama sınıfı"""
    
    def __init__(self):
        self.analyzer = AIAnalyzer()
        self.seen_posts = set()
        self.post_buffer = []
    
    def run(self):
        """Radar'ı başlat"""
        self._print_banner()
        
        while True:
            try:
                self._scan_cycle()
                time.sleep(Config.SCAN_INTERVAL)
            except KeyboardInterrupt:
                print("\n\n👋 Market Radar durduruldu. Güle güle!")
                break
            except Exception as e:
                print(f"\n⚠️ Beklenmeyen hata: {e}")
                time.sleep(60)
    
    def _print_banner(self):
        """Başlık yazdır"""
        print("\n" + "="*60)
        print("🚀 MARKET RADAR v2.0 - Reddit Fırsat Tarayıcısı")
        print("="*60)
        print(f"🤖 AI Sağlayıcı: {Config.AI_PROVIDER.upper()}")
        print(f"📦 Batch Boyutu: {Config.BATCH_SIZE}")
        print(f"🎯 Min. Puan: {Config.MIN_SCORE}")
        print(f"📍 Subredditler: {', '.join(Config.TARGET_SUBREDDITS)}")
        print("="*60 + "\n")
        print("📡 Tarama başlatılıyor... (Durdurmak için Ctrl+C)\n")
    
    def _scan_cycle(self):
        """Tek bir tarama döngüsü"""
        url = f"https://www.reddit.com/r/{'+'.join(Config.TARGET_SUBREDDITS)}/new.json?limit=25"
        
        try:
            response = requests.get(url, headers=Config.HEADERS, timeout=15)
            
            if response.status_code == 429:
                print("⏳ Rate limit! 60 saniye bekleniyor...")
                time.sleep(60)
                return
            
            if response.status_code != 200:
                print(f"⚠️ Reddit HTTP {response.status_code}")
                return
            
            data = response.json()
            posts = data.get('data', {}).get('children', [])
            
            new_count = 0
            for post in posts:
                if self._process_post(post['data']):
                    new_count += 1
            
            # Buffer dolduysa analiz et
            if len(self.post_buffer) >= Config.BATCH_SIZE:
                self._analyze_buffer()
            
            status = f"🔄 Tarandı: {len(posts)} post | Yeni: {new_count} | Buffer: {len(self.post_buffer)}/{Config.BATCH_SIZE}"
            print(status, end='\r', flush=True)
            
        except requests.exceptions.Timeout:
            print("⏳ Reddit timeout, tekrar denenecek...")
        except requests.exceptions.RequestException as e:
            print(f"⚠️ İstek hatası: {e}")
    
    def _process_post(self, post_data):
        """Tek bir postu işle"""
        pid = post_data.get('id')
        
        if pid in self.seen_posts:
            return False
        
        self.seen_posts.add(pid)
        
        title = post_data.get('title', '')
        selftext = post_data.get('selftext', '')
        full_text = (title + " " + selftext).lower()
        
        # Çok kısa içerikleri atla
        if len(selftext) < 30:
            return False
        
        # Keyword kontrolü
        if any(kw in full_text for kw in Config.KEYWORDS):
            print(f"\n➕ Buffer'a eklendi: {title[:50]}...", flush=True)
            
            self.post_buffer.append({
                "text": title + "\n" + selftext,
                "permalink": f"https://www.reddit.com{post_data['permalink']}"
            })
            return True
        
        return False
    
    def _analyze_buffer(self):
        """Buffer'daki postları analiz et"""
        results = self.analyzer.analyze_batch(self.post_buffer)
        opportunities = []
        
        for res in results:
            if res.get("is_opportunity") and res.get("score", 0) >= Config.MIN_SCORE:
                p_idx = res.get("post_id")
                
                if p_idx is not None and p_idx < len(self.post_buffer):
                    real_link = self.post_buffer[p_idx]['permalink']
                    
                    # Konsola yazdır
                    self._print_opportunity(res, real_link)
                    
                    # CSV için hazırla
                    opp = res.copy()
                    opp['permalink'] = real_link
                    opportunities.append(opp)
        
        if opportunities:
            CSVWriter.save(opportunities)
        else:
            print("❌ Bu pakette yüksek puanlı fırsat bulunamadı.\n")
        
        # Buffer'ı temizle
        self.post_buffer = []
    
    def _print_opportunity(self, opp, link):
        """Fırsat bilgisini yazdır"""
        print("\n" + "★"*60)
        print(f"🚀 YENİ FIRSAT BULUNDU! (Puan: {opp.get('score', 'N/A')}/10)")
        print(f"🔗 {link}")
        print(f"😭 Problem: {opp.get('pain_point', 'N/A')}")
        print(f"🎯 Hedef: {opp.get('target_audience', 'N/A')}")
        print(f"💡 Çözüm: {opp.get('suggested_solution', 'N/A')}")
        print("★"*60 + "\n", flush=True)


def main():
    """Ana giriş noktası"""
    # Gerekli API key kontrolü
    if Config.AI_PROVIDER == 'openai' and not Config.OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY bulunamadı!")
        print("   .env dosyasına OPENAI_API_KEY=sk-xxx ekleyin.")
        sys.exit(1)
    
    if Config.AI_PROVIDER == 'gemini' and not Config.GEMINI_API_KEY:
        print("❌ GEMINI_API_KEY bulunamadı!")
        print("   .env dosyasına GEMINI_API_KEY=xxx ekleyin.")
        sys.exit(1)
    
    radar = MarketRadar()
    radar.run()


if __name__ == "__main__":
    main()
