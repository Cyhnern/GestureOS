# GestureOS - Elle Bilgisayar Kontrolü

Kamera üzerinden el hareketlerini algılayıp bilgisayarı **dokunmadan**
kontrol etmeyi sağlayan bir masaüstü uygulaması. MediaPipe ile el/parmak
takibi yapılır, algılanan pozlar (gesture) fare veya klavye/medya
komutlarına çevrilir.

## Neler Yapabiliyor?

- **Sağ el → Fare kontrolü**
  - El hareketiyle imleç sürme
  - İşaret+başparmak pinch → sol tık (kısa tut-bırak) / kilit aç-kapat (uzun tutma)
  - Orta parmak+başparmak pinch → sağ tık
  - Yumruk (Fist) → sürükle (drag)
  - 🔒 Kilit: mouse kontrolünü tamamen dondurup (yanlışlıkla tıklamayı önlemek için) açıp kapatma

- **Sol el → Profile bağlı komutlar** (ses, medya, klavye kısayolları, kaydırma)
  - Aynı gesture seti (Pinch, MiddlePinch, Fist, OpenPalm, Victory, ThumbUp)
    kullanılıyor, ama sağ elden farklı olarak **hangi gesture'ın hangi
    komutu tetikleyeceği aktif profile göre değişiyor**
  - 5 hazır profil: **Office, Gaming, Presentation, Editing, Browser**
  - Profil, arayüzdeki menüden anında (uygulamayı yeniden başlatmadan) değiştirilebilir
  - Sadece **avuç içi kameraya dönükken** tetiklenir — el sırtı gösterildiğinde
    (bilekten çevrildiğinde) yanlışlıkla komut tetiklenmesini önlemek için
    ayrı bir kontrol vardır

