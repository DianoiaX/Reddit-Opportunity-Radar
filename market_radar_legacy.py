

import praw
import os
from dotenv import load_dotenv
from datetime import datetime

# .env dosyasından çevresel değişkenleri yükle
load_dotenv()


# Hedeflediğimiz Subredditler
TARGET_SUBREDDITS = [
    "SaaS",           # SaaS araçları hakkında şikayetler
    "Entrepreneur",   # Girişimcilik fırsatları
    "smallbusiness",  # Gerçek işletme sahiplerinin sorunları
    "startups",       # Startup ekosistemi
    "sideproject"     # Yan projeler ve fikirler
]

# Avlayacağımız Anahtar Kelimeler (Case insensitive arama yapacağız)
# Bu kalıplar genellikle bir problem veya ihtiyaç sinyali verir
KEYWORDS = [
    "how do i",           # Manuel yapılan bir iş sinyali
    "alternative to",     # Mevcut çözüm pahalı veya kötü
    "pain in the ass",    # Çözülmesi gereken bir sorun
    "hate when",          # Duygusal tepki = Satış fırsatı
    "manual work",        # Otomasyon fırsatı
    "too expensive",      # Fiyat problemi
    "wish there was",     # Karşılanmamış ihtiyaç
    "tired of",           # Hayal kırıklığı
    "spreadsheet",        # Otomasyon fırsatı
    "looking for a tool", # Aktif çözüm arayışı
    "anyone know",        # Bilgi arayışı
    "is there a",         # Çözüm arayışı
    "struggling with",    # Problem yaşıyor
    "need help with",     # Yardım ihtiyacı
    "frustrated with"     # Hayal kırıklığı
]


def validate_credentials():
    """Reddit API bilgilerinin tanımlı olup olmadığını kontrol eder."""
    if not REDDIT_CLIENT_ID or REDDIT_CLIENT_ID == 'your_client_id_here':
        print("❌ HATA: REDDIT_CLIENT_ID tanımlı değil!")
        print("   .env dosyasını kontrol et ve Reddit API bilgilerini gir.")
        return False
    if not REDDIT_CLIENT_SECRET or REDDIT_CLIENT_SECRET == 'your_client_secret_here':
        print("❌ HATA: REDDIT_CLIENT_SECRET tanımlı değil!")
        print("   .env dosyasını kontrol et ve Reddit API bilgilerini gir.")
        return False
    return True


def format_post(submission, found_keywords):
    """Bulunan bir postu güzel formatta yazdırır."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    print(f"\n{'='*60}")
    print(f"🚨 FIRSAT SİNYALİ! [{timestamp}]")
    print(f"{'='*60}")
    print(f"🔑 Tetikleyici: {', '.join(found_keywords)}")
    print(f"📌 Başlık: {submission.title}")
    print(f"📍 Subreddit: r/{submission.subreddit.display_name}")
    print(f"👍 Upvote: {submission.score} | 💬 Yorum: {submission.num_comments}")
    print(f"🔗 Link: https://www.reddit.com{submission.permalink}")
    
    # İçeriğin ilk 200 karakterini göster (varsa)
    if submission.selftext:
        preview = submission.selftext[:200].replace('\n', ' ')
        if len(submission.selftext) > 200:
            preview += "..."
        print(f"📝 Önizleme: {preview}")
    
    print(f"{'='*60}")


def scan_reddit(stream_mode=False):
    """
    Reddit'i tarar ve fırsat sinyallerini yakalar.
    
    Args:
        stream_mode: True ise canlı akışı dinler (sürekli çalışır),
                     False ise son postları tarar ve çıkar.
    """
    print("\n" + "="*60)
    print("📡 REDDIT OPPORTUNITY RADAR v0.1")
    print("="*60)
    
    # Kimlik bilgilerini kontrol et
    if not validate_credentials():
        return
    
    print("✅ Kimlik bilgileri doğrulandı")
    
    # Reddit bağlantısını kur
    try:
        reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=REDDIT_USER_AGENT
        )
        # Bağlantıyı test et
        reddit.user.me()  # Read-only mode'da None döner, hata vermez
        print("✅ Reddit bağlantısı kuruldu")
    except Exception as e:
        print(f"❌ Reddit bağlantısı kurulamadı: {e}")
        return
    
    # Subredditleri birleştir (örn: "SaaS+Entrepreneur+...")
    subreddit_query = "+".join(TARGET_SUBREDDITS)
    subreddit = reddit.subreddit(subreddit_query)
    
    print(f"🎯 Hedef Subredditler: {', '.join(TARGET_SUBREDDITS)}")
    print(f"🔍 Anahtar Kelime Sayısı: {len(KEYWORDS)}")
    print(f"📊 Mod: {'Canlı Akış (Stream)' if stream_mode else 'Anlık Tarama'}")
    print("-" * 60)
    
    found_count = 0
    
    try:
        if stream_mode:
            # Canlı akış modu - sürekli dinler
            print("📡 Canlı akış başlatıldı... (Durdurmak için Ctrl+C)")
            for submission in subreddit.stream.submissions(skip_existing=True):
                full_text = (submission.title + " " + submission.selftext).lower()
                found_keywords = [kw for kw in KEYWORDS if kw in full_text]
                
                if found_keywords:
                    found_count += 1
                    format_post(submission, found_keywords)
        else:
            # Anlık tarama modu - son 100 postu tarar
            print("🔄 Son postlar taranıyor...")
            for submission in subreddit.new(limit=100):
                full_text = (submission.title + " " + submission.selftext).lower()
                found_keywords = [kw for kw in KEYWORDS if kw in full_text]
                
                if found_keywords:
                    found_count += 1
                    format_post(submission, found_keywords)
            
            print(f"\n📊 Tarama Tamamlandı!")
            print(f"   Taranan post sayısı: 100")
            print(f"   Bulunan fırsat sayısı: {found_count}")
                
    except KeyboardInterrupt:
        print(f"\n\n⏹️ Tarama durduruldu.")
        print(f"   Toplam bulunan fırsat: {found_count}")
    except Exception as e:
        print(f"\n❌ Hata oluştu: {e}")


def main():
    """Ana fonksiyon - kullanıcıya mod seçimi sunar."""
    print("\n" + "="*60)
    print("🚀 REDDIT OPPORTUNITY RADAR")
    print("   Para kazandıracak fırsatları Reddit'te yakala!")
    print("="*60)
    
    print("\nMod Seçimi:")
    print("  [1] Anlık Tarama - Son 100 postu tara ve çık")
    print("  [2] Canlı Akış - Yeni postları sürekli dinle")
    print("  [Q] Çıkış")
    
    choice = input("\nSeçimin (1/2/Q): ").strip().lower()
    
    if choice == '1':
        scan_reddit(stream_mode=False)
    elif choice == '2':
        scan_reddit(stream_mode=True)
    elif choice == 'q':
        print("👋 Görüşürüz!")
    else:
        print("❌ Geçersiz seçim. Varsayılan olarak anlık tarama yapılıyor...")
        scan_reddit(stream_mode=False)


if __name__ == "__main__":
    main()
