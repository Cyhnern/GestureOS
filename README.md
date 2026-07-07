# GestureOS - MVP (Kamera + El Algılama İskeleti)

Bu, GestureOS projesinin ilk çalışan çekirdeğidir. Şu an yaptığı:

- Kamerayı ayrı bir thread'de okur (gecikmeyi azaltmak için)
- MediaPipe ile el(ler)i algılar ve landmark'ları ekranda çizer
- CustomTkinter arayüzünde canlı video + FPS + güven oranı gösterir

Henüz **gesture -> komut** dönüşümü (mouse, ses, klavye vs.) yok.
Bu, bir sonraki aşamada `gestures/classifier.py` ve `controllers/` katmanlarıyla eklenecek.

## Kurulum (Windows)

```bash
# Proje klasörüne gir
cd GestureOS

# (Önerilir) Sanal ortam oluştur
python -m venv venv
venv\Scripts\activate

# Bağımlılıkları kur
pip install -r requirements.txt
```

## Çalıştırma

```bash
python main.py
```

Uygulama açıldığında:
- Sol tarafta kamera görüntüsü ve üzerinde çizilen el iskeleti (landmark'lar) görünür
- Sağ tarafta FPS, algılanan el sayısı, sol/sağ el güven oranı gösterilir
- `Q` tuşuna basarak veya "Kapat" butonuyla kapatabilirsin

## Olası Sorunlar

- **"Kamera açılamadı" hatası**: Başka bir uygulama (Zoom, Teams, Discord vs.)
  kamerayı kullanıyor olabilir. Onu kapat ya da `config.py` içindeki
  `CAMERA_INDEX` değerini `1` yaparak dene.
- **Düşük FPS**: `config.py` içinde `MODEL_COMPLEXITY = 0` yaparak veya
  `FRAME_WIDTH`/`FRAME_HEIGHT` değerlerini düşürerek performansı artırabilirsin.
- **customtkinter ile ilgili görsel bozukluklar**: `pip install --upgrade customtkinter` deneyin.

## Proje Yapısı (Şu Ana Kadar Kurulanlar)

```
GestureOS/
├── main.py                    # Giriş noktası - her şeyi birbirine bağlar
├── config.py                  # Tüm ayarlar tek yerde
├── requirements.txt
│
├── detector/
│   ├── camera.py              # Threaded kamera okuma
│   ├── hand_detector.py       # MediaPipe wrapper
│   └── landmark_tracker.py    # Landmark smoothing (moving average)
│
├── gui/
│   └── dashboard.py           # CustomTkinter arayüzü
│
├── data/
│   └── gestures.json          # Gesture -> komut eşlemesi (henüz kullanılmıyor)
│
└── utils/
    └── logger.py               # Merkezi log sistemi
```

## Sonraki Adım

Bir sonraki aşamada önerilen sıralama:
1. `gestures/classifier.py` — landmark'lardan "Pinch", "Fist", "OpenPalm" gibi
   gesture'ları hesaplayan mantık (parmak uçları arası mesafe, açı hesapları)
2. `gestures/gesture_filter.py` — debounce/cooldown (config.py'de zaten
   `GESTURE_DEBOUNCE_MS` ve `GESTURE_COOLDOWN_MS` tanımlı)
3. `controllers/mouse.py` — pyautogui ile gerçek mouse hareketi/tıklama
