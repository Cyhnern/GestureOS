"""
HandDetector: MediaPipe Hands modelini sarmalayan (wrap eden) sınıf.

Bu katmanın tek görevi: bir görüntü (frame) alıp, içindeki el(ler)in
21 landmark noktasını + hangi elin (Left/Right) olduğunu döndürmek.
Gesture yorumlama (pinch mi, yumruk mu) burada YAPILMAZ — o iş
gestures/classifier.py katmanına ait. Bu ayrım sayesinde algılama
mantığını değiştirmeden gesture kurallarını istediğimiz gibi değiştirebiliriz.
"""
import cv2
import mediapipe as mp
import sys
import os
from dataclasses import dataclass, field
from typing import List

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger

logger = get_logger("HandDetector")


@dataclass
class HandResult:
    label: str                      # "Left" veya "Right"
    landmarks: List[tuple]           # [(x, y, z), ...] normalize (0-1) koordinatlar
    landmarks_px: List[tuple]        # [(x, y), ...] piksel koordinatları
    confidence: float = 0.0


class HandDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.MAX_NUM_HANDS,
            model_complexity=config.MODEL_COMPLEXITY,
            min_detection_confidence=config.DETECTION_CONFIDENCE,
            min_tracking_confidence=config.TRACKING_CONFIDENCE,
        )
        logger.info("MediaPipe Hands modeli yüklendi.")

    def process(self, frame) -> List[HandResult]:
        """
        Frame'i işler, algılanan elleri HandResult listesi olarak döndürür.
        Frame BGR formatında olmalı (OpenCV varsayılanı).
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.hands.process(rgb_frame)

        hand_results: List[HandResult] = []
        h, w = frame.shape[:2]

        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                label = handedness.classification[0].label  # "Left" / "Right"
                score = handedness.classification[0].score

                norm_points = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
                px_points = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks.landmark]

                hand_results.append(
                    HandResult(
                        label=label,
                        landmarks=norm_points,
                        landmarks_px=px_points,
                        confidence=score,
                    )
                )

        return hand_results

    def draw_landmarks(self, frame, mp_hand_landmarks_list=None):
        """
        Not: Şu anki process() metodu çizim için ham mediapipe nesnesini
        döndürmüyor (sadece basit veri sınıfı). Görsel debug amaçlı çizim
        istersen, aşağıdaki draw_raw() metodunu kullan.
        """
        pass

    def draw_raw(self, frame, results):
        """MediaPipe'in kendi ham sonucu üzerinden hızlı görsel debug çizimi."""
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_styles.get_default_hand_landmarks_style(),
                    self.mp_styles.get_default_hand_connections_style(),
                )
        return frame

    def process_and_draw(self, frame):
        """
        Kolaylık metodu: hem HandResult listesi döndürür hem de frame üzerine
        landmark'ları çizer. Dashboard bunu kullanacak.
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.hands.process(rgb_frame)

        hand_results: List[HandResult] = []
        h, w = frame.shape[:2]

        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                label = handedness.classification[0].label
                score = handedness.classification[0].score

                norm_points = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
                px_points = [(int(lm.x * w), int(lm.y * h)) for lm in hand_landmarks.landmark]

                hand_results.append(
                    HandResult(label=label, landmarks=norm_points,
                               landmarks_px=px_points, confidence=score)
                )

                self.mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS,
                    self.mp_styles.get_default_hand_landmarks_style(),
                    self.mp_styles.get_default_hand_connections_style(),
                )

        return frame, hand_results

    def close(self):
        self.hands.close()
        logger.info("MediaPipe Hands kapatıldı.")
