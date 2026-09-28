# -*- coding: utf-8 -*-
"""
Inti aplikasi absensi QR: konfigurasi, daftar mahasiswa, token QR berganti,
aturan waktu, dan tema.

Keamanan QR:
- Token dihitung dari HMAC(rahasia, mk|pertemuan|mulai|jendela_30_detik).
- Token berganti tiap 30 detik; yang diterima hanya jendela sekarang dan
  satu jendela sebelumnya (maks sekitar 60 detik). Foto QR yang dikirim
  lewat WhatsApp cepat kedaluwarsa.
- Tidak perlu server state: semua informasi sesi ada di URL dan ditandatangani.
"""
import hashlib
import hmac
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

WIB = ZoneInfo("Asia/Jakarta")

# ---------------- Konfigurasi aturan ----------------
JENDELA_DETIK = 30        # QR berganti tiap 30 detik
BUKA_MENIT = 20           # sesi absensi dibuka 20 menit sejak dimulai
TERLAMBAT_MENIT = 10      # lewat 10 menit dari mulai = Terlambat
BATAS_KEHADIRAN = 75      # persen minimal (tanda merah di rekap)
JUMLAH_PERTEMUAN = 16
BATAS_ISI_FORM_DETIK = 180  # setelah memindai, mahasiswa punya 3 menit mengisi

STATUS = ["Hadir", "Terlambat", "Izin", "Sakit", "Alfa"]
KODE = {"Hadir": "H", "Terlambat": "T", "Izin": "I", "Sakit": "S", "Alfa": "A"}

# Mata kuliah yang dilayani. Tambahkan di sini untuk mata kuliah lain.
MATA_KULIAH = {
    "EBIS": {
        "nama": "E-Business",
        "prodi": "S1 Kewirausahaan",
        "semester": "5",
        "dosen": "Ardiansyah Japlani, S.E., M.B.A.",
    },
}


def _secret(nama, default=""):
    try:
        return st.secrets.get(nama, default)
    except Exception:
        return default


# ---------------- Daftar mahasiswa ----------------
def daftar_mahasiswa(mk):
    """Kembalikan dict {npm: nama}. Sumber: st.secrets[mahasiswa][MK], lalu
    file lokal data_mahasiswa.py (diabaikan git, tidak ikut diunggah)."""
    try:
        data = st.secrets["mahasiswa"][mk]
        return {str(k): str(v) for k, v in dict(data).items()}
    except Exception:
        pass
    try:
        import data_mahasiswa
        return dict(data_mahasiswa.MAHASISWA.get(mk, {}))
    except Exception:
        return {}


# ---------------- Token QR ----------------
def _rahasia():
    return _secret("QR_SECRET", "ganti-rahasia-qr-ini").encode()


def jendela(ts=None):
    return int((ts or time.time()) // JENDELA_DETIK)


def buat_token(mk, pertemuan, mulai, w):
    pesan = f"{mk}|{pertemuan}|{int(mulai)}|{w}".encode()
    return hmac.new(_rahasia(), pesan, hashlib.sha256).hexdigest()[:12]


def token_valid(mk, pertemuan, mulai, token, ts=None):
    w = jendela(ts)
    for kandidat in (w, w - 1):
        if hmac.compare_digest(buat_token(mk, pertemuan, mulai, kandidat), str(token)):
            return True
    return False


def detik_sisa_jendela(ts=None):
    ts = ts or time.time()
    return JENDELA_DETIK - int(ts % JENDELA_DETIK)


def _akar(url):
    """Ambil hanya skema + domain, buang nama halaman (mis. /Dosen_Buka_Sesi)
    agar QR selalu mengarah ke halaman mahasiswa (halaman utama)."""
    from urllib.parse import urlparse
    u = urlparse(url.strip())
    if u.scheme and u.netloc:
        return f"{u.scheme}://{u.netloc}"
    return ""


def base_url():
    url = _akar(_secret("APP_URL", ""))
    if url:
        return url
    try:
        url = _akar(st.context.url or "")  # tersedia di Streamlit versi baru
        if url:
            return url
    except Exception:
        pass
    return "http://localhost:8501"


def url_absen(mk, pertemuan, mulai, ts=None):
    from urllib.parse import urlencode
    tok = buat_token(mk, pertemuan, mulai, jendela(ts))
    q = urlencode({"mk": mk, "p": pertemuan, "s": int(mulai), "t": tok})
    return f"{base_url()}/?{q}"


# ---------------- Aturan waktu ----------------
def status_waktu(mulai, ts=None):
    """Kembalikan 'Hadir', 'Terlambat', atau None bila sesi sudah ditutup."""
    menit = ((ts or time.time()) - mulai) / 60
    if menit < 0 or menit > BUKA_MENIT:
        return None
    return "Hadir" if menit <= TERLAMBAT_MENIT else "Terlambat"


def sekarang_wib():
    return datetime.now(WIB)


def fmt_wib(ts):
    return datetime.fromtimestamp(ts, WIB).strftime("%d-%m-%Y %H:%M:%S")


# ---------------- Tema ----------------
def set_page(judul, ikon="🗓️", layout="centered"):
    st.set_page_config(page_title=f"{judul} · Absensi QR", page_icon=ikon, layout=layout)
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
html, body, [class*="css"], p, li, label, span { font-family:'Plus Jakarta Sans',sans-serif; }
.stApp { background: radial-gradient(900px 400px at 100% -10%, #e8f7ef 0%, transparent 55%), #f6f8f7; }
.kartu { background:#fff; border:1px solid #e3ece7; border-radius:18px; padding:1.2rem 1.4rem;
  box-shadow:0 6px 20px rgba(20,90,60,.06); }
.hero { background:linear-gradient(120deg,#0f766e,#10b981); color:#fff; border-radius:20px;
  padding:1.4rem 1.6rem; }
.hero h2 { color:#fff; margin:0; }
.hero p { color:rgba(255,255,255,.92); margin:.3rem 0 0; }
.besar { font-size:2.4rem; font-weight:800; }
div.stButton > button { border-radius:12px; font-weight:700; }
</style>""", unsafe_allow_html=True)


def cek_pin(label="PIN dosen"):
    """Gerbang sederhana untuk halaman dosen. Kembalikan True bila PIN benar."""
    if st.session_state.get("dosen_ok"):
        return True
    pin = st.text_input(label, type="password")
    if pin:
        if pin == _secret("DOSEN_PIN", "ebis2026"):
            st.session_state["dosen_ok"] = True
            st.rerun()
        else:
            st.error("PIN salah.")
    return False
