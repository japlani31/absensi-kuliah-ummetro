# Panduan Absensi QR

Aplikasi absensi berbasis QR untuk mata kuliah **E-Business** (S1 Kewirausahaan, Semester 5).
Dosen: Ardiansyah Japlani, S.E., M.B.A.

## Alur di kelas

1. Dosen membuka menu **Dosen Buka Sesi**, masukkan PIN, pilih pertemuan, klik **Mulai sesi**.
2. Tampilkan QR di proyektor. QR berganti tiap 30 detik.
3. Mahasiswa memindai QR, isi NPM, centang pernyataan, klik **Catat kehadiran**.
4. Daftar yang sudah/belum absen tampil langsung di layar dosen.

## Aturan

| Aturan | Nilai | Diubah di |
|---|---|---|
| QR berganti | 30 detik | `core.py` JENDELA_DETIK |
| Sesi dibuka | 20 menit | `core.py` BUKA_MENIT |
| Terlambat setelah | 10 menit | `core.py` TERLAMBAT_MENIT |
| Batas kehadiran (tanda merah) | 75% | `core.py` BATAS_KEHADIRAN |

Satu NPM hanya bisa absen sekali per pertemuan. NPM di luar daftar kelas ditolak.

## Menghubungkan ke Google Sheet

1. Buat Google Sheet baru, salin ID-nya (bagian antara `/d/` dan `/edit` di alamat).
2. Buka script.google.com, New project, tempel isi `apps_script.gs`, isi `SHEET_ID` dan `PIN`.
3. Deploy > New deployment > Web app. Execute as: **Me**. Who has access: **Anyone**.
4. Salin Web app URL ke Secrets (`APPS_SCRIPT_URL`).

## Secrets (Streamlit Cloud > Settings > Secrets)

Salin dari `.streamlit/secrets.toml.example`, lalu isi `APPS_SCRIPT_URL`, `DOSEN_PIN`,
`QR_SECRET` (kalimat acak panjang), dan `APP_URL` (alamat aplikasi setelah deploy).
Daftar mahasiswa juga ditaruh di Secrets agar data pribadi tidak masuk GitHub.

## Sheet terpisah per mata kuliah

Setiap mata kuliah disimpan ke Google Sheet sendiri. Buat Sheet baru + proyek Apps
Script baru (isi `apps_script.gs` yang sama, `SHEET_ID` diganti), deploy, lalu tambahkan
URL-nya di Secrets:

```toml
[apps_script]
MKI = "https://script.google.com/macros/s/.../exec"
```

E-Business tetap memakai `APPS_SCRIPT_URL`. Bila URL suatu mata kuliah belum diisi, absensi
ditolak dengan pesan jelas (tidak pernah tercampur ke Sheet lain).

## Menambah mata kuliah lain

Tambahkan entri di `MATA_KULIAH` (`core.py`) dan daftar mahasiswanya di Secrets
(`[mahasiswa.KODE]`).
