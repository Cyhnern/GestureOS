"""
Dashboard: CustomTkinter tabanlı ana pencere.

Sorumluluğu:
- Kamera akışını (işlenmiş frame'i) ekranda göstermek
- FPS, algılanan el sayısı, hangi el(ler) gibi canlı istatistikleri göstermek
- Uygulamayı temiz şekilde kapatmak (kamera + mediapipe kaynaklarını serbest bırakmak)

Gesture/komut mantığı burada YOK; dashboard sadece "gösterge paneli".
main.py, her frame'de update_frame() metodunu çağırarak besler.
"""
import customtkinter as ctk
from PIL import Image, ImageTk
import cv2
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import get_logger

logger = get_logger("Dashboard")

# Pencere ilk açıldığında ya da genişlik/yükseklik bilgisi henüz hazır
# olmadığında kullanılacak başlangıç boyutu.
DEFAULT_DISPLAY_W = 720
DEFAULT_DISPLAY_H = 405
STATS_PANEL_WIDTH = 280  # İstatistik panelinin asla bu değerin altına sıkışmaması için


class Dashboard(ctk.CTk):
    def __init__(self, on_close_callback=None, on_profile_change=None, profile_names=None, active_profile=None):
        super().__init__()

        self.on_close_callback = on_close_callback
        # ERİŞİLEBİLİRLİK / SOL EL: profil menüsü artık sadece görsel değil -
        # kullanıcı seçim yaptığında engine.py'deki aktif profili değiştirir
        # (hangi sol el gesture'ının hangi komutu tetiklediğini belirler).
        self.on_profile_change = on_profile_change
        self.profile_names = profile_names or ["Office", "Gaming", "Presentation", "Editing", "Browser"]
        self.active_profile = active_profile or self.profile_names[0]
        self.display_size = (DEFAULT_DISPLAY_W, DEFAULT_DISPLAY_H)

        ctk.set_appearance_mode(config.APP_THEME)
        ctk.set_default_color_theme(config.APP_COLOR_THEME)

        self.title(config.APP_TITLE)
        self.minsize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

        self._build_layout()

        # Pencereyi açılışta ekranı kaplayacak şekilde başlat (Windows'a özel "zoomed" state).
        try:
            self.state("zoomed")
        except Exception:
            logger.warning("Pencere maximize edilemedi, normal boyutta açılıyor.")

    def _build_layout(self):
        # Ana grid: sol = video, sağ = istatistik paneli
        # Sağ kolona SABİT bir minsize veriyoruz ki video paneli asla onu sıkıştıramasın.
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0, minsize=STATS_PANEL_WIDTH)
        self.grid_rowconfigure(0, weight=1)

        # ---- Sol: Video paneli ----
        self.video_frame = ctk.CTkFrame(self, corner_radius=12)
        self.video_frame.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        self.video_frame.grid_rowconfigure(0, weight=1)
        self.video_frame.grid_columnconfigure(0, weight=1)

        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Tek bir CTkImage nesnesi tutuyoruz; her frame'de YENİDEN OLUŞTURMAK
        # yerine bunun içeriğini güncelleyeceğiz. Her frame'de yeni bir
        # CTkImage/PhotoImage yaratmak Windows'ta GDI handle'larını sızdırır
        # (eskisi GC ile tam temizlenmiyor) ve birkaç dakika içinde process'in
        # GDI handle limitine (10.000) çarpıp NATIVE olarak çökmesine sebep olur.
        self._ctk_img = None
        self._last_img_size = None

        # Video paneli yeniden boyutlandığında (örn. pencere maximize edilince)
        # display_size'ı güncelle. Bu SADECE resize olayında tetiklenir, her
        # karede değil - bu yüzden önceki "sürekli büyüme" hatasına düşmez.
        self.video_frame.bind("<Configure>", self._on_video_frame_resize)

        # ---- Sağ: İstatistik paneli ----
        self.stats_frame = ctk.CTkFrame(self, corner_radius=12)
        self.stats_frame.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")

        title = ctk.CTkLabel(
            self.stats_frame, text="✋ GestureOS", font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=(20, 10))

        self.fps_value = self._add_stat_row("FPS", "0.0")
        self.hands_value = self._add_stat_row("Algılanan El", "0")
        self.left_conf_value = self._add_stat_row("Sol El Güven", "-")
        self.right_conf_value = self._add_stat_row("Sağ El Güven", "-")
        self.gesture_value = self._add_stat_row("Gesture (Sağ El)", "-")
        self.left_gesture_value = self._add_stat_row("Gesture (Sol El)", "-")
        self.status_value = self._add_stat_row("Durum", "Bekleniyor...")

        # Profil seçici: artık gerçek işlevi var - seçim, sol elin hangi
        # komutları tetiklediğini (data/profiles.json üzerinden) değiştirir.
        profile_label = ctk.CTkLabel(self.stats_frame, text="Aktif Profil (Sol El)", font=ctk.CTkFont(size=13))
        profile_label.pack(pady=(25, 5))
        self.profile_menu = ctk.CTkOptionMenu(
            self.stats_frame, values=self.profile_names, command=self._handle_profile_change
        )
        self.profile_menu.set(self.active_profile)
        self.profile_menu.pack(pady=(0, 20))

        quit_btn = ctk.CTkButton(
            self.stats_frame, text="Kapat (Q)", fg_color="#a83232",
            hover_color="#801f1f", command=self._handle_close
        )
        quit_btn.pack(side="bottom", pady=20)

        self.bind("<q>", lambda e: self._handle_close())

    def _handle_profile_change(self, selected_name: str):
        logger.info("Profil menüsünden seçim yapıldı: %s", selected_name)
        if self.on_profile_change:
            self.on_profile_change(selected_name)

    def _add_stat_row(self, label_text: str, initial_value: str) -> ctk.CTkLabel:
        row = ctk.CTkFrame(self.stats_frame, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=6)

        label = ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(size=13), anchor="w")
        label.pack(side="left")

        value = ctk.CTkLabel(row, text=initial_value, font=ctk.CTkFont(size=13, weight="bold"), anchor="e")
        value.pack(side="right")

        return value

    def _on_video_frame_resize(self, event):
        # Minimize/arka plana atma sırasında Windows bazen 1x1 gibi anlamsız
        # boyutlarla Configure event'i fırlatır. Bunları filtrelemezsek her
        # seferinde display_size değişip gereksiz yere yeni image objesi
        # yaratma döngüsüne (ve GDI sızıntısına) girer.
        if event.width < 50 or event.height < 50:
            return

        # Kenar boşluklarını (padx/pady=10) düşüp makul bir minimum ile sınırlıyoruz.
        w = max(event.width - 20, 320)
        h = max(event.height - 20, 180)
        self.display_size = (w, h)

    def update_frame(self, frame_bgr):
        """OpenCV (BGR) frame'ini alır ve video panelinde güncel display_size'da gösterir."""
        # Pencere minimize edilmişse (arka planda, ikon halinde) hiçbir şey
        # çizmeye gerek yok - hem gereksiz hem de bazı Windows sürümlerinde
        # iconic durumdaki bir pencereye GDI çizimi yapmaya çalışmak sorunlu
        # olabiliyor.
        try:
            if self.state() == "iconic":
                return
        except Exception:
            pass

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        w, h = self.display_size
        img = img.resize((w, h))

        # KRİTİK FIX: Her frame'de yeni bir CTkImage yaratmak yerine, eğer
        # boyut değişmediyse VAR OLAN CTkImage'ın içeriğini güncelliyoruz.
        # Yeni CTkImage/PhotoImage her yaratıldığında bir Windows GDI handle
        # tüketiyor ve customtkinter bunları GC anında tam serbest bırakmıyor;
        # 60fps'te birkaç dakika içinde process'in GDI handle limitine (10.000)
        # çarpıp AÇIKLAMASIZ (native) çökmesine yol açıyordu.
        if self._ctk_img is None or self._last_img_size != (w, h):
            self._ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
            self._last_img_size = (w, h)
            self.video_label.configure(image=self._ctk_img, text="")
        else:
            self._ctk_img.configure(light_image=img, dark_image=img)

    def update_stats(self, fps: float, hand_results, gesture_name: str = "-", left_gesture_name: str = "-"):
        self.fps_value.configure(text=f"{fps:.1f}")
        self.hands_value.configure(text=str(len(hand_results)))

        left = next((h for h in hand_results if h.label == "Left"), None)
        right = next((h for h in hand_results if h.label == "Right"), None)

        self.left_conf_value.configure(text=f"%{left.confidence*100:.0f}" if left else "-")
        self.right_conf_value.configure(text=f"%{right.confidence*100:.0f}" if right else "-")
        self.gesture_value.configure(text=gesture_name)
        self.left_gesture_value.configure(text=left_gesture_name)

        status = "El(ler) algılandı" if hand_results else "El aranıyor..."
        self.status_value.configure(text=status)

    def _handle_close(self):
        logger.info("Kapatma isteği alındı.")
        if self.on_close_callback:
            self.on_close_callback()
        self.destroy()