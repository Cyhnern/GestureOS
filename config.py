"""
GestureOS - Merkezi Yapılandırma Dosyası
Tüm sabitler burada tutulur, böylece kod içinde "magic number" olmaz.
"""

# ---------------- KAMERA AYARLARI ----------------
CAMERA_INDEX = 0            # Birden fazla kamera varsa 1, 2... deneyebilirsin
FRAME_WIDTH = 960
FRAME_HEIGHT = 540
TARGET_FPS = 60
FLIP_HORIZONTAL = True      # Ayna görüntüsü (doğal his için True kalsın)

# ---------------- MEDIAPIPE AYARLARI ----------------
MAX_NUM_HANDS = 2
DETECTION_CONFIDENCE = 0.7
TRACKING_CONFIDENCE = 0.6   # ERİŞİLEBİLİRLİK: biraz düşürüldü (0.7->0.6).
                            # El, sınırlı hareket aralığı yüzünden "ideal"
                            # poza tam giremeyebilir - eli hafif kararsız
                            # görsek bile takibi TAMAMEN kaybetmemek, sürekli
                            # kaybedip yeniden bulmaktan daha iyidir.
MODEL_COMPLEXITY = 1        # 0=hızlı/az doğru, 1=dengeli

# ---------------- SMOOTHING / FİLTRELEME ----------------
# ERİŞİLEBİLİRLİK NOTU: Bu bölümdeki tüm değerler "titreme/istemsiz hareketi
# yutma" ile "tepki hızı" arasındaki dengeyi ayarlar. Motor kontrolü kısıtlı
# kullanıcılar için dengeyi bilinçli olarak STABİLİTE tarafına kaydırdık -
# biraz daha yavaş ama çok daha öngörülebilir bir imleç, hızlı ama titrek/
# yanlışlıkla tıklayan bir imleçten çok daha kullanılabilir.
SMOOTHING_WINDOW = 8        # 5->8: landmark yumuşatma penceresi büyütüldü,
                            # istemsiz küçük titremeler daha çok bastırılıyor.
GESTURE_DEBOUNCE_MS = 400   # 200->400: bir gesture'ın "kararlı" sayılması için
                            # gereken süre uzatıldı. Kısa, istemsiz bir pinch
                            # anı artık yanlışlıkla tıklama tetiklemiyor -
                            # kullanıcının pozu GERÇEKTEN kastederek tutması gerekiyor.
GESTURE_COOLDOWN_MS = 700   # 400->700: aynı pozu tutmaya devam ederse
                            # art arda çoklu tıklama (spam-click) riski azaltıldı.

# ---------------- İMLEÇ / MOUSE AYARLARI ----------------
# Bu değerler artık burada, tek bir yerden ayarlanabilsin diye (mouse.py bunu okur).
MOUSE_MARGIN_RATIO = 0.15   # Kenarlara daha kolay ulaşmak için düşürüldü.
                            # Çok agresif olursa orta bölgede hassasiyet azalır.
MOUSE_CURSOR_SMOOTHING = 0.28  # Kenarlara ulaşmayı kolaylaştırmak için biraz
                               # artırıldı (daha hızlı tepki).
MOUSE_DEAD_ZONE_PX = 4      # Kenar hassasiyeti için biraz düşürüldü.
MOUSE_EDGE_SNAP_RATIO = 0.92  # El frame'in %92+ kenarındaysa imleç ekran
                              # kenarına yapışır (smoothing yüzünden uca
                              # ulaşamama sorununu çözer).

# ---------------- GESTURE ALGILAMA ----------------
PINCH_RATIO_THRESHOLD = 0.40  # 0.35->0.40: parmakları TAM kapatmak zor
                              # olabileceği için pinch'in tetiklenmesi biraz
                              # kolaylaştırıldı. Bu değer kişiden kişiye elin
                              # esnekliğine göre ayarlanmalı - ideal olarak
                              # kullanıcıya özel bir kalibrasyon adımı eklenebilir.

# ---------------- EL KAYBI / GRACE PERIOD ----------------
RIGHT_HAND_LOST_GRACE_MS = 15000  # Kısa algılama kayıplarında imleç yerinde kalır.
                                # Bu süreden uzun kayıp = "gerçek el kaybı".

# El kameradan çıkıp geri gelince imlecin sıçramaması için: geri geldiğinde
# el yeterince hareket edene kadar imleç sabit kalır (px cinsinden eşik).
REACQUIRE_MOVE_THRESHOLD_PX = 10

# ---------------- KİLİT (LOCK) GESTURE ----------------
# Sağ elde başparmak + işaret parmağını birbirine değdirip bu süre kadar
# tutunca mouse kontrolü kilitlenir/açılır. Kısa pinch = sol tık (normal).
LOCK_PINCH_THRESHOLD = 0.40   # Pinch eşiği (sol tık ile aynı mantık).
LOCK_GESTURE_HOLD_MS = 700    # Kilit için pinch bu kadar tutulmalı.

# ---------------- RENKLER (BGR - OpenCV formatı) ----------------
COLOR_LANDMARK = (0, 255, 170)
COLOR_CONNECTION = (255, 200, 0)
COLOR_TEXT = (255, 255, 255)
COLOR_BG_PANEL = (20, 20, 20)

# ---------------- GUI AYARLARI ----------------
APP_TITLE = "GestureOS - Kontrol Paneli"
APP_THEME = "dark"          # "dark" | "light" | "system"
APP_COLOR_THEME = "green"   # customtkinter renk teması
WINDOW_MIN_WIDTH = 1100
WINDOW_MIN_HEIGHT = 650

# ---------------- LOG AYARLARI ----------------
LOG_FILE = "gestureos.log"
LOG_LEVEL = "INFO"          # DEBUG, INFO, WARNING, ERROR

# ---------------- SOL EL / PROFİL SİSTEMİ ----------------
# Sol el artık gesture_filter.py + classifier.py üzerinden aynı şekilde
# sınıflandırılıyor, ama tetiklediği aksiyon SABİT değil - aktif profile
# (data/profiles.json) göre değişiyor. Profil, Dashboard'daki menüden
# canlı olarak değiştirilebilir.
DEFAULT_PROFILE = "Office"   # Uygulama açılışında aktif olacak profil

# pyautogui.scroll() birimi. Pozitif değer yukarı, negatif değer aşağı
# kaydırma anlamına gelir (controllers/keyboard.py bunu +/- olarak kullanır).
SCROLL_AMOUNT = 300