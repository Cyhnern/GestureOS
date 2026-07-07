"""
MouseController: pyautogui ile gerçek fare kontrolü yapar.

Tasarım notları:
- pyautogui.PAUSE=0 yapıyoruz çünkü varsayılan her çağrı sonrası 0.1sn
  bekliyor; bu gerçek zamanlı gesture kontrolünde gözle görülür bir
  gecikmeye sebep olur.
- pyautogui.FAILSAFE=True BİLİNÇLİ olarak açık bırakılıyor: fareyi
  ekranın sol üst köşesine (0,0) götürürsen pyautogui bir exception
  fırlatıp durur. Bu, gesture algılama çıldırıp fareyi kontrolden
  çıkardığında elle acil durdurma imkanı sağlar. KAPATMA.
"""
import pyautogui
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger

logger = get_logger("MouseController")

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True

SCREEN_W, SCREEN_H = pyautogui.size()

# ERİŞİLEBİLİRLİK: Bu değerler artık config.py'de tutuluyor, tek yerden
# ayarlanabilsinler diye (kullanıcının hareket aralığına/titremesine göre
# ince ayar yapmak gerekebilir).
MARGIN_RATIO = config.MOUSE_MARGIN_RATIO
CURSOR_SMOOTHING = config.MOUSE_CURSOR_SMOOTHING
DEAD_ZONE_PX = config.MOUSE_DEAD_ZONE_PX
EDGE_SNAP_RATIO = config.MOUSE_EDGE_SNAP_RATIO


class MouseController:
    def __init__(self, frame_width: int, frame_height: int):
        self.frame_w = frame_width
        self.frame_h = frame_height
        self._dragging = False
        self._smooth_x = None
        self._smooth_y = None

    def _map_to_screen(self, x_px: int, y_px: int):
        margin_x = self.frame_w * MARGIN_RATIO
        margin_y = self.frame_h * MARGIN_RATIO

        usable_w = self.frame_w - 2 * margin_x
        usable_h = self.frame_h - 2 * margin_y

        rel_x = (x_px - margin_x) / usable_w
        rel_y = (y_px - margin_y) / usable_h

        rel_x = min(max(rel_x, 0.0), 1.0)
        rel_y = min(max(rel_y, 0.0), 1.0)

        # Kenar snap: el frame'in uçlarına yaklaştığında smoothing beklemeden
        # ekranın kenarına yapış (kenara ulaşamama sorununu çözer).
     #   if rel_x >= EDGE_SNAP_RATIO:
        #    rel_x = 1.0
       # elif rel_x <= (1.0 - EDGE_SNAP_RATIO):
        #    rel_x = 0.0
       # if rel_y >= EDGE_SNAP_RATIO:
        #    rel_y = 1.0
       # elif rel_y <= (1.0 - EDGE_SNAP_RATIO):
      #      rel_y = 0.0

        screen_x = int(rel_x * (SCREEN_W - 1))
        screen_y = int(rel_y * (SCREEN_H - 1))

        # PyAutoGUI'nin fail-safe'i tam (0,0) gibi köşe piksellerinde tetiklenir.
        # Normal kullanımda (elin frame kenarına gelmesiyle) buraya yanlışlıkla
        # düşmemesi için birkaç piksel içeri çekiyoruz.
        screen_x = min(max(screen_x, 2), SCREEN_W - 3)
        screen_y = min(max(screen_y, 2), SCREEN_H - 3)

        return screen_x, screen_y

    def move_to(self, x_px: int, y_px: int):
        screen_x, screen_y = self._map_to_screen(x_px, y_px)

        # İlk çağrıda smoothing state'i başlat
        if self._smooth_x is None:
            self._smooth_x, self._smooth_y = screen_x, screen_y

        # Üstel hareketli ortalama (exponential moving average): yeni konum,
        # eski konumla yeni ölçüm arasında bir yerde olur. Bu ani sıçramaları
        # yumuşatır ama sürekli aynı yöne hareket edildiğinde gecikme yaratmaz.
        new_x = self._smooth_x + (screen_x - self._smooth_x) * CURSOR_SMOOTHING
        new_y = self._smooth_y + (screen_y - self._smooth_y) * CURSOR_SMOOTHING

        # Ölü bölge: çok küçük değişimleri tamamen yok say (elin doğal titremesi)
        if abs(new_x - self._smooth_x) < DEAD_ZONE_PX and abs(new_y - self._smooth_y) < DEAD_ZONE_PX:
            return

        self._smooth_x, self._smooth_y = new_x, new_y

        try:
            pyautogui.moveTo(int(new_x), int(new_y), duration=0)
        except pyautogui.FailSafeException:
            logger.warning("Fail-safe tetiklendi (fare ekranın köşesine gitti).")

    def left_click(self):
        try:
            pyautogui.click(button="left")
            logger.info("Sol tık tetiklendi")
        except pyautogui.FailSafeException:
            logger.warning("Fail-safe tetiklendi, sol tık iptal edildi.")

    def double_click(self):
        try:
            pyautogui.doubleClick()
            logger.info("Çift tık tetiklendi")
        except pyautogui.FailSafeException:
            logger.warning("Fail-safe tetiklendi, çift tık iptal edildi.")

    def right_click(self):
        try:
            pyautogui.click(button="right")
            logger.info("Sağ tık tetiklendi")
        except pyautogui.FailSafeException:
            logger.warning("Fail-safe tetiklendi, sağ tık iptal edildi.")

    def start_drag(self):
        if not self._dragging:
            try:
                pyautogui.mouseDown(button="left")
                self._dragging = True
                logger.info("Sürükleme (drag) başladı")
            except pyautogui.FailSafeException:
                logger.warning("Fail-safe tetiklendi, sürükleme başlatılamadı.")

    def stop_drag(self):
        if self._dragging:
            try:
                pyautogui.mouseUp(button="left")
                logger.info("Sürükleme (drag) bitti")
            except pyautogui.FailSafeException:
                logger.warning("Fail-safe tetiklendi (mouseUp sırasında).")
            finally:
                # Fail-safe patlasa bile "dragging" durumunda takılı kalmamalı,
                # yoksa program sürükleme moduna kilitlenmiş gibi davranır.
                self._dragging = False