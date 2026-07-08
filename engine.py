"""
GestureEngine: Kamera okuma + el algılama + gesture sınıflandırma + mouse
kontrolünün TAMAMINI, GUI'den (Tkinter) tamamen bağımsız bir arka plan
thread'inde çalıştırır.

NEDEN GEREKLİ?
Windows, odakta olmayan (arka plana atılmış) pencerelerin GUI zamanlayıcılarını
(Tkinter'ın `after()` mekanizması buna dayanır) ciddi şekilde yavaşlatabilir/
kısıtlayabilir - bu, güç tasarrufu amaçlı bir davranıştır. Eğer gesture
işleme mantığı doğrudan Tkinter'ın `after()` döngüsüne bağlıysa, kullanıcı
başka bir uygulamaya geçtiği anda el algılama neredeyse tamamen durur.

Bu sınıf, tüm işlemeyi normal bir Python thread'ine taşır (bu, Windows'un
GUI mesaj kuyruğu zamanlayıcısından bağımsızdır ve bu şekilde kısıtlanmaz).
Dashboard, sadece bu thread'in ürettiği "en son frame + istatistikler"i
`get_latest()` ile okuyup ekranda gösterir. Yani:
- Pencere odakta değilken görsel güncelleme yavaşlayabilir (önemsiz)
- Ama mouse kontrolü / tıklamalar HER ZAMAN tam hızda çalışmaya devam eder
"""
import threading
import time
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import config
from detector.camera import Camera
from detector.hand_detector import HandDetector
from detector.landmark_tracker import LandmarkTracker
from classifier import classify, cursor_point_px, is_lock_pinch_gesture, is_palm_facing_camera
from gestures.gesture_filter import GestureFilter
from gestures.profile_manager import ProfileManager
from controllers.mouse import MouseController
from controllers.keyboard import KeyboardController
from utils.logger import get_logger

logger = get_logger("GestureEngine")

# Hangi gesture -> hangi mouse aksiyonu. Yeni bir gesture eklemek istersen
# sadece burada bir satır eklemen yeterli.
GESTURE_TO_ACTION = {
    "Pinch": "left_click",
    "MiddlePinch": "right_click",
}


