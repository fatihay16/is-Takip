# -*- coding: utf-8 -*-
"""
Mustafakemalpaşa Belediyesi İmar ve Encümen Kayıt Yönetim Sistemi
Kurumsal Modern Tasarım, Tema ve Windows Pencere Yönetim Modülü

Özellikler:
- Windows yerel pencere çerçevesi (Titlebar, minimize, maximize/restore, close butonları)
- Windows görev çubuğunu (taskbar) kapatmayan akıllı ekran ve çalışma alanı (workarea) yerleşimi
- Yüksek çözünürlüklü ekranlarda (HiDPI) net tipografi (Windows DPI farkındalığı)
- Kurumsal Belediye Laciverti (#1E3A8A) ve Parlak Vurgu Mavisi (#2563EB)
- ttk Clam tabanlı modern düz (flat) tasarım, yuvarlatılmış estetik butonlar, sekmeler ve tablolar
- Çift temalı (Açık / Koyu) eksiksiz renk motoru
"""

import sys
import tkinter as tk
from tkinter import ttk

# Windows HiDPI Netlik Ayarı (Bulanık yazıları ve donuk pikselleri önler)
if sys.platform.startswith("win"):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# ==========================================
# KURUMSAL BELEDİYE RENK PALETLERİ
# ==========================================
ACIK = {
    "arka": "#F1F5F9",          # Modern açık gri/mavi zemin (Slate-100)
    "kart": "#FFFFFF",          # Kart ve panel zeminleri (Temiz Beyaz)
    "kart_alt": "#E2E8F0",      # İkincil kart / tablo başlık zemini (Slate-200)
    "metin": "#0F172A",         # Ana koyu metin (Slate-900)
    "soluk": "#64748B",         # İkincil / soluk metin (Slate-500)
    "kenar": "#CBD5E1",         # İnce açık kenarlıklar (Slate-300)
    "kenar_koyu": "#94A3B8",    # Belirgin kenarlık (Slate-400)
    "ust": "#1E3A8A",           # Kurumsal Belediye Laciverti (Blue-900)
    "ust_alt": "#1E40AF",       # Başlık ikincil / hover (Blue-800)
    "vurgu": "#2563EB",         # Vurgu Rengi (Blue-600)
    "vurgu_koyu": "#1D4ED8",    # Vurgu Aktif / Pressed (Blue-700)
    "hover": "#DBEAFE",         # Açık Mavi Hover (Blue-100)
    "secim": "#BFDBFE",         # Seçim Alanı (Blue-200)
    "tehlike": "#DC2626",       # Tehlike Kırmızı (Red-600)
    "tehlike_hover": "#B91C1C", # Tehlike Hover (Red-700)
    "tehlike_bg": "#FEE2E2",    # Tehlike Zemin (Red-100)
    "basari": "#16A34A",        # Başarı Yeşili (Green-600)
    "basari_bg": "#DCFCE7",     # Başarı Zemin (Green-100)
    "uyari": "#D97706",         # Uyarı Turuncusu (Amber-600)
    "uyari_bg": "#FEF3C7",      # Uyarı Zemin (Amber-100)
    "sb": "#CBD5E1",            # Scrollbar gövde
    "sb_hover": "#94A3B8",      # Scrollbar aktif
}

