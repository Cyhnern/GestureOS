"""
GestureFilter: Ham gesture sonuçlarını "kararlı" hale getirir.

İki farklı problemi çözer:

1. TİTREME/GÜRÜLTÜ: Tek bir frame'de yanlışlıkla algılanan bir gesture
   hemen bir komut tetiklemesin. Bunun için bir gesture'ın GESTURE_DEBOUNCE_MS
   kadar süre aynı kalması (yani "kararlı" olması) beklenir.

2. SPAM: Kullanıcı elini "Pinch" pozisyonunda tutmaya devam ederse, komut
   saniyede onlarca kez tetiklenmemeli (yoksa 1 tık yerine 50 tık gider).
   Bunun için GESTURE_COOLDOWN_MS kadar bekleme süresi uygulanır.

Bu iki değer config.py içinde ayarlanabilir.
"""
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class GestureFilter:
    def __init__(self):
        # label -> (gesture_name, bu_gesture_ilk_ne_zaman_görüldü)
        self._pending = {}
        # (label, gesture_name) -> en son ne zaman tetiklendi
        self._last_triggered = {}

    def update(self, label: str, gesture_name: str) -> bool:
        """
        Bu frame'de, bu el için bu gesture'ın komutu TETİKLEMESİ gerekip
        gerekmediğini döndürür. True dönerse controller katmanı komutu
        BİR KEZ çalıştırmalı (ör. tek bir sol tık).
        """
        now = time.time() * 1000  # ms cinsinden

        if gesture_name in ("None", None):
            self._pending.pop(label, None)
            return False

        pending_name, first_seen = self._pending.get(label, (None, now))

        if pending_name != gesture_name:
            # Yeni bir gesture görülmeye başlandı, kararlılık sayacını sıfırla
            self._pending[label] = (gesture_name, now)
            return False

        stable_duration = now - first_seen
        if stable_duration < config.GESTURE_DEBOUNCE_MS:
            return False  # Henüz yeterince kararlı değil, bekle

        key = (label, gesture_name)
        last_time = self._last_triggered.get(key, 0)
        if now - last_time < config.GESTURE_COOLDOWN_MS:
            return False  # Cooldown süresinde, tekrar tetikleme

        self._last_triggered[key] = now
        return True

    def reset(self, label: str = None):
        """Bir elin (ya da tüm ellerin) durumu sıfırlanır (örn. el kaybolduğunda)."""
        if label:
            self._pending.pop(label, None)
        else:
            self._pending.clear()
            self._last_triggered.clear()
