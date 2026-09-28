# -*- coding: utf-8 -*-
"""
Penyimpanan absensi ke Google Sheet lewat Google Apps Script.
Bila APPS_SCRIPT_URL belum diatur, dipakai file CSV lokal (untuk uji coba).

Aksi ke Apps Script:
- absen  : catat kehadiran (server menolak bila NPM sudah absen di pertemuan itu)
- set    : ubah/isi status manual oleh dosen (Izin, Sakit, dll)
- rekap  : ambil semua baris (butuh PIN)
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


def _url():
    try:
        return st.secrets.get("APPS_SCRIPT_URL", "").strip()
    except Exception:
        return ""


# ---------------- CSV lokal (cadangan / uji coba) ----------------
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


# ---------------- API ----------------
def catat_absen(mk, pertemuan, npm, nama, status):
    """Kembalikan (kode, pesan). kode: 'ok' | 'duplikat' | 'gagal'."""
    baris = {"waktu": fmt_wib(time.time()), "mk": mk, "pertemuan": int(pertemuan),
             "npm": str(npm), "nama": nama, "status": status}
    url = _url()
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
    baris = {"waktu": fmt_wib(time.time()), "mk": mk, "pertemuan": int(pertemuan),
             "npm": str(npm), "nama": nama, "status": status}
    url = _url()
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


@st.cache_data(ttl=5, show_spinner=False)
def ambil_rekap(pin):
    """Ambil semua baris absensi. Di-cache 5 detik agar tidak membebani server."""
    url = _url()
    if url and requests is not None:
        try:
            r = requests.get(url, params={"aksi": "rekap", "pin": pin}, timeout=15)
            js = r.json()
            if isinstance(js, list):
                return js
            return []
        except Exception:
            return []
    return _baca_csv()