class GestureEngine:
    def __init__(self):
        self.camera = Camera()
        self.detector = HandDetector()
        self.tracker = LandmarkTracker()
        self.gesture_filter = GestureFilter()
        self.mouse = MouseController(config.FRAME_WIDTH, config.FRAME_HEIGHT)

        # ERİŞİLEBİLİRLİK / SOL EL: sol el artık sağ elle AYNI classify()
        # fonksiyonuyla sınıflandırılıyor (aynı GestureFilter instance'ı,
        # label bazlı ayrı state tuttuğu için sağ eli etkilemiyor), ama
        # tetiklediği aksiyon aktif PROFİLE göre değişiyor - bu yüzden
        # mouse kontrolünden ayrı bir katman (klavye/medya) devreye giriyor.
        self.profile_manager = ProfileManager(default=config.DEFAULT_PROFILE)
        self.keyboard = KeyboardController()

        self.running = False
        self.thread = None

        # KRİTİK: El, ekranın kenarına yaklaştıkça (kamera FOV sınırında)
        # MediaPipe algılaması kararsızlaşır - el hâlâ oradayken bile ara sıra
        # tek frame'lik "algılanamadı" blip'leri olur. Eskiden bu blip'lerde
        # ANINDA tracker/filter resetleniyordu, bu da el bir sonraki frame'de
        # tekrar algılandığında sanki "yeni bir el"miş gibi davranılmasına ve
        # imlecin sıçramasına/geri kaymasına sebep oluyordu. Şimdi kısa süreli
        # kayıplarda (RIGHT_HAND_LOST_GRACE_MS içinde) hiçbir şeyi resetlemiyoruz;
        # sadece el gerçekten bu süre boyunca hiç görünmezse "gerçek kayıp" say.
        self._right_hand_last_seen = 0.0

        # KRİTİK FIX: Bir el, kamera FOV'undan çıkıp TEKRAR GİRDİĞİNDE hangi
        # elin bir önceki frame'de mevcut olduğunu takip ediyoruz. Bunu
        # LandmarkTracker'ın geçmişini DOĞRU ZAMANDA (sadece yeniden görünme
        # anında) sıfırlamak için kullanacağız - detaylar aşağıda.
        self._present_labels_last_frame = set()

        # KRİTİK: El gerçekten kayboldu mu (grace süresini aştı mı)?
        # Kısa blip'lerde tracker resetlenmez; imleç yerinde kalır.
        self._right_hand_truly_lost = False

        # El kameradan çıkıp geri gelince imlecin sıçramaması için: geri geldiğinde
        # kullanıcı elini bilinçli hareket ettirene kadar imleç sabit kalır.
        self._reacquiring = False
        self._reacquire_anchor = None

        # ERİŞİLEBİLİRLİK: Sağ elde başparmak + serçe pinch tutarak mouse
        # kontrolünü dondurma/açma. Kısa pinch = sol tık, uzun tutma = kilit.
        self.locked = False
        self._lock_stable_since = None
        self._lock_toggle_ready = True

        # Kısa pinch = sol tık, uzun pinch = kilit (release tabanlı tıklama)
        self._pinch_active = False
        self._pinch_started_at = None

        # Dashboard'un thread-safe okuyacağı "en son durum"
        self._lock = threading.Lock()
        self._latest_frame = None
        self._latest_hand_results = []
        self._latest_gesture_name = "-"
        self._latest_left_gesture_name = "-"

    def start(self):
        self.camera.start()
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("GestureEngine arka plan thread'i başlatıldı (GUI'den bağımsız).")

    def _run_loop(self):
        """
        Bu döngü, pencere odakta olsun olmasın SÜREKLİ aynı hızda çalışır.
        Windows'un GUI zamanlayıcı kısıtlamalarından etkilenmez çünkü
        Tkinter'ın after() mekanizmasını hiç kullanmıyor.
        """
        while self.running:
            try:
                self._process_one_frame()
            except Exception:
                # KRİTİK: Burada bir exception yakalanmazsa, thread SESSİZCE ölür
                # ve ekran donmuş gibi kalır (GUI çalışmaya devam eder ama yeni
                # frame gelmediği için hiçbir şey güncellenmez). Bu yüzden tüm
                # döngüyü try/except ile sarmalıyoruz - hata olsa bile thread
                # ayakta kalır ve terminale TAM hata mesajı yazılır.
                logger.exception("İşleme döngüsünde beklenmeyen hata oluştu:")
                time.sleep(0.1)

    def _process_one_frame(self):
        ret, frame = self.camera.read()
        if not ret or frame is None:
            time.sleep(0.01)
            return

        frame, hand_results = self.detector.process_and_draw(frame)

        # Tracker reset: SADECE el gerçekten kaybolduysa (grace aşıldıysa)
        # yeniden görününce sıfırla. Kısa blip'orunur,lerde eski geçmiş k
        # imleç kenara giderken "sıfırlama" hissi oluşmaz.
        current_labels = {h.label for h in hand_results}
        for label in current_labels - self._present_labels_last_frame:
            if label == "Right" and self._right_hand_truly_lost:
                self.tracker.reset(label)
                self._reacquiring = True
                self._reacquire_anchor = None
                self._right_hand_truly_lost = False
            elif label != "Right":
                self.tracker.reset(label)
        self._present_labels_last_frame = current_labels

        # Landmark smoothing (imlecin titremeden hareket etmesi için)
        for hand in hand_results:
            hand.landmarks_px = self.tracker.smooth(hand.label, hand.landmarks_px)

        right_hand = next((h for h in hand_results if h.label == "Right"), None)
        gesture_name = "-"

        self._update_lock_state(right_hand)

        if right_hand is not None:
            self._right_hand_last_seen = time.time() * 1000

            gesture = classify(right_hand.landmarks, right_hand.label)
            gesture_name = gesture.name

            if self.locked:
                self.mouse.stop_drag()
                gesture_name = "🔒 KİLİTLİ (açmak için 🤏 tutun)"
            else:
                cursor_x, cursor_y = cursor_point_px(right_hand.landmarks_px)
                self._move_cursor_with_reacquire(cursor_x, cursor_y)

                if gesture.name == "Fist":
                    self.mouse.start_drag()
                else:
                    self.mouse.stop_drag()

                self._handle_pinch_click(gesture.name, right_hand.label)

                if gesture.name not in ("Pinch",) and self.gesture_filter.update(right_hand.label, gesture.name):
                    self._execute_action(gesture.name)
        else:
            now = time.time() * 1000
            time_since_seen = now - self._right_hand_last_seen

            if time_since_seen < config.RIGHT_HAND_LOST_GRACE_MS:
                pass
            else:
                if not self._right_hand_truly_lost:
                    self._right_hand_truly_lost = True
                self.mouse.stop_drag()
                self.gesture_filter.reset("Right")

            if self.locked:
                gesture_name = "🔒 KİLİTLİ (açmak için 🤏 tutun)"

        # ---- SOL EL: fare kontrolüyle tamamen bağımsız, profile bağlı aksiyonlar ----
        # Aynı classify()/GestureFilter kullanılıyor (GestureFilter zaten label
        # bazlı ayrı state tuttuğu için sağ eldeki debounce/cooldown'u etkilemez).
        # Fark: tetiklenen KOMUT sabit değil, aktif profile (data/profiles.json)
        # göre değişiyor - bu yüzden mouse yerine keyboard controller'a gidiyor.
        left_hand = next((h for h in hand_results if h.label == "Left"), None)
        left_gesture_name = "-"

        if left_hand is not None:
            left_gesture = classify(left_hand.landmarks, left_hand.label)
            action_gesture_name = left_gesture.name

            # SOL EL: OpenPalm/Fist/Victory/ThumbUp gibi parmak-pozisyonu
            # tabanlı gesture'lar, el kameraya arkadan dönükken de (parmaklar
            # yine aynı şekilde açık/kapalı sayıldığı için) yanlışlıkla
            # tetiklenebiliyordu. Bu kontrol SADECE burada, sol el için
            # uygulanıyor - classify() fonksiyonu ve dolayısıyla sağ elin
            # davranışı hiç değişmedi. Pinch/MiddlePinch mesafe tabanlı
            # olduğu (ve zaten sadece avuç öne dönükken doğal olarak
            # yapılabildiği) için bu kontrolün dışında tutuluyor.
            if action_gesture_name not in ("None", "Pinch", "MiddlePinch"):
                if not is_palm_facing_camera(left_hand.landmarks, left_hand.label):
                    action_gesture_name = "None"

            left_gesture_name = left_gesture.name if action_gesture_name != "None" else "-"

            if self.gesture_filter.update(left_hand.label, action_gesture_name):
                self._execute_left_action(action_gesture_name)
        else:
            # Sol el sağ el gibi "grace period" gerektirmiyor (sürekli imleç
            # takibi yok, sadece anlık tetiklenen komutlar) - o yüzden el
            # kayboldu mu diye beklemeden pending state'i direkt temizliyoruz.
            self.gesture_filter.reset("Left")

        with self._lock:
            self._latest_frame = frame
            self._latest_hand_results = hand_results
            self._latest_gesture_name = gesture_name
            self._latest_left_gesture_name = left_gesture_name

    def _move_cursor_with_reacquire(self, cursor_x: int, cursor_y: int):
        """
        El kameradan çıkıp geri gelince imlecin elin yeni konumuna sıçramasını
        önler. Geri geldiğinde referans noktası kaydedilir; kullanıcı elini
        yeterince hareket ettirene kadar imleç sabit kalır.
        """
        if not self._reacquiring:
            self.mouse.move_to(cursor_x, cursor_y)
            return

        if self._reacquire_anchor is None:
            self._reacquire_anchor = (cursor_x, cursor_y)
            return

        ax, ay = self._reacquire_anchor
        moved = ((cursor_x - ax) ** 2 + (cursor_y - ay) ** 2) ** 0.5
        if moved >= config.REACQUIRE_MOVE_THRESHOLD_PX:
            self._reacquiring = False
            self._reacquire_anchor = None
            self.mouse.move_to(cursor_x, cursor_y)

    def _update_lock_state(self, right_hand):
        """
        Sağ elde başparmak + serçe pinch'i config.LOCK_GESTURE_HOLD_MS kadar
        tutunca mouse kontrolünü kilitler/açar. Poz bırakılıp tekrar
        yapılmadan bir sonraki toggle'a izin verilmez.
        """
        now = time.time() * 1000

        is_lock_pinch = False
        if right_hand is not None:
            is_lock_pinch = is_lock_pinch_gesture(right_hand.landmarks, right_hand.label)

        if not is_lock_pinch:
            self._lock_stable_since = None
            self._lock_toggle_ready = True
            return

        if self._lock_stable_since is None:
            self._lock_stable_since = now
            return

        stable_for = now - self._lock_stable_since
        if stable_for >= config.LOCK_GESTURE_HOLD_MS and self._lock_toggle_ready:
            self.locked = not self.locked
            self._lock_toggle_ready = False
            logger.info("Mouse kontrolü %s", "KİLİTLENDİ 🔒" if self.locked else "AÇILDI 🔓")

    def _handle_pinch_click(self, gesture_name: str, label: str):
        """
        Pinch (başparmak+işaret) artık SADECE sol tık için kullanılıyor.
        Kilit ayrı bir fiziksel poz (başparmak+serçe, is_lock_pinch_gesture)
        olduğu için burada bir üst süre sınırına gerek yok: Pinch ne kadar
        uzun tutulursa tutulsun, bırakıldığında (ve minimum debounce süresini
        geçtiyse) sol tık tetiklenir.
        """
        now = time.time() * 1000
        is_pinch = gesture_name == "Pinch"

        if is_pinch:
            if not self._pinch_active:
                self._pinch_active = True
                self._pinch_started_at = now
            return

        if not self._pinch_active:
            return

        duration = now - (self._pinch_started_at or now)
        self._pinch_active = False
        self._pinch_started_at = None

        if duration >= config.GESTURE_DEBOUNCE_MS and not self.locked:
            self._execute_action("Pinch")

    def _execute_action(self, gesture_name: str):
        action = GESTURE_TO_ACTION.get(gesture_name)
        if action == "left_click":
            self.mouse.left_click()
        elif action == "right_click":
            self.mouse.right_click()

    def _execute_left_action(self, gesture_name: str):
        """
        Sol el gesture'ını aktif profildeki aksiyona çevirip çalıştırır.
        Aksiyon string'i (ör. "volume_up"), controllers/keyboard.py içindeki
        BİREBİR AYNI isimli metoda karşılık gelir - yeni bir aksiyon eklemek
        istersen hem profiles.json'a hem KeyboardController'a aynı ismi
        eklemen yeterli.
        """
        action_name = self.profile_manager.get_action(gesture_name)
        if not action_name:
            return  # Aktif profilde bu gesture için tanımlı bir aksiyon yok

        method = getattr(self.keyboard, action_name, None)
        if callable(method):
            method()
        else:
            logger.warning(
                "Profildeki aksiyon '%s' KeyboardController'da bulunamadı.", action_name
            )

    def set_profile(self, name: str) -> bool:
        """Dashboard'daki profil menüsünden çağrılır (GUI thread'inden)."""
        return self.profile_manager.set_active(name)

    def get_active_profile(self) -> str:
        return self.profile_manager.get_active()

    def get_profile_names(self):
        return self.profile_manager.profile_names()

    def get_latest(self):
        """
        GUI tarafının okuması için thread-safe erişim.
        (frame, hand_results, gesture_name_right, gesture_name_left, fps)
        """
        with self._lock:
            return (
                self._latest_frame,
                self._latest_hand_results,
                self._latest_gesture_name,
                self._latest_left_gesture_name,
                self.camera.get_fps(),
            )

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=1.0)
        self.camera.stop()
        self.detector.close()
        logger.info("GestureEngine durduruldu.")