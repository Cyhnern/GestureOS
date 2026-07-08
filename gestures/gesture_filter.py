"""
GestureFilter: Ham gesture sonuçlarını "kararlı" hale getirir.

İki farklı problemi çözer:

1. TİTREME/GÜRÜLTÜ: Tek bir frame'de yanlışlıkla algılanan bir gesture
   hemen bir komut tetiklemesin. Bunun için bir gesture'ın GESTURE_DEBOUNCE_MS
   kadar süre aynı kalması (yani "kararlı" olması) beklenir.

2. TEKRARLI TETİKLENME: Kullanıcı elini bir pozda (ör. OpenPalm) tutmaya
   devam ederse, komut sadece BİR KEZ tetiklenmeli - poz tutulduğu sürece
   tekrar tekrar değil. Bu özellikle mute/play-pause gibi TOGGLE komutlar
   için kritik: eskiden GESTURE_COOLDOWN_MS'de bir tekrar tetikleniyordu,
   bu da poz birkaç saniye tutulduğunda sesin hızlıca açılıp kapanması gibi
   istenmeyen bir davranışa yol açıyordu. Artık aynı poz aynı elde
   tutulduğu sürece sadece bir kez tetiklenir; yeniden tetiklenebilmesi için
   kullanıcının pozu BIRAKIP (None ya da farklı bir gesture) tekrar
   yapması gerekir.

Bu değerler config.py içinde ayarlanabilir.
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
        # (label, gesture_name) -> bu "tutma" sırasında zaten tetiklendi mi
        self._fired_this_hold = set()

    def update(self, label: str, gesture_name: str) -> bool:
        """
        Bu frame'de, bu el için bu gesture'ın komutu TETİKLEMESİ gerekip
        gerekmediğini döndürür. True dönerse controller katmanı komutu
        BİR KEZ çalıştırmalı (ör. tek bir mute komutu). Poz bırakılıp
        tekrar yapılmadan aynı gesture bir daha True döndürmez.
        """
        now = time.time() * 1000  # ms cinsinden

        if gesture_name in ("None", None):
            self._pending.pop(label, None)
            self._forget_fired(label)
            return False

        pending_name, first_seen = self._pending.get(label, (None, now))

        if pending_name != gesture_name:
            # Yeni bir gesture görülmeye başlandı (ya da eskisi bırakılıp
            # tekrar yapıldı) - kararlılık sayacını sıfırla ve bu elin
            # daha önce "tetiklendi" işaretlerini temizle, böylece aynı
            # poz tekrar yapıldığında yeniden tetiklenebilir.
            self._pending[label] = (gesture_name, now)
            self._forget_fired(label)
            return False

        stable_duration = now - first_seen
        if stable_duration < config.GESTURE_DEBOUNCE_MS:
            return False  # Henüz yeterince kararlı değil, bekle

        key = (label, gesture_name)
        if key in self._fired_this_hold:
            return False  # Bu poz bu tutma boyunca zaten bir kez tetiklendi

        self._fired_this_hold.add(key)
        return True

    def _forget_fired(self, label: str):
        self._fired_this_hold = {
            key for key in self._fired_this_hold if key[0] != label
        }

    def reset(self, label: str = None):
        """Bir elin (ya da tüm ellerin) durumu sıfırlanır (örn. el kaybolduğunda)."""
        if label:
            self._pending.pop(label, None)
            self._forget_fired(label)
        else:
            self._pending.clear()
            self._fired_this_hold.clear()