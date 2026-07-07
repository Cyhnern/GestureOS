"""
GestureOS - Giriş Noktası (v3 - Arka planda çalışabilen mimari)

Bu dosyanın TEK sorumluluğu: GestureEngine'i başlatmak ve Dashboard'u
periyodik olarak onun ürettiği en son frame/istatistiklerle güncellemek.

ÖNEMLİ: Gerçek gesture algılama, sınıflandırma ve mouse kontrolü artık
main.py'de DEĞİL, engine.py içindeki bağımsız thread'de çalışıyor. Bu
sayede pencere odakta olmasa (başka bir uygulamaya geçilmiş olsa) bile
mouse kontrolü kesintisiz devam eder - sadece görsel güncelleme (bu dosya)
Windows tarafından yavaşlatılabilir, ki bu önemli değil.
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from engine import GestureEngine
from gui.dashboard import Dashboard
from utils.logger import get_logger

logger = get_logger("Main")


class GestureOSApp:
    def __init__(self):
        self.engine = GestureEngine()
        self.dashboard = Dashboard(
            on_close_callback=self.shutdown,
            on_profile_change=self.engine.set_profile,
            profile_names=self.engine.get_profile_names(),
            active_profile=self.engine.get_active_profile(),
        )
        self._running = False

    def start(self):
        logger.info("GestureOS başlatılıyor...")
        self.engine.start()
        self._running = True
        self._refresh_gui()
        self.dashboard.mainloop()

    def _refresh_gui(self):
        if not self._running:
            return

        frame, hand_results, gesture_name, left_gesture_name, fps = self.engine.get_latest()

        if frame is not None:
            self.dashboard.update_frame(frame)
            self.dashboard.update_stats(fps, hand_results, gesture_name, left_gesture_name)

        # Bu sadece GÖRSEL güncelleme sıklığı; gerçek algılama/mouse kontrolü
        # engine.py'de ayrı bir hızda ve GUI'den bağımsız çalışıyor.
        self.dashboard.after(16, self._refresh_gui)

    def shutdown(self):
        logger.info("GestureOS kapatılıyor...")
        self._running = False
        self.engine.stop()


def main():
    app = GestureOSApp()
    try:
        app.start()
    except RuntimeError as e:
        logger.error(str(e))
        print(f"\nHATA: {e}\n")
    except KeyboardInterrupt:
        app.shutdown()


if __name__ == "__main__":
    main()