KOYU = {
    "arka": "#0B1120",          # Derin gece laciverti (Slate-950)
    "kart": "#1E293B",          # Kart ve panel zeminleri (Slate-800)
    "kart_alt": "#334155",      # İkincil kart / tablo başlık zemini (Slate-700)
    "metin": "#F8FAFC",         # Açık metin (Slate-50)
    "soluk": "#94A3B8",         # Soluk metin (Slate-400)
    "kenar": "#334155",         # Kenarlıklar (Slate-700)
    "kenar_koyu": "#475569",    # Belirgin kenarlık (Slate-600)
    "ust": "#070D19",           # En koyu başlık zemini
    "ust_alt": "#1E293B",       # Başlık ikincil
    "vurgu": "#3B82F6",         # Parlak Vurgu (Blue-500)
    "vurgu_koyu": "#2563EB",    # Vurgu Aktif (Blue-600)
    "hover": "#1E293B",         # Koyu Hover
    "secim": "#1E3A8A",         # Seçim Alanı (Blue-900)
    "tehlike": "#EF4444",       # Hata Kırmızı (Red-500)
    "tehlike_hover": "#DC2626", # Hata Hover (Red-600)
    "tehlike_bg": "#451A1A",    # Hata Zemin
    "basari": "#22C55E",        # Başarı Yeşili (Green-500)
    "basari_bg": "#14532D",     # Başarı Zemin
    "uyari": "#F59E0B",         # Uyarı Sarı (Amber-500)
    "uyari_bg": "#452C06",      # Uyarı Zemin
    "sb": "#475569",            # Scrollbar gövde
    "sb_hover": "#64748B",      # Scrollbar aktif
}

# Sayaç kartı rakam renkleri (açık, koyu)
STAT_RENK = {
    "mavi":   ("#2563EB", "#60A5FA"),
    "yesil":  ("#16A34A", "#4ADE80"),
    "kirmizi": ("#DC2626", "#F87171"),
    "turuncu": ("#EA580C", "#FB923C"),
    "mor":    ("#9333EA", "#C084FC"),
}


def stat_renk(ad, koyu=False):
    return STAT_RENK[ad][1 if koyu else 0]


def font_ailesi():
    """Windows'ta Segoe UI, diğer sistemlerde sistem varsayılan modern fontunu seçer."""
    if sys.platform.startswith("win"):
        return "Segoe UI"
    elif sys.platform.startswith("darwin"):
        return "SF Pro Display"
    return "DejaVu Sans"

