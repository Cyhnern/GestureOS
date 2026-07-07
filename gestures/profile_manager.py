"""
ProfileManager: Aktif profile göre "sol el gesture -> aksiyon" eşlemesini
yönetir.

Profiller data/profiles.json içinde tutulur. Her profil, GestureClassifier'ın
ürettiği gesture isimlerini (Pinch, MiddlePinch, Fist, OpenPalm, Victory,
ThumbUp) bir aksiyon string'ine eşler. Bu aksiyon string'leri
controllers/keyboard.py içindeki metod adlarıyla BİREBİR aynı olmalıdır -
engine.py bu ismi doğrudan getattr(keyboard_controller, action_name) ile
çağrılabilir bir metoda çevirir.

Thread-safety notu: Kullanıcı Dashboard'daki profil menüsünden seçim
yaptığında bu GUI thread'inden çağrılır (set_active), engine ise kendi arka
plan thread'inde sürekli get_action ile okur. İkisi aynı anda olabileceği
için basit bir kilit (Lock) ile korunuyor.
"""
import json
import os
import sys
import threading

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_THIS_DIR)
sys.path.append(_PROJECT_ROOT)

from utils.logger import get_logger

logger = get_logger("ProfileManager")

DEFAULT_PROFILES_PATH = os.path.join(_PROJECT_ROOT, "data", "profiles.json")


class ProfileManager:
    def __init__(self, path: str = DEFAULT_PROFILES_PATH, default: str = "Office"):
        self._lock = threading.Lock()
        self._profiles = self._load(path)

        if default in self._profiles:
            self._active = default
        elif self._profiles:
            # Varsayılan profil dosyada yoksa (ör. kullanıcı profiles.json'ı
            # elle düzenlemiş), sessizce çökmek yerine ilk profili kullan.
            self._active = next(iter(self._profiles))
            logger.warning(
                "Varsayılan profil '%s' bulunamadı, '%s' kullanılıyor.",
                default, self._active,
            )
        else:
            self._active = None
            logger.error("Hiç profil yüklenemedi - sol el aksiyonları devre dışı kalacak.")

    def _load(self, path: str) -> dict:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info("Profiller yüklendi: %s", ", ".join(data.keys()))
            return data
        except (OSError, json.JSONDecodeError) as e:
            logger.error("Profiller yüklenemedi (%s): %s", path, e)
            return {}

    def set_active(self, name: str) -> bool:
        with self._lock:
            if name not in self._profiles:
                logger.warning("Bilinmeyen profil seçilmeye çalışıldı: %s", name)
                return False
            self._active = name
            logger.info("Aktif profil değişti: %s", name)
            return True

    def get_active(self) -> str:
        with self._lock:
            return self._active

    def get_action(self, gesture_name: str):
        """
        Verilen gesture ismi için aktif profildeki aksiyon string'ini döndürür.
        Eşleme yoksa None döner (engine.py bu durumda hiçbir şey tetiklemez).
        """
        with self._lock:
            if self._active is None:
                return None
            return self._profiles.get(self._active, {}).get(gesture_name)

    def profile_names(self):
        return list(self._profiles.keys())
