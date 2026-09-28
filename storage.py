# -*- coding: utf-8 -*-
"""
Penyimpanan absensi ke Google Sheet lewat Google Apps Script.

Setiap mata kuliah bisa punya Google Sheet (dan Apps Script) SENDIRI:
- APPS_SCRIPT_URL              -> dipakai E-Business (EBIS)
- [apps_script] MKI = "..."    -> dipakai Manajemen Keuangan Internasional
Mata kuliah lain cukup ditambah di tabel [apps_script] pada Secrets.

Pengaman: bila aplikasi berjalan online tetapi mata kuliah itu belum punya
URL, absensi DITOLAK dengan pesan jelas, bukan diam-diam dicampur ke Sheet
mata kuliah lain. File CSV lokal hanya dipakai bila tidak ada URL sama sekali
(uji coba di laptop).

Aksi ke Apps Script: absen, set (status manual), rekap (butuh PIN).
"""
import csv
import os
import time

import streamlit as st

try:
    import requests
except Exception:
    requests = None

from core import fmt_wib

CSV = "absensi_lokal.csv"
KOLOM = ["waktu", "mk", "pertemuan", "npm", "nama", "status"]
BELUM_DIATUR = "belum-diatur"


def _secret(nama, default=""):
    try:
        return st.secrets.get(nama, default)
    except Exception:
        return default


def _url(mk):
    """URL Apps Script khusus mata kuliah. Kembalikan '' (mode lokal) atau
    BELUM_DIATUR (online, tapi mata kuliah ini belum punya Sheet sendiri)."""
    try:
        khusus = dict(st.secrets.get("apps_script", {}))
    except Exception:
        khusus = {}
    if khusus.get(mk):
        return str(khusus[mk]).strip()
    utama = str(_secret("APPS_SCRIPT_URL", "")).strip()
    if mk == "EBIS" and utama:
        return utama
    if utama or khusus:          # sedang online, tapi mk ini belum diatur
        return BELUM_DIATUR
    return ""                    # tidak ada URL sama sekali: mode lokal


# ---------------- CSV lokal (uji coba) ----------------
def _baca_csv():
    if not os.path.exists(CSV):
        return []
    with open(CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _tulis_csv(rows):
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=KOLOM)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in KOLOM})


def _cari(rows, mk, p, npm):
    for i, r in enumerate(rows):
        if r["mk"] == mk and str(r["pertemuan"]) == str(p) and str(r["npm"]) == str(npm):
            return i
    return -1


def _baris(mk, pertemuan, npm, nama, status):
    return {"waktu": fmt_wib(time.time()), "mk": mk, "pertemuan": int(pertemuan),
            "npm": str(npm), "nama": nama, "status": status}


PESAN_BELUM = ("Penyimpanan untuk mata kuliah ini belum diatur dosen "
               "(Google Sheet belum terhubung). Hubungi dosen.")


# ---------------- API ----------------
def catat_absen(mk, pertemuan, npm, nama, status):
    """Kembalikan (kode, pesan). kode: 'ok' | 'duplikat' | 'gagal'."""
    baris = _baris(mk, pertemuan, npm, nama, status)
    url = _url(mk)
    if url == BELUM_DIATUR:
        return "gagal", PESAN_BELUM
    if url and requests is not None:
        try:
            r = requests.post(url, json={"aksi": "absen", **baris}, timeout=12)
            js = r.json() if r.status_code == 200 else {}
            if js.get("status") == "ok":
                return "ok", "Kehadiran tercatat."
            if js.get("status") == "duplikat":
                return "duplikat", "Kamu sudah tercatat absen di pertemuan ini."
            return "gagal", f"Server membalas: {js or r.status_code}"
        except Exception as e:
            return "gagal", f"Gagal terhubung ke server ({e}). Coba lagi."
    rows = _baca_csv()
    if _cari(rows, mk, pertemuan, npm) >= 0:
        return "duplikat", "Kamu sudah tercatat absen di pertemuan ini."
    rows.append(baris)
    _tulis_csv(rows)
    return "ok", "Kehadiran tercatat (mode lokal)."


def set_status(mk, pertemuan, npm, nama, status, pin):
    """Isi/ubah status manual oleh dosen (upsert)."""
    baris = _baris(mk, pertemuan, npm, nama, status)
    url = _url(mk)
    if url == BELUM_DIATUR:
        return False, PESAN_BELUM
    if url and requests is not None:
        try:
            r = requests.post(url, json={"aksi": "set", "pin": pin, **baris}, timeout=12)
            js = r.json() if r.status_code == 200 else {}
            return js.get("status") == "ok", js.get("pesan", "") or "Status diperbarui."
        except Exception as e:
            return False, f"Gagal: {e}"
    rows = _baca_csv()
    i = _cari(rows, mk, pertemuan, npm)
    if i >= 0:
        rows[i].update(baris)
    else:
        rows.append(baris)
    _tulis_csv(rows)
    return True, "Status diperbarui (mode lokal)."


def status_penyimpanan(mk):
    """Untuk ditampilkan di halaman dosen."""
    url = _url(mk)
    if url == BELUM_DIATUR:
        return "belum"
    return "sheet" if url else "lokal"


@st.cache_data(ttl=5, show_spinner=False)
def ambil_rekap(pin, mk):
    """Ambil semua baris absensi satu mata kuliah. Di-cache 5 detik."""
    url = _url(mk)
    if url == BELUM_DIATUR:
        return []
    if url and requests is not None:
        try:
            # PIN dikirim di body (POST), bukan di URL, agar tidak tercatat di log.
            r = requests.post(url, json={"aksi": "rekap", "pin": pin}, timeout=15)
            js = r.json()
            if isinstance(js, list):
                return [x for x in js if x.get("mk") == mk]
            return []
        except Exception:
            return []
    return [x for x in _baca_csv() if x.get("mk") == mk]
