# -*- coding: utf-8 -*-
"""
Halaman absensi mahasiswa. Terbuka saat mahasiswa memindai QR di kelas.
URL berisi: mk, p (pertemuan), s (waktu mulai sesi), t (token berganti).

Jalankan:  streamlit run app.py
"""
import time

import streamlit as st

import core
from storage import catat_absen

core.set_page("Absensi")
ss = st.session_state
q = st.query_params
mk, p, s, t = q.get("mk"), q.get("p"), q.get("s"), q.get("t")

if not all([mk, p, s, t]):
    st.markdown("""<div class="hero"><h2>🗓️ Absensi QR</h2>
    <p>Pindai QR code yang ditampilkan dosen di kelas menggunakan kamera HP kamu.</p></div>""",
                unsafe_allow_html=True)
    st.write("")
    st.info("Halaman ini hanya bisa dipakai lewat QR dari dosen. Dosen: buka menu "
            "**Dosen Buka Sesi** di panel kiri.")
    st.stop()

info = core.MATA_KULIAH.get(mk)
try:
    mulai = int(s)
    pertemuan = int(p)
except ValueError:
    info = None
if not info:
    st.error("QR tidak dikenali. Minta dosen menampilkan ulang QR.")
    st.stop()

st.markdown(f"""<div class="hero"><h2>{info['nama']}</h2>
<p>Pertemuan {pertemuan} · {info['prodi']} Semester {info['semester']}</p></div>""",
            unsafe_allow_html=True)
st.write("")

kunci = f"{mk}|{pertemuan}|{mulai}"

# Token diperiksa sekali saat halaman pertama dibuka, lalu mahasiswa diberi
# waktu terbatas untuk mengisi form.
if ss.get("scan_kunci") != kunci:
    if not core.token_valid(mk, pertemuan, mulai, t):
        st.error("⏰ QR sudah kedaluwarsa. QR berganti tiap 30 detik; "
                 "pindai lagi QR yang sedang tampil di layar kelas.")
        st.stop()
    ss["scan_kunci"] = kunci
    ss["scan_waktu"] = time.time()

if ss.get("sudah_absen") == kunci:
    st.success(f"✅ {ss.get('pesan_absen', 'Kehadiran kamu sudah tercatat.')}")
    st.stop()

status = core.status_waktu(mulai)
if status is None:
    st.error("Sesi absensi untuk pertemuan ini sudah ditutup.")
    st.stop()
if time.time() - ss["scan_waktu"] > core.BATAS_ISI_FORM_DETIK:
    st.error("Waktu mengisi habis. Pindai ulang QR yang sedang tampil di layar kelas.")
    ss.pop("scan_kunci", None)
    st.stop()

if status == "Terlambat":
    st.warning(f"Kamu tercatat **Terlambat** (lewat {core.TERLAMBAT_MENIT} menit dari mulai).")

roster = core.daftar_mahasiswa(mk)
npm = st.text_input("Masukkan NPM kamu", max_chars=12, placeholder="cth: 12345678").strip()

if npm:
    nama = roster.get(npm)
    if not nama:
        st.error("NPM tidak terdaftar di kelas ini. Periksa kembali, atau hubungi dosen.")
    else:
        st.markdown(f"""<div class="kartu">Nama terdaftar:<br>
        <span class="besar">{nama}</span></div>""", unsafe_allow_html=True)
        st.write("")
        yakin = st.checkbox("Saya menyatakan data ini benar dan saya hadir di kelas.")
        if st.button("✅ Catat kehadiran saya", type="primary", width="stretch", disabled=not yakin):
            # hitung ulang status saat tombol ditekan
            status = core.status_waktu(mulai) or "Terlambat"
            kode, pesan = catat_absen(mk, pertemuan, npm, nama, status)
            if kode in ("ok", "duplikat"):
                ss["sudah_absen"] = kunci
                ss["pesan_absen"] = (f"{pesan} {nama}, status: {status}."
                                     if kode == "ok" else pesan)
                st.rerun()
            else:
                st.error(pesan)

st.caption(f"Waktu sekarang: {core.sekarang_wib():%H:%M:%S} WIB · "
           "Titip absen adalah pelanggaran akademik.")
