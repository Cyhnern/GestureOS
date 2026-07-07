"""
KeyboardController: Sol el gesture'larının tetiklediği klavye kısayolları ve
medya/ses tuşları için pyautogui sarmalayıcısı.

Tasarım notu: Ses ve medya tuşları için işletim sisteminin NATIVE sanal tuş
kodları kullanılır (ör. "volumeup", "playpause"). Bu sayede hangi pencere/
uygulama aktifken tetiklendiği önemli değildir - Windows bu tuşları global
olarak yakalar (ör. Spotify arka plandayken bile play/pause onu kontrol eder,
ses her zaman sistem geneli değişir).

mouse.py'den FARKLI olarak burada pyautogui.FAILSAFE davranışı önemli
değildir (imleç hareketi yok) ama yine de her metod try/except ile sarılıdır -
beklenmeyen bir pyautogui hatası (ör. bir tuş kombinasyonu bazı klavye
sürücülerinde desteklenmiyorsa) tüm arka plan thread'ini (engine.py)
çökertmesin diye.
"""
import functools
import pyautogui
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger

logger = get_logger("KeyboardController")


def _safe(action_name: str):
    """Ortak try/except sarmalayıcı: her metodu tekrar tekrar yazmamak için."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(self, *args, **kwargs):
            try:
                fn(self, *args, **kwargs)
                logger.info("Sol el aksiyonu tetiklendi: %s", action_name)
            except Exception:
                logger.exception("Sol el aksiyonu başarısız: %s", action_name)
        return wrapper
    return decorator


class KeyboardController:
    """
    Her metod adı, data/profiles.json içindeki aksiyon string'leriyle BİREBİR
    eşleşir (engine.py, profile_manager'dan gelen aksiyon adını
    getattr(self.keyboard, action_name) ile burada bir metoda çevirir).
    Buraya yeni bir aksiyon eklerken metod adını profiles.json'da kullandığın
    isimle aynı tutmayı unutma.
    """

    # ---- Ses ----
    @_safe("volume_up")
    def volume_up(self):
        pyautogui.press("volumeup")

    @_safe("volume_down")
    def volume_down(self):
        pyautogui.press("volumedown")

    @_safe("mute")
    def mute(self):
        pyautogui.press("volumemute")

    # ---- Medya ----
    @_safe("play_pause")
    def play_pause(self):
        pyautogui.press("playpause")

    @_safe("next_track")
    def next_track(self):
        pyautogui.press("nexttrack")

    @_safe("prev_track")
    def prev_track(self):
        pyautogui.press("prevtrack")

    # ---- Pencere / sekme gezinme ----
    @_safe("alt_tab")
    def alt_tab(self):
        pyautogui.hotkey("alt", "tab")

    @_safe("escape")
    def escape(self):
        pyautogui.press("esc")

    @_safe("next_tab")
    def next_tab(self):
        pyautogui.hotkey("ctrl", "tab")

    @_safe("prev_tab")
    def prev_tab(self):
        pyautogui.hotkey("ctrl", "shift", "tab")

    # ---- Sunum / slayt ----
    @_safe("next_slide")
    def next_slide(self):
        pyautogui.press("right")

    @_safe("prev_slide")
    def prev_slide(self):
        pyautogui.press("left")

    # ---- Düzenleme ----
    @_safe("undo")
    def undo(self):
        pyautogui.hotkey("ctrl", "z")

    @_safe("redo")
    def redo(self):
        pyautogui.hotkey("ctrl", "y")

    # ---- Kaydırma (scroll) ----
    @_safe("scroll_up")
    def scroll_up(self):
        pyautogui.scroll(config.SCROLL_AMOUNT)

    @_safe("scroll_down")
    def scroll_down(self):
        pyautogui.scroll(-config.SCROLL_AMOUNT)
