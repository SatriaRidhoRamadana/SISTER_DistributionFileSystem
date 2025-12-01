**DOKUMENTASI SISTEM - DISTRIBUTED FILE SYSTEM (DFS)**

**Versi:** 1.0
**Tanggal:** 1 Desember 2025
**Status:** Development / Dokumentasi Terstruktur

## 📋 Daftar Isi

- Ringkasan Sistem
- Arsitektur Sistem
- Komponen Utama
- Persyaratan & Instalasi
- Cara Menjalankan
- API Endpoints (ringkasan)
- Database Schema (ringkasan)
- Testing
- Troubleshooting
- Struktur Project

---

## Ringkasan Sistem

Distributed File System (DFS) adalah sistem penyimpanan file terdistribusi yang mendukung replikasi otomatis, toleransi terhadap kegagalan (fault tolerance), dan mekanisme pemulihan otomatis. Implementasi ini menggunakan Python (Flask untuk layanan HTTP) dan SQLite untuk metadata persistensi pada mode development.

Tujuan dokumen ini adalah menyajikan dokumentasi teknis yang terstruktur, mudah dibaca, dan konsisten untuk pengembang dan penguji.

---

## Arsitektur Sistem (Singkat)

```
Client -> Naming Service (Coordinator, :5000)
                ├─ Storage Node 1 (:5001)
                ├─ Storage Node 2 (:5002)
                └─ Storage Node 3 (:5003)
```

- Naming Service bertindak sebagai koordinator metadata, penugasan upload, dan pemantauan kesehatan node.
- Storage Node menyimpan data fisik, melayani upload/download, dan mengirim heartbeat ke Naming Service.

---

## Komponen Utama

- **Naming Service** (`naming_service.py`): metadata manager, scheduler replikasi, health monitor, dan Web UI (port default: 5000).
- **Storage Node** (`storage_node.py`): menyimpan file, menyediakan endpoint upload/download, heartbeat ke naming service (port default: 5001-5003).
- **Client CLI** (`dfs_client.py`): tooling CLI untuk upload, download, list, delete, dan statistik.
- **Replication Manager** (`replication_manager.py`): background worker yang menangani re-replication saat node gagal.
- **Advanced Recovery** (`advanced_recovery.py`): strategi recovery prioritas untuk skenario kegagalan kompleks.
- **Database Schema** (`database_schema.py`): definisi tabel SQLite untuk metadata file, replicas, dan history.

---

## Persyaratan & Instalasi

**Software**:
- Python 3.9+
- pip

**Dependencies** (development):
```text
flask>=2.0.0
flask-cors>=3.0.10
requests>=2.28.0
```

Instalasi cepat:
```powershell
pip install -r requirements.txt
```

Persiapkan folder storage lokal:
```powershell
mkdir .\storage\node1
mkdir .\storage\node2
mkdir .\storage\node3
```

---

## Cara Menjalankan

Rekomendasi (Windows PowerShell): jalankan Naming Service dulu, lalu storage nodes di terminal terpisah.

Contoh manual:
```powershell
# Terminal 1 - Naming Service
python naming_service.py

# Terminal 2 - Storage Node 1
python storage_node.py --port 5001 --storage-dir .\storage\node1

# Terminal 3 - Storage Node 2
python storage_node.py --port 5002 --storage-dir .\storage\node2

# Terminal 4 - Storage Node 3
python storage_node.py --port 5003 --storage-dir .\storage\node3
```

Ada juga skrip `start_system.bat` yang sudah ada di project untuk mempermudah start pada Windows.

---

## API Endpoints (Ringkasan)

Naming Service (default: `http://localhost:5000`):

- `POST /api/upload/request` — minta lokasi upload & file_id (payload: filename, file_size, replication_factor).
- `GET  /api/download/{file_id}` — mendapatkan metadata dan daftar URLs download.
- `GET  /api/files` — daftar file metadata.
- `GET  /api/stats` — statistik sistem (nodes, files, replika).

Storage Node (contoh: `http://localhost:5001`):

- `POST /upload/{file_id}` — terima upload multipart/form-data.
- `GET  /download/{file_id}` — unduh file fisik.
- `GET  /health` — health check node.

Contoh ringkas request upload flow:
1. Client meminta upload ke Naming Service (`/api/upload/request`).
2. Naming Service mengembalikan `file_id` dan `upload_nodes` (upload URLs).
3. Client melakukan POST multipart ke salah satu Storage Node.

---

## Database Schema (Ringkasan)

Skema SQLite (metadata) mencakup tabel utama:

- `files` : informasi file (file_id, filename, size, checksum, created_at)
- `replicas` : mapping file_id -> node_id -> path
- `nodes` : registry node (node_id, addr, port, last_heartbeat, status)
- `upload_history` : riwayat upload/download dan perubahan replikasi

Untuk pengembangan, lihat `database_schema.py` untuk definisi SQL lengkap.

---

## Testing

Test otomatis ada di file `test_dfs.py`, `test_recovery.py`, dan `test_advanced_recovery.py`.

Menjalankan test suite singkat:
```powershell
python -m pytest test_dfs.py -q
python -m pytest test_recovery.py -q
```

Uji manual disarankan untuk skenario kegagalan: start 3 node, upload file, hentikan satu node, periksa re-replication.

---

## Troubleshooting (Ringkasan)

- Connection refused: pastikan service berjalan dan port tidak diblokir.
   ```powershell
   netstat -an | Select-String "5000|5001|5002|5003"
   ```
- Not enough storage nodes active: periksa health endpoint `GET /health` pada setiap node dan restart node yang mati.
- Checksum mismatch: hapus dan upload ulang file jika integritas rusak.

---

## Struktur Project (Ringkasan)

```
.
├── naming_service.py
├── storage_node.py
├── dfs_client.py
├── database_schema.py
├── replication_manager.py
├── advanced_recovery.py
├── requirements.txt
├── start_system.bat
├── storage/ (node folders)
└── tests/ (test files)
```

---

Jika Anda ingin saya menambahkan bagian tertentu (mis. detail API lengkap, contoh payload, atau diagram jaringan multi-laptop), beri tahu bagian mana yang ingin diperluas dan saya akan memperbaruinya.

**Perubahan:** file `DokumentasiSistem.md` telah disusun ulang agar konsisten dengan format `DOKUMENTASI_SISTEM.md`.
