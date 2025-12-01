# Presentasi: Distributed File System (DFS)

**Versi:** 1.2 — Presentasi
**Tanggal:** 1 Desember 2025

---

## Slide 1 — Ringkasan Singkat

- Apa itu: DFS adalah sistem penyimpanan file terdistribusi yang menyediakan replikasi, integritas, dan pemulihan otomatis.
- Tujuan: menyimpan file secara redundan di beberapa node sehingga layanan tetap tersedia ketika sebagian node turun.
- Kunci: Metadata (naming service), data (storage nodes), dan client orchestration.

---

## Slide 2 — Komponen & Peran (Ringkas)

- Naming Service: koordinator yang menyimpan metadata file, memilih node untuk upload, memantau kesehatan node, dan mengatur replikasi.
- Storage Node: menyimpan file fisik, menyajikan endpoint upload/download, mengirim heartbeat ke naming service.
- DFS Client: antarmuka pengguna (CLI) untuk upload/download/list/delete file.
- Replication Manager & Advanced Recovery: logic background untuk menjaga faktor replikasi dan memperbaiki kehilangan replica.

Penjelasan singkat tiap peran diberikan untuk audiens teknis agar paham tanggung jawab tiap service.

---

## Slide 3 — Arsitektur & Alur Upload/Download

1) Upload — langkah per langkah (penjelasan naratif):
	- Client meminta upload ke Naming Service (mengirim filename, size, replication_factor).
	- Naming Service mengalokasikan `file_id` dan memilih node-node target berdasarkan kesehatan dan ruang.
	- Client mengunggah berkas langsung ke salah satu Storage Node yang ditunjuk.
	- Storage Node menyimpan berkas, menghitung checksum SHA256, lalu mengonfirmasi ke Naming Service.
	- Naming Service mencatat replica baru di metadata.

2) Download — langkah per langkah:
	- Client meminta metadata & daftar replica dari Naming Service.
	- Client memilih salah satu replica sehat dan mengunduh file langsung dari Storage Node.

Gunakan diagram sederhana di slide untuk memperjelas alur (Client → Naming → Storage Nodes).

---

## Slide 4 — Skema Metadata & Integritas

- Database: SQLite (`dfs.db`) pada pengaturan development menyimpan tabel inti: `nodes`, `files`, `replicas`, `upload_history`.
- Checksum: setiap file diberi SHA256 untuk menjaga integritas; checksum disimpan di metadata `files`.
- Penjelasan setiap tabel (1–2 kalimat) ditujukan agar audiens tahu di mana info file & replica disimpan.

---

## Slide 5 — API Utama (Naming Service)

- `POST /api/upload/request`: minta `file_id` & upload targets — jelaskan request body dan response singkat.
- `GET /api/download/{file_id}`: dapatkan metadata & daftar replica.
- `POST /api/node/register` & `POST /api/node/heartbeat`: bagaimana node mendaftar & melaporkan status.

Catat: beri contoh payload singkat pada slide (1–2 contoh JSON) untuk audience developer.

---

## Slide 6 — API Node (Storage Node)

- `POST /upload/{file_id}`: menerima multipart upload; behavior: simpan file ke `<storage-dir>/<file_id>` dan buat meta JSON.
- `GET /download/{file_id}`: mengirim file sebagai attachment.
- `GET /health`: endpoint health untuk pemantauan.

Tekankan: komunikasi upload/download terjadi langsung antara client dan storage node; naming service hanya mengatur metadata & koordinasi.

---

## Slide 7 — Replikasi & Recovery (Ringkas)

- Default replication factor: 2 (konfigurasi dapat diubah).
- Deteksi kegagalan: heartbeat; jika node hilang → tanda `offline` di metadata.
- Re-replication: replication manager memilih sumber dan target, menyalin file, lalu memperbarui metadata.

Tambahkan contoh alur recovery singkat yang menampilkan trigger → copy → confirm → update metadata.

---

## Slide 8 — Storage Layout & Praktik Penulisan

- Struktur penyimpanan: `<storage-dir>/<file_id>` (binary) dan `<file_id>.meta.json` (small JSON dengan filename/checksum/timestamp).
- Jelaskan alasan menyimpan `.meta.json` lokal: cepat verifikasi, mempermudah operasi delete/cleanup lokal.

---

## Slide 9 — Menjalankan Sistem (Demo Steps)

Ringkasan langkah yang bisa ditampilkan ke audience saat demo singkat:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python database_schema.py
mkdir .\storage\node1; mkdir .\storage\node2; mkdir .\storage\node3
python naming_service.py
python storage_node.py --port 5001 --storage-dir .\storage\node1
python storage_node.py --port 5002 --storage-dir .\storage\node2
python storage_node.py --port 5003 --storage-dir .\storage\node3
```

Berikan catatan singkat: jalankan nodes di terminal terpisah dan tunjukkan health endpoints.

---

## Slide 10 — Pengujian & Skrip

- Unit tests: `pytest` pada file `test_dfs.py`, `test_recovery.py`, `test_advanced_recovery.py`.
- Demo failure test: upload file, hentikan satu node, tunjukkan re-replication, dan verifikasi metadata.

Tambahkan rekomendasi: otomatisasi test e2e menggunakan skrip PowerShell/Makefile.

---

## Slide 11 — Troubleshooting & Logging

- Hal-hal umum: port collision, permission error, node tidak terdaftar.
- Perintah cepat untuk cek:

```powershell
Invoke-RestMethod -Uri 'http://localhost:5000/health'
Invoke-RestMethod -Uri 'http://localhost:5001/health'
netstat -ano | Select-String ":5000|:5001|:5002|:5003"
```

Sertakan tips membaca logs stdout dari services untuk menemukan penyebab.

---

## Slide 12 — Perintah Git / Deployment singkat

- Commit & push docs changes:

```powershell
git add DokumentasiSistem.md presentasi_dfs.md
git commit -m "Docs: sync presentation with DFS documentation"
git push origin main
```

---

## Slide 13 — Kesimpulan & Next Steps

- Sistem sudah memiliki alur dasar upload/download, replikasi, dan recovery.
- Next steps: tambahkan auth internal, monitoring, dan automation tests.
- Ajak audiens untuk mencoba demo singkat dan mengajukan pertanyaan teknis.

---

*File ini berisi versi presentasi yang menjelaskan setiap bagian dari `DokumentasiSistem.md` dalam bahasa presentasi — cocok untuk demo teknis.*
