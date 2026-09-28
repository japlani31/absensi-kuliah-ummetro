# -*- coding: utf-8 -*-
"""Rekap kehadiran: matriks per pertemuan, persentase, status manual, unduh Excel/PDF."""
import io

import pandas as pd
import streamlit as st
from fpdf import FPDF

import core
from storage import ambil_rekap, set_status

core.set_page("Rekap Kehadiran", "📊", layout="wide")
st.markdown("## 📊 Rekap Kehadiran")

if not core.cek_pin():
    st.stop()

pin = core._secret("DOSEN_PIN", "ebis2026")
mk = st.selectbox("Mata kuliah", list(core.MATA_KULIAH),
                  format_func=lambda k: core.MATA_KULIAH[k]["nama"])
info = core.MATA_KULIAH[mk]
roster = core.daftar_mahasiswa(mk)

if st.button("🔄 Muat ulang data"):
    ambil_rekap.clear()

rows = ambil_rekap(pin, mk)
dilaksanakan = sorted({int(r["pertemuan"]) for r in rows})


def matriks():
    """DataFrame: NPM, Nama, P1..Pn (kode H/T/I/S/A), rekap & persentase."""
    status = {(str(r["npm"]), int(r["pertemuan"])): r["status"] for r in rows}
    data = []
    for npm, nama in roster.items():
        baris = {"NPM": npm, "Nama": nama}
        hitung = {s: 0 for s in core.STATUS}
        for p in dilaksanakan:
            st_ = status.get((npm, p), "Alfa")
            baris[f"P{p}"] = core.KODE[st_]
            hitung[st_] += 1
        for s_ in core.STATUS:
            baris[s_] = hitung[s_]
        n = len(dilaksanakan)
        baris["% Hadir"] = round((hitung["Hadir"] + hitung["Terlambat"]) / n * 100, 1) if n else 0.0
        data.append(baris)
    return pd.DataFrame(data)


df = matriks()

c1, c2, c3 = st.columns(3)
c1.metric("Mahasiswa terdaftar", len(roster))
c2.metric("Pertemuan terlaksana", len(dilaksanakan))
if not df.empty and dilaksanakan:
    c3.metric(f"Di bawah {core.BATAS_KEHADIRAN}%", int((df["% Hadir"] < core.BATAS_KEHADIRAN).sum()))

if not dilaksanakan:
    st.info("Belum ada data absensi untuk mata kuliah ini.")
else:
    st.caption("Kode: H=Hadir, T=Terlambat, I=Izin, S=Sakit, A=Alfa. "
               f"Baris merah = kehadiran di bawah {core.BATAS_KEHADIRAN}%.")

    def warnai(baris):
        merah = baris["% Hadir"] < core.BATAS_KEHADIRAN
        return ["background-color:#fde2e2;color:#9b1c1c" if merah else "" for _ in baris]

    st.dataframe(df.style.apply(warnai, axis=1), hide_index=True, width="stretch")

    # ---------- Unduh ----------
    xbuf = io.BytesIO()
    with pd.ExcelWriter(xbuf, engine="openpyxl") as xw:
        df.to_excel(xw, index=False, sheet_name="Rekap")
        pd.DataFrame(rows).to_excel(xw, index=False, sheet_name="Data Mentah")

    def pdf_rekap():
        pdf = FPDF(orientation="L")
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, f"Rekap Kehadiran {info['nama']} - {info['prodi']} Semester {info['semester']}",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, f"Dosen: {info['dosen']}  |  Dicetak: {core.sekarang_wib():%d-%m-%Y %H:%M} WIB",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        kolom = list(df.columns)
        lebar = {"NPM": 22, "Nama": 62, "% Hadir": 16}
        pdf.set_font("Helvetica", "B", 7)
        for k in kolom:
            pdf.cell(lebar.get(k, 9 if k.startswith("P") else 14), 6, k, border=1, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", "", 7)
        for _, b in df.iterrows():
            merah = b["% Hadir"] < core.BATAS_KEHADIRAN
            pdf.set_text_color(170, 20, 20) if merah else pdf.set_text_color(0, 0, 0)
            for k in kolom:
                pdf.cell(lebar.get(k, 9 if k.startswith("P") else 14), 6,
                         str(b[k])[:40], border=1, align="L" if k == "Nama" else "C")
            pdf.ln()
        pdf.set_text_color(0, 0, 0)
        return bytes(pdf.output())

    d1, d2 = st.columns(2)
    d1.download_button("📥 Unduh Excel", xbuf.getvalue(), file_name=f"Rekap_Absensi_{mk}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       width="stretch")
    d2.download_button("📥 Unduh PDF", pdf_rekap(), file_name=f"Rekap_Absensi_{mk}.pdf",
                       mime="application/pdf", width="stretch")

# ---------- Status manual ----------
st.divider()
st.markdown("### ✏️ Ubah status (Izin / Sakit / koreksi)")
st.caption("Untuk mahasiswa yang menyerahkan surat izin/sakit, atau koreksi data.")
e1, e2, e3 = st.columns(3)
p_ubah = e1.selectbox("Pertemuan", list(range(1, core.JUMLAH_PERTEMUAN + 1)), key="p_ubah")
npm_ubah = e2.selectbox("Mahasiswa", list(roster), format_func=lambda k: f"{k} · {roster[k]}")
st_ubah = e3.selectbox("Status", core.STATUS, index=2)
if st.button("Simpan status"):
    ok, pesan = set_status(mk, p_ubah, npm_ubah, roster[npm_ubah], st_ubah, pin)
    (st.success if ok else st.error)(pesan)
    ambil_rekap.clear()
