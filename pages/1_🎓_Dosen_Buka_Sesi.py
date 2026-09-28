# -*- coding: utf-8 -*-
"""Halaman dosen: buka sesi absensi dan tampilkan QR yang berganti tiap 30 detik."""
import io
import time

import segno
import streamlit as st

import core
from storage import ambil_rekap

core.set_page("Dosen Buka Sesi", "🎓", layout="wide")
st.markdown("## 🎓 Buka Sesi Absensi")

if not core.cek_pin():
    st.stop()

ss = st.session_state
pin = core._secret("DOSEN_PIN", "ebis2026")

if not ss.get("sesi"):
    c1, c2 = st.columns(2)
    mk = c1.selectbox("Mata kuliah", list(core.MATA_KULIAH),
                      format_func=lambda k: f"{core.MATA_KULIAH[k]['nama']} ({core.MATA_KULIAH[k]['prodi']})")
    pertemuan = c2.selectbox("Pertemuan ke-", list(range(1, core.JUMLAH_PERTEMUAN + 1)))
    st.caption(f"Sesi dibuka {core.BUKA_MENIT} menit. Lewat {core.TERLAMBAT_MENIT} menit, "
               "mahasiswa tercatat Terlambat.")
    if st.button("▶️ Mulai sesi & tampilkan QR", type="primary"):
        ss["sesi"] = {"mk": mk, "p": pertemuan, "mulai": int(time.time())}
        st.rerun()
    st.stop()

sesi = ss["sesi"]
info = core.MATA_KULIAH[sesi["mk"]]
roster = core.daftar_mahasiswa(sesi["mk"])


@st.cache_data(max_entries=4, show_spinner=False)
def gambar_qr(url):
    """QR hanya digambar ulang saat isinya berubah (tiap 30 detik), bukan tiap refresh."""
    buf = io.BytesIO()
    segno.make(url, error="m").save(buf, kind="png", scale=12, border=2)
    return buf.getvalue()


# Diperbarui tiap 5 detik (bukan tiap detik) agar server gratis tidak terus sibuk.
# Token menerima jendela sekarang + sebelumnya, jadi jeda 5 detik tetap aman.
@st.fragment(run_every=5)
def tampil_qr():
    now = time.time()
    status = core.status_waktu(sesi["mulai"], now)
    kiri, kanan = st.columns([3, 2])
    with kiri:
        st.markdown(f"### {info['nama']} · Pertemuan {sesi['p']}")
        if status is None:
            st.error("Sesi ditutup. QR tidak lagi berlaku.")
            return
        url = core.url_absen(sesi["mk"], sesi["p"], sesi["mulai"], now)
        st.image(gambar_qr(url), width=460)
        st.caption("QR berganti otomatis tiap 30 detik.")
    with kanan:
        batas_telat = core.fmt_wib(sesi["mulai"] + core.TERLAMBAT_MENIT * 60)[-8:-3]
        tutup = core.fmt_wib(sesi["mulai"] + core.BUKA_MENIT * 60)[-8:-3]
        st.markdown(f"""<div class="kartu">
        <div>Tepat waktu sampai</div><div class="besar">{batas_telat} WIB</div>
        <div style="margin-top:.6rem">Sesi ditutup pukul</div><div class="besar">{tutup} WIB</div>
        <div style="margin-top:.6rem">Status saat ini: <b>{status}</b></div></div>""",
                    unsafe_allow_html=True)


@st.fragment(run_every=15)
def daftar_hadir():
    rows = [r for r in ambil_rekap(pin)
            if r.get("mk") == sesi["mk"] and str(r.get("pertemuan")) == str(sesi["p"])]
    st.markdown(f"#### 👥 Sudah absen: {len(rows)} dari {len(roster)} mahasiswa")
    if rows:
        st.dataframe([{"NPM": r["npm"], "Nama": r["nama"], "Status": r["status"],
                       "Waktu": r["waktu"]} for r in rows], hide_index=True, width="stretch")
    belum = [f"{n} ({k})" for k, n in roster.items()
             if k not in {str(r["npm"]) for r in rows}]
    if belum:
        with st.expander(f"Belum absen ({len(belum)})"):
            st.write("\n".join(f"- {b}" for b in belum))


tampil_qr()
daftar_hadir()

if st.button("⏹️ Tutup sesi"):
    ss.pop("sesi", None)
    st.rerun()