def tema_uygula(pencere, koyu=False):
    """
    Tüm Tkinter ve TTK bileşenlerine profesyonel belediye kurumsal tasarımını uygular.
    Standart butonları, tabloları, form girişlerini, sekmeleri ve scrollbarları modernize eder.
    """
    palet = KOYU if koyu else ACIK
    pencere.configure(bg=palet["arka"])

    f_ad = font_ailesi()
    f_normal = (f_ad, 10)
    f_kucuk = (f_ad, 9)
    f_kalin = (f_ad, 10, "bold")
    f_buyuk = (f_ad, 12, "bold")

    # Tkinter standart dialog ve popup menü varsayılanları
    for ad, v in [
        ("*Font", f_normal),
        ("*Toplevel.background", palet["arka"]),
        ("*Listbox.background", palet["kart"]),
        ("*Listbox.foreground", palet["metin"]),
        ("*Listbox.selectBackground", palet["vurgu"]),
        ("*Listbox.selectForeground", "#FFFFFF"),
        ("*Listbox.relief", "flat"),
        ("*Listbox.highlightThickness", 1),
        ("*Listbox.highlightColor", palet["vurgu"]),
        ("*Listbox.highlightBackground", palet["kenar"]),
        ("*Text.background", palet["kart"]),
        ("*Text.foreground", palet["metin"]),
        ("*Text.relief", "flat"),
        ("*Text.highlightThickness", 1),
        ("*Text.highlightColor", palet["vurgu"]),
        ("*Text.highlightBackground", palet["kenar"]),
        ("*Menu.background", palet["kart"]),
        ("*Menu.foreground", palet["metin"]),
        ("*Menu.activeBackground", palet["vurgu"]),
        ("*Menu.activeForeground", "#FFFFFF"),
        ("*Menu.relief", "flat"),
        ("*Menu.borderWidth", 1),
        ("*TCombobox*Listbox.background", palet["kart"]),
        ("*TCombobox*Listbox.foreground", palet["metin"]),
        ("*TCombobox*Listbox.selectBackground", palet["vurgu"]),
        ("*TCombobox*Listbox.selectForeground", "#FFFFFF"),
    ]:
        pencere.option_add(ad, v)

    st = ttk.Style(pencere)
    try:
        st.theme_use("clam")
    except Exception:
        pass

    # Genel Varsayılanlar
    st.configure(".",
                 font=f_normal,
                 background=palet["arka"],
                 foreground=palet["metin"],
                 bordercolor=palet["kenar"],
                 focuscolor=palet["vurgu"])

    # Frame & Labelframe (Kart Görünümü)
    st.configure("TFrame", background=palet["arka"])
    st.configure("Card.TFrame", background=palet["kart"], relief="solid", borderwidth=1)
    st.configure("TLabelframe", background=palet["arka"], bordercolor=palet["kenar"], borderwidth=1, relief="solid")
    st.configure("TLabelframe.Label", background=palet["arka"], foreground=palet["vurgu"], font=f_kalin)

    # Label Stilleri
    st.configure("TLabel", background=palet["arka"], foreground=palet["metin"], font=f_normal)
    st.configure("Muted.TLabel", foreground=palet["soluk"], font=f_kucuk)
    st.configure("Header.TLabel", font=(f_ad, 16, "bold"), foreground=palet["vurgu"] if koyu else palet["ust"])
    st.configure("Sub.TLabel", font=f_kucuk, foreground=palet["soluk"])
    st.configure("Card.TLabel", background=palet["kart"], foreground=palet["metin"])

    # Standart Buton (TButton)
    st.configure("TButton",
                 background=palet["kart"],
                 foreground=palet["metin"],
                 bordercolor=palet["kenar"],
                 lightcolor=palet["kart"],
                 darkcolor=palet["kart"],
                 padding=(12, 7),
                 relief="flat",
                 borderwidth=1,
                 font=f_normal)
    st.map("TButton",
           background=[("pressed", palet["secim"]), ("active", palet["hover"])],
           foreground=[("pressed", palet["vurgu_koyu"]), ("active", palet["vurgu"])],
           bordercolor=[("active", palet["vurgu"]), ("pressed", palet["vurgu"])],
           lightcolor=[("active", palet["hover"]), ("pressed", palet["secim"])],
           darkcolor=[("active", palet["hover"]), ("pressed", palet["secim"])])

    # Vurgulu Buton (Accent.TButton - Primer İşlemler)
    st.configure("Accent.TButton",
                 background=palet["vurgu"],
                 foreground="#FFFFFF",
                 bordercolor=palet["vurgu"],
                 lightcolor=palet["vurgu"],
                 darkcolor=palet["vurgu"],
                 padding=(14, 8),
                 relief="flat",
                 borderwidth=1,
                 font=f_kalin)
    st.map("Accent.TButton",
           background=[("pressed", palet["vurgu_koyu"]), ("active", palet["vurgu_koyu"])],
           foreground=[("active", "#FFFFFF"), ("pressed", "#FFFFFF")],
           bordercolor=[("active", palet["vurgu_koyu"]), ("pressed", palet["vurgu_koyu"])],
           lightcolor=[("active", palet["vurgu_koyu"]), ("pressed", palet["vurgu_koyu"])],
           darkcolor=[("active", palet["vurgu_koyu"]), ("pressed", palet["vurgu_koyu"])])

    # Tehlike / Silme Butonu (Danger.TButton)
    st.configure("Danger.TButton",
                 background=palet["kart"],
                 foreground=palet["tehlike"],
                 bordercolor=palet["kenar"],
                 lightcolor=palet["kart"],
                 darkcolor=palet["kart"],
                 padding=(12, 7),
                 relief="flat",
                 borderwidth=1,
                 font=f_normal)
    st.map("Danger.TButton",
           background=[("pressed", palet["tehlike_bg"]), ("active", palet["tehlike_bg"])],
           bordercolor=[("active", palet["tehlike"]), ("pressed", palet["tehlike"])],
           lightcolor=[("active", palet["tehlike_bg"]), ("pressed", palet["tehlike_bg"])],
           darkcolor=[("active", palet["tehlike_bg"]), ("pressed", palet["tehlike_bg"])],
           foreground=[("active", palet["tehlike_hover"]), ("pressed", palet["tehlike_hover"])])

    # Menü Butonu (TMenubutton)
    st.configure("TMenubutton",
                 background=palet["kart"],
                 foreground=palet["metin"],
                 bordercolor=palet["kenar"],
                 lightcolor=palet["kart"],
                 darkcolor=palet["kart"],
                 arrowcolor=palet["soluk"],
                 padding=(12, 7),
                 relief="flat",
                 borderwidth=1,
                 font=f_normal)
    st.map("TMenubutton",
           background=[("pressed", palet["secim"]), ("active", palet["hover"])],
           foreground=[("pressed", palet["vurgu_koyu"]), ("active", palet["vurgu"])],
           bordercolor=[("active", palet["vurgu"])],
           lightcolor=[("active", palet["hover"])],
           darkcolor=[("active", palet["hover"])])

    # Metin Giriş Kutusu (TEntry)
    st.configure("TEntry",
                 fieldbackground=palet["kart"],
                 foreground=palet["metin"],
                 insertcolor=palet["metin"],
                 bordercolor=palet["kenar"],
                 lightcolor=palet["kenar"],
                 darkcolor=palet["kenar"],
                 padding=6,
                 relief="flat")
    st.map("TEntry",
           bordercolor=[("focus", palet["vurgu"])],
           lightcolor=[("focus", palet["vurgu"])],
           darkcolor=[("focus", palet["vurgu"])])

    # Açılır Liste (TCombobox)
    st.configure("TCombobox",
                 fieldbackground=palet["kart"],
                 background=palet["kart"],
                 foreground=palet["metin"],
                 insertcolor=palet["metin"],
                 bordercolor=palet["kenar"],
                 lightcolor=palet["kenar"],
                 darkcolor=palet["kenar"],
                 arrowcolor=palet["vurgu"],
                 padding=5,
                 relief="flat")
    st.map("TCombobox",
           fieldbackground=[("readonly", palet["kart"])],
           foreground=[("readonly", palet["metin"])],
           bordercolor=[("focus", palet["vurgu"])],
           lightcolor=[("focus", palet["vurgu"])],
           darkcolor=[("focus", palet["vurgu"])],
           selectbackground=[("readonly", palet["kart"])],
           selectforeground=[("readonly", palet["metin"])])

    # Sayı Kutusu (TSpinbox)
    st.configure("TSpinbox",
                 fieldbackground=palet["kart"],
                 foreground=palet["metin"],
                 background=palet["kart"],
                 insertcolor=palet["metin"],
                 bordercolor=palet["kenar"],
                 lightcolor=palet["kenar"],
                 darkcolor=palet["kenar"],
                 arrowcolor=palet["vurgu"],
                 padding=5)
    st.map("TSpinbox",
           bordercolor=[("focus", palet["vurgu"])],
           lightcolor=[("focus", palet["vurgu"])],
           darkcolor=[("focus", palet["vurgu"])])

    # Onay Kutusu (TCheckbutton)
    st.configure("TCheckbutton",
                 background=palet["arka"],
                 foreground=palet["metin"],
                 font=f_normal)
    st.map("TCheckbutton",
           background=[("active", palet["arka"])],
           foreground=[("active", palet["vurgu"])])

    # Sekmeler (TNotebook & TNotebook.Tab)
    st.configure("TNotebook",
                 background=palet["arka"],
                 borderwidth=0,
                 tabmargins=(4, 6, 4, 0))
    st.configure("TNotebook.Tab",
                 background=palet["kart_alt"],
                 foreground=palet["soluk"],
                 padding=(18, 8),
                 font=f_kalin,
                 borderwidth=0,
                 lightcolor=palet["kart_alt"],
                 darkcolor=palet["kart_alt"],
                 bordercolor=palet["kenar"])
    st.map("TNotebook.Tab",
           background=[("selected", palet["kart"]), ("active", palet["hover"])],
           foreground=[("selected", palet["vurgu"]), ("active", palet["vurgu"])],
           lightcolor=[("selected", palet["kart"]), ("active", palet["hover"])],
           darkcolor=[("selected", palet["kart"]), ("active", palet["hover"])],
           bordercolor=[("selected", palet["kenar"])])

    # Tablo (Treeview)
    st.configure("Treeview",
                 background=palet["kart"],
                 fieldbackground=palet["kart"],
                 foreground=palet["metin"],
                 rowheight=34,
                 borderwidth=0,
                 font=f_normal)
    st.configure("Treeview.Heading",
                 background=palet["kart_alt"],
                 foreground=palet["soluk"],
                 font=(f_ad, 9, "bold"),
                 padding=(8, 11),
                 relief="flat",
                 borderwidth=0,
                 lightcolor=palet["kart_alt"],
                 darkcolor=palet["kart_alt"],
                 bordercolor=palet["kenar"])
    st.map("Treeview.Heading",
           background=[("active", palet["secim"])],
           lightcolor=[("active", palet["secim"])],
           darkcolor=[("active", palet["secim"])])
    st.map("Treeview",
           background=[("selected", palet["secim"])],
           foreground=[("selected", palet["metin"])])

    # Alt bilgi çubuğu (tablo altındaki "42 kayıt listelendi..." şeridi)
    st.configure("Footer.TLabel", background=palet["kart_alt"], foreground=palet["soluk"],
                 font=f_kucuk, padding=(14, 8))

    # İlerleme Çubuğu (Horizontal.TProgressbar)
    st.configure("Horizontal.TProgressbar",
                 background=palet["vurgu"],
                 troughcolor=palet["kenar"],
                 borderwidth=0,
                 thickness=7)

    # Kaydırma Çubukları (Scrollbars)
    st.configure("Vertical.TScrollbar",
                 background=palet["sb"],
                 troughcolor=palet["arka"],
                 bordercolor=palet["arka"],
                 arrowcolor=palet["soluk"],
                 lightcolor=palet["sb"],
                 darkcolor=palet["sb"],
                 relief="flat",
                 borderwidth=0)
    st.map("Vertical.TScrollbar",
           background=[("active", palet["sb_hover"])],
           lightcolor=[("active", palet["sb_hover"])],
           darkcolor=[("active", palet["sb_hover"])])
    st.configure("Horizontal.TScrollbar",
                 background=palet["sb"],
                 troughcolor=palet["arka"],
                 bordercolor=palet["arka"],
                 arrowcolor=palet["soluk"],
                 lightcolor=palet["sb"],
                 darkcolor=palet["sb"],
                 relief="flat",
                 borderwidth=0)
    st.map("Horizontal.TScrollbar",
           background=[("active", palet["sb_hover"])],
           lightcolor=[("active", palet["sb_hover"])],
           darkcolor=[("active", palet["sb_hover"])])

    return palet


