"""
LandmarkTracker: El titremesinden (jitter) kaynaklanan gürültüyü azaltmak için
son N frame'in ortalamasını alan basit bir hareketli ortalama (moving average)
filtresi uygular. Bu, mouse kontrolünde fare imlecinin titrememesi için kritiktir.
"""
from collections import deque
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class LandmarkTracker:
    def __init__(self, window: int = config.SMOOTHING_WINDOW):
        self.window = window
        # Her el (Left/Right) için ayrı geçmiş tutulur
        self.history = {
            "Left": deque(maxlen=window),
            "Right": deque(maxlen=window),
        }

    def smooth(self, label: str, landmarks_px: list) -> list:
        """
        Verilen elin piksel landmark'larını geçmiş ile ortalayıp
        yumuşatılmış halini döndürür.
        """
        if label not in self.history:
            self.history[label] = deque(maxlen=self.window)

        self.history[label].append(landmarks_px)

        hist = self.history[label]
        n_points = len(landmarks_px)
        smoothed = []

        for i in range(n_points):
            xs = [frame[i][0] for frame in hist]
            ys = [frame[i][1] for frame in hist]
            smoothed.append((sum(xs) // len(xs), sum(ys) // len(ys)))

        return smoothed

    def reset(self, label: str = None):
        if label:
            self.history[label].clear()
        else:
            for key in self.history:
                self.history[key].clear()