- **Erişilebilirliğe özel tasarım kararları**
  - İstemsiz titreme/hareketleri yutan yumuşatma (smoothing) ve ölü bölge (dead zone)
  - Bir gesture'ın "kararlı" sayılması için bekleme süresi (debounce) + tekrar
    tetiklenmeyi sınırlayan bekleme (cooldown) — istemsiz/yarım pozların
    yanlışlıkla komut tetiklemesini engeller
  - El kısa süreliğine kameradan çıkarsa imleç sıçramaz, yerinde kalır
  - Pencere odakta olmasa bile (başka bir uygulamaya geçilmiş olsa) el
    algılama ve komutlar kesintisiz çalışmaya devam eder (arka plan thread'i)

## Kurulum (Windows)

> **Önemli — Python sürümü:** MediaPipe, Python 3.13/3.12 ile güvenilir
> çalışmıyor. **Python 3.11** kullanman gerekiyor. Kurulu değilse
> [python.org](https://www.python.org/downloads/release/python-3119/)'dan indir.

```bash
# Proje klasörüne gir
cd GestureOS

# Python 3.11 ile sanal ortam oluştur
py -3.11 -m venv venv
venv\Scripts\activate

# Bağımlılıkları kur
pip install -r requirements.txt

# MediaPipe'i, "solutions" API'sinin (bu projenin kullandığı) hâlâ var
# olduğu sürüme sabitle - daha yeni sürümler bu API'yi kaldırdı
pip install mediapipe==0.10.14
```

## Çalıştırma

```bash
python main.py
```

Uygulama açıldığında:
- Sol tarafta kamera görüntüsü ve üzerinde çizilen el iskeleti görünür
- Sağ tarafta FPS, algılanan el sayısı, sağ/sol el güven oranı ve gesture
  isimleri gösterilir
- **"Aktif Profil (Sol El)"** menüsünden sol elin komut setini değiştirebilirsin
- `Q` tuşuna basarak veya "Kapat" butonuyla kapatabilirsin

## Profilleri Özelleştirme

Sol elin hangi gesture'da hangi komutu çalıştıracağı `data/profiles.json`
dosyasında tutulur. Kod tarafına dokunmadan, bu dosyayı düzenleyerek
eşlemeleri değiştirebilirsin:

```json
{
  "Office": {
    "Pinch": "volume_down",
    "MiddlePinch": "volume_up",
    "Fist": "mute",
    "OpenPalm": "play_pause",
    "Victory": "alt_tab",
    "ThumbUp": "escape"
  }
}
```

Kullanılabilir aksiyon isimleri (`controllers/keyboard.py` içindeki
metodlarla birebir eşleşir): `volume_up`, `volume_down`, `mute`,
`play_pause`, `next_track`, `prev_track`, `alt_tab`, `escape`, `next_tab`,
`prev_tab`, `next_slide`, `prev_slide`, `undo`, `redo`, `scroll_up`,
`scroll_down`.

Yeni bir profil eklemek istersen `data/profiles.json`'a yeni bir profil
adı + eşleme ekleyip Dashboard'daki menüde otomatik olarak görünmesini
sağlayabilirsin (kod değişikliği gerekmez).

## Olası Sorunlar

- **"Kamera açılamadı" hatası**: Başka bir uygulama (Zoom, Teams, Discord vs.)
  kamerayı kullanıyor olabilir. Onu kapat ya da `config.py` içindeki
  `CAMERA_INDEX` değerini `1` yaparak dene.
- **`AttributeError: module 'mediapipe' has no attribute 'solutions'`**:
  MediaPipe'in çok yeni bir sürümü kurulmuş demektir (yeni sürümler eski
  "Solutions" API'sini kaldırdı). `pip install mediapipe==0.10.14` ile
  düzelt.
- **Düşük FPS**: `config.py` içinde `MODEL_COMPLEXITY = 0` yaparak veya
  `FRAME_WIDTH`/`FRAME_HEIGHT` değerlerini düşürerek performansı artırabilirsin.
- **Sol el gesture'ları tetiklenmiyor**: `data/profiles.json` dosyasının
  gerçekten `data/` klasörünün içinde olduğundan emin ol; `gestureos.log`
  dosyasında `"Profiller yüklendi: ..."` satırını görmelisin.
- **customtkinter ile ilgili görsel bozukluklar**: `pip install --upgrade customtkinter` deneyin.

## Proje Yapısı

```
GestureOS/
├── main.py                    # Giriş noktası - engine ile dashboard'u birbirine bağlar
├── engine.py                  # Kamera + algılama + sınıflandırma + kontrol (arka plan thread'i)
├── config.py                  # Tüm ayarlar tek yerde
├── requirements.txt
│
├── detector/
│   ├── camera.py               # Threaded kamera okuma
│   ├── hand_detector.py        # MediaPipe wrapper
│   └── landmark_tracker.py     # Landmark smoothing (moving average)
│
├── gestures/
│   ├── classifier.py           # Landmark'lardan gesture ismi üretir (Pinch, Fist, ThumbUp...)
│   ├── gesture_filter.py       # Debounce/cooldown (kararlılık kontrolü)
│   └── profile_manager.py      # Sol el: aktif profile göre gesture->aksiyon eşlemesi
│
├── controllers/
│   ├── mouse.py                 # Sağ el: gerçek fare kontrolü (pyautogui)
│   └── keyboard.py              # Sol el: ses/medya/klavye kısayolları (pyautogui)
│
├── gui/
│   └── dashboard.py             # CustomTkinter arayüzü + profil menüsü
│
├── data/
│   ├── profiles.json            # Profil bazlı sol el gesture->aksiyon eşlemeleri
│   └── gestures.json            # (legacy, artık kullanılmıyor)
│
└── utils/
    └── logger.py                # Merkezi log sistemi
```

## Gesture Referansı

**Sağ El (Fare — sabit, profilden bağımsız)**

| Gesture | Aksiyon |
|---|---|
| İşaret+başparmak pinch (kısa) | Sol tık |
| İşaret+başparmak pinch (700ms+ tutma) | 🔒 Kilit aç/kapat |
| Orta parmak+başparmak pinch | Sağ tık |
| Yumruk (Fist) | Sürükle (drag) |
| El açık, hareket | İmleç hareketi |

**Sol El (profile göre değişir — varsayılan eşlemeler)**

| Gesture | Office | Gaming | Presentation | Editing | Browser |
|---|---|---|---|---|---|
| Pinch | Ses azalt | Ses azalt | Önceki slayt | Geri al | Aşağı kaydır |
| MiddlePinch | Ses artır | Ses artır | Sonraki slayt | Yinele | Yukarı kaydır |
| Fist | Sessiz | Sessiz | Esc | Esc | Sessiz |
| OpenPalm | Play/Pause | Esc | Play/Pause | Alt+Tab | Alt+Tab |
| Victory | Alt+Tab | Alt+Tab | Alt+Tab | Aşağı kaydır | Sonraki sekme |
| ThumbUp | Esc | Play/Pause | Sessiz | Yukarı kaydır | Esc |