def pencere_merkeze_yerlestir(pencere, genislik=1420, yukseklik=780, oran_max=0.92):
    """
    Pencereyi ekran çözünürlüğüne göre akıllıca hesaplar.
    Windows görev çubuğunu (taskbar) kapatmaz ve ekranın dışına taşmaz.
    """
    try:
        pencere.update_idletasks()
        ekran_g = pencere.winfo_screenwidth()
        ekran_y = pencere.winfo_screenheight()

        hedef_g = min(int(genislik), int(ekran_g * oran_max))
        kullanilabilir_y = ekran_y - 75  # Görev çubuğu boşluğu
        hedef_y = min(int(yukseklik), int(kullanilabilir_y * oran_max))

        x = max(0, (ekran_g - hedef_g) // 2)
        y = max(10, (kullanilabilir_y - hedef_y) // 2)

        pencere.geometry(f"{hedef_g}x{hedef_y}+{x}+{y}")
    except Exception:
        pass


def ozel_baslik(pencere, baslik, koyu=False, kurumsal_alt=None):
    """
    Windows yerel pencere kontrollerini (küçült, büyüt, kapat, Aero snap, görev çubuğu)
    %100 koruyan kurumsal belediye bilgi şeridi.
    """
    palet = KOYU if koyu else ACIK

    pencere.title(baslik)
    try:
        pencere.overrideredirect(False)
    except Exception:
        pass

    # En üst kurumsal belediye başlık şeridi
    cubuk = tk.Frame(
        pencere,
        bg=palet["ust"],
        height=52
    )
    cubuk.pack(side="top", fill="x")
    cubuk.pack_propagate(False)

    # Sol belediye arma / simge
    sol_kutu = tk.Frame(cubuk, bg=palet["ust"])
    sol_kutu.pack(side="left", fill="y", padx=(16, 8))

    arma_metin = tk.Label(
        sol_kutu,
        text="🏛",
        bg=palet["ust"],
        fg="#FFFFFF",
        font=("Segoe UI Emoji", 15)
    )
    arma_metin.pack(side="left", pady=10)

    # Başlık ve Kurumsal Birim Açıklaması
    yazi_kutu = tk.Frame(cubuk, bg=palet["ust"])
    yazi_kutu.pack(side="left", fill="both", expand=True)

    yazi = tk.Label(
        yazi_kutu,
        text=baslik,
        bg=palet["ust"],
        fg="#FFFFFF",
        font=(font_ailesi(), 11, "bold"),
        anchor="w"
    )
    yazi.pack(side="top", fill="x", pady=(7, 0))

    alt_aciklama = kurumsal_alt or "T.C. Mustafakemalpaşa Belediyesi • İmar ve Şehircilik Müdürlüğü"
    alt_yazi = tk.Label(
        yazi_kutu,
        text=alt_aciklama,
        bg=palet["ust"],
        fg="#93C5FD" if not koyu else "#94A3B8",
        font=(font_ailesi(), 8),
        anchor="w"
    )
    alt_yazi.pack(side="top", fill="x")

    # Sağ durum rozeti
    sag_kutu = tk.Frame(cubuk, bg=palet["ust"])
    sag_kutu.pack(side="right", fill="y", padx=16)

    tema_rozet = tk.Label(
        sag_kutu,
        text="🌙 Koyu Mod" if koyu else "☀️ Açık Mod",
        bg=palet["ust_alt"],
        fg="#FFFFFF",
        font=(font_ailesi(), 8, "bold"),
        padx=10,
        pady=3
    )
    tema_rozet.pack(side="right", pady=13)

    # Tema değişince başlık şeridini yeniden boyayabilmek için parçaları sakla
    cubuk._modern_baslik = True
    cubuk._parcalar = {"cubuk": cubuk, "sol": sol_kutu, "arma": arma_metin, "yazi_kutu": yazi_kutu,
                       "yazi": yazi, "alt": alt_yazi, "sag": sag_kutu, "rozet": tema_rozet}
    return cubuk


def baslik_yenile(cubuk, koyu=False):
    """ozel_baslik ile oluşturulan şeridi açık/koyu temaya göre yeniden boyar."""
    p = KOYU if koyu else ACIK
    try:
        k = cubuk._parcalar
        for ad in ("cubuk", "sol", "arma", "yazi_kutu", "yazi", "sag"):
            k[ad].configure(bg=p["ust"])
        k["alt"].configure(bg=p["ust"], fg="#94A3B8" if koyu else "#93C5FD")
        k["rozet"].configure(bg=p["ust_alt"], text="🌙 Koyu Mod" if koyu else "☀️ Açık Mod")
    except Exception:
        pass
