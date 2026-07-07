"""
GestureClassifier: El landmark'larından (parmak pozisyonlarından) anlamlı
gesture isimleri üretir (Pinch, Fist, OpenPalm, Victory, ThumbUp...).

Bu katman SADECE "şu an hangi gesture yapılıyor" sorusuna cevap verir.
Debounce/cooldown mantığı (gesture_filter.py) ve komut çalıştırma
(controllers/) tamamen ayrı katmanlardır — bu ayrım sayesinde yeni bir
gesture eklemek istediğinde sadece bu dosyayı değiştirmen yeterli olur.
"""
import math
import sys
import os
from dataclasses import dataclass
from typing import List, Tuple

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

# ---- MediaPipe'in 21 el noktası indeksleri (referans için) ----
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

# ERİŞİLEBİLİRLİK: Bu değer artık config.py'de - kullanıcının el esnekliğine/
# hareket aralığına göre kolayca ayarlanabilsin diye.
PINCH_RATIO_THRESHOLD = config.PINCH_RATIO_THRESHOLD


@dataclass
class GestureResult:
    name: str          # "Pinch", "MiddlePinch", "Fist", "OpenPalm", "Victory", "ThumbUp", "None"
    confidence: float  # 0.0 - 1.0 arası kaba bir güven skoru


def _distance(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def _hand_size(landmarks) -> float:
    """
    Elin kabaca 'referans boyu'. Kamera uzaklığı değiştikçe mutlak piksel
    mesafeleri değişir; bunun yerine bu referansa oranlayarak mesafe
    hesapladığımızda kullanıcı elini kameraya yaklaştırıp uzaklaştırsa da
    pinch algılama tutarlı çalışır.
    """
    return _distance(landmarks[WRIST], landmarks[MIDDLE_MCP]) or 1e-6


def _finger_up(landmarks, tip_idx: int, pip_idx: int) -> bool:
    """Parmak ucu, orta eklemden daha yukarıdaysa (normalize y küçükse) parmak açık sayılır."""
    return landmarks[tip_idx][1] < landmarks[pip_idx][1]


def _thumb_up(landmarks, label: str) -> bool:
    """
    Başparmak dikey değil yanal hareket ettiği için diğer parmaklardan
    farklı kontrol edilir. `label`, MediaPipe'in verdiği 'Left'/'Right'
    etiketidir (görüntü flip edildiği için yönler buna göre ters çevrilir).
    """
    tip_x = landmarks[THUMB_TIP][0]
    ip_x = landmarks[THUMB_IP][0]
    if label == "Right":
        return tip_x < ip_x
    return tip_x > ip_x


def fingers_up(landmarks, label: str) -> List[bool]:
    """[thumb, index, middle, ring, pinky] -> her biri açık mı (True) kapalı mı (False)."""
    return [
        _thumb_up(landmarks, label),
        _finger_up(landmarks, INDEX_TIP, INDEX_PIP),
        _finger_up(landmarks, MIDDLE_TIP, MIDDLE_PIP),
        _finger_up(landmarks, RING_TIP, RING_PIP),
        _finger_up(landmarks, PINKY_TIP, PINKY_PIP),
    ]


def cursor_point_px(landmarks_px):
    """
    Fare imleci için parmak UCU yerine daha STABİL bir referans nokta döndürür.

    Neden gerekli? İşaret parmağının ucu (INDEX_TIP), pinch gesture'ı sırasında
    doğal olarak kayar - çünkü başparmakla birleşirken zaten hareket ediyor.
    Bu da tam tıklama anında imlecin, kullanıcının asıl hedeflediği noktadan
    kaymasına sebep olur (özellikle motor kontrolü kısıtlı kullanıcılar için
    ciddi bir kullanılabilirlik sorunu). Bunun yerine, pinch'ten çok daha az
    etkilenen işaret + orta parmak eklem (MCP - avuca yakın eklem) noktalarının
    ortalamasını kullanıyoruz; bu nokta parmaklar birleşirken neredeyse sabit kalır.

    landmarks_px: HandResult.landmarks_px (piksel koordinatları, smoothed)
    """
    ix, iy = landmarks_px[INDEX_MCP]
    mx, my = landmarks_px[MIDDLE_MCP]
    return (ix + mx) // 2, (iy + my) // 2


def is_lock_pinch_gesture(landmarks, label: str) -> bool:
    """
    Sağ elde başparmak + işaret parmağı (serçe) birbirine değdirilince kilit
    toggle'ı için kullanılır. Sol tık da aynı pinch'i kullanır; fark, kilit
    için pozun config.LOCK_GESTURE_HOLD_MS kadar tutulmasıdır (engine.py).
    """
    if label != "Right":
        return False

    size = _hand_size(landmarks)
    pinch_dist = _distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) / size
    return pinch_dist < config.LOCK_PINCH_THRESHOLD


def classify(landmarks, label: str) -> GestureResult:
    """
    landmarks: normalize edilmiş (0-1 aralığında) landmark listesi
               (HandResult.landmarks - piksel değil!)
    label: "Left" / "Right"
    """
    size = _hand_size(landmarks)
    thumb, index, middle, ring, pinky = fingers_up(landmarks, label)

    pinch_dist = _distance(landmarks[THUMB_TIP], landmarks[INDEX_TIP]) / size
    middle_pinch_dist = _distance(landmarks[THUMB_TIP], landmarks[MIDDLE_TIP]) / size

    # Sıralama önemli: en spesifik/öncelikli gesture'lar önce kontrol edilmeli.
    # KRİTİK FIX: Çoğu insanın parmakları tam bağımsız çalışmaz - başparmakla
    # orta parmağı birleştirmeye çalışırken (MiddlePinch/sağ tık) işaret
    # parmağı da doğal olarak başparmağa yaklaşır. Bu yüzden ikisi de aynı
    # anda eşiğin altına düşebiliyor. Sadece "önce MiddlePinch'i kontrol et"
    # sırası, frame'den frame'e hangisinin biraz daha yakın olduğuna göre
    # iki gesture arasında ÇIRPINMAYA (flicker) sebep oluyordu - bu da sağ
    # tık sırasında imlecin/tetiklemenin "tam olmaması" hissini yaratıyordu.
    # Çözüm: ikisi de eşiğin altındaysa, HANGİSİ DAHA YAKINSA (daha net/kararlı
    # olan) onu seç.
    middle_pinch_active = middle_pinch_dist < PINCH_RATIO_THRESHOLD
    pinch_active = pinch_dist < PINCH_RATIO_THRESHOLD

    if middle_pinch_active and (not pinch_active or middle_pinch_dist <= pinch_dist):
        return GestureResult("MiddlePinch", round(1.0 - middle_pinch_dist, 2))

    if pinch_active:
        return GestureResult("Pinch", round(1.0 - pinch_dist, 2))

    if not any([index, middle, ring, pinky]):
        return GestureResult("Fist", 0.9)

    if all([index, middle, ring, pinky]):
        return GestureResult("OpenPalm", 0.9)

    if index and middle and not ring and not pinky:
        return GestureResult("Victory", 0.85)

    if thumb and not any([index, middle, ring, pinky]):
        return GestureResult("ThumbUp", 0.8)

    return GestureResult("None", 0.0)