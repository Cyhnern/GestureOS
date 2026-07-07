"""
Camera modülü.

Neden ayrı thread'de okuma yapıyoruz?
cv2.VideoCapture.read() bloklayan (blocking) bir çağrıdır. Eğer bunu ana
thread'de (GUI ile aynı yerde) çağırırsak, kamera her frame beklediğinde
arayüz donar. Bu yüzden kamera okuma işini arka planda sürekli çalışan
bir thread'e veriyoruz; GUI/işleme tarafı sadece "en son hazır frame'i"
alır. Bu pattern'e genelde "threaded video stream" denir.
"""
import cv2
import threading
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger

logger = get_logger("Camera")


class Camera:
    def __init__(self, index: int = config.CAMERA_INDEX):
        self.index = index
        self.cap = None
        self.frame = None
        self.ret = False
        self.running = False
        self.lock = threading.Lock()
        self.thread = None

        # Basit FPS ölçümü
        self._fps = 0.0
        self._last_time = time.time()

    def start(self):
        self.cap = cv2.VideoCapture(self.index, cv2.CAP_DSHOW)  # Windows'ta CAP_DSHOW daha hızlı açılır
        if not self.cap.isOpened():
            logger.error(f"Kamera açılamadı (index={self.index}).")
            raise RuntimeError(
                f"Kamera açılamadı (index={self.index}). "
                f"Başka bir uygulama kamerayı kullanıyor olabilir ya da "
                f"config.CAMERA_INDEX değerini değiştirmen gerekebilir."
            )

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.TARGET_FPS)

        self.running = True
        self.thread = threading.Thread(target=self._update_loop, daemon=True)
        self.thread.start()
        logger.info(f"Kamera başlatıldı (index={self.index}).")
        return self

    def _update_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Frame okunamadı, tekrar deneniyor...")
                time.sleep(0.05)
                continue

            if config.FLIP_HORIZONTAL:
                frame = cv2.flip(frame, 1)

            # FPS hesapla
            now = time.time()
            elapsed = now - self._last_time
            self._last_time = now
            if elapsed > 0:
                instant_fps = 1.0 / elapsed
                # Küçük bir smoothing (ani sıçramaları engelle)
                self._fps = self._fps * 0.9 + instant_fps * 0.1

            with self.lock:
                self.frame = frame
                self.ret = ret

    def read(self):
        """En son hazır frame'i döndürür. (ret, frame)"""
        with self.lock:
            if self.frame is None:
                return False, None
            return self.ret, self.frame.copy()

    def get_fps(self) -> float:
        return round(self._fps, 1)

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        if self.cap is not None:
            self.cap.release()
        logger.info("Kamera durduruldu.")
