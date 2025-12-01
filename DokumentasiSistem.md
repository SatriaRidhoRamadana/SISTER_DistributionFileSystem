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
**DOKUMENTASI SISTEM - DISTRIBUTED FILE SYSTEM (DFS)**

**Versi:** 1.2
**Tanggal:** 1 Desember 2025
**Status:** Development — DFS-focused documentation

## Daftar Isi
- Ringkasan singkat
- Komponen & Peran
- Arsitektur & Alur
- Skema Metadata (SQLite)
- API Lengkap (Naming Service & Storage Node)
- Cara Menjalankan (PowerShell)
- Replikasi & Strategi Recovery
- Storage layout & file format
- Pengujian & Skrip
- Troubleshooting & Logging
- Perintah Git / Deployment singkat

---

## Ringkasan singkat

Dokumentasi ini menjelaskan Distributed File System (DFS) yang ada di repository: layanan utama, antarmuka API, skema metadata, prosedur menjalankan sistem di lingkungan development (Windows), mekanisme replikasi, dan recovery. Fokus sekarang hanya pada komponen DFS (naming service, storage nodes, client, replication & recovery).

Tujuan: memberi pengembang panduan lengkap untuk menjalankan, menguji, dan memperluas DFS.

---

## Komponen & Peran

- `naming_service.py` — Coordinator/metadata service. Menyimpan metadata file, memilih storage nodes untuk upload, melacak replicas, memicu re-replication saat node gagal. Port default: `5000`.
- `storage_node.py` — Node penyimpanan: menerima upload, menyimpan file pada storage-dir, melayani download, menyediakan `/health` dan mengirim heartbeat ke naming service. Port default: `5001`, `5002`, `5003`.
- `dfs_client.py` — CLI client untuk upload/download/list/delete. Mengkomunikasikan dengan naming service untuk mendapatkan upload targets.
- `database_schema.py` — Skrip/definisi schema SQLite (metadata files, replicas, nodes, history).
- `replication_manager.py` — Logic untuk re-replication (dipanggil oleh naming service atau berjalan sebagai background worker).
- `advanced_recovery.py` — Mekanisme recovery saat terjadi korupsi atau multi-node failure.

---

## Arsitektur & Alur

Ringkasan alur upload:
1. Client meminta upload ke Naming Service: `POST /api/upload/request` dengan payload `{filename, size, replication_factor}`.
2. Naming Service membuat `file_id`, memilih N storage nodes sesuai `replication_factor` dan mengembalikan upload URLs.
3. Client melakukan `POST /upload/{file_id}` (multipart/form-data) langsung ke storage node yang dipilih.
4. Storage Node menyimpan file, menghitung checksum (SHA256), lalu mengirim notifikasi / konfirmasi ke Naming Service.
5. Naming Service memperbarui metadata (`files`, `replicas`) dan menandai upload selesai.

Ringkasan alur download:
1. Client meminta `GET /api/download/{file_id}` ke Naming Service.
2. Naming Service mengembalikan daftar replica endpoints `[{node_id, url}, ...]` dan metadata file.
3. Client memilih node (biasanya node pertama yang sehat) dan mengunduh `GET /download/{file_id}` dari node tersebut.

Health + pemantauan:
- Storage Node secara periodik mengirim heartbeat ke Naming Service (`POST /api/node/heartbeat`).
- Jika heartbeat terhenti > threshold, Naming Service menandai node `unavailable` dan memicu re-replication untuk setiap file yang kehilangan replica.

---

## Skema Metadata (SQLite)

Lokasi database development: `dfs.db` (file SQLite di root project). Skema inti:

- `nodes` (node_id TEXT PRIMARY KEY, addr TEXT, port INTEGER, status TEXT, last_heartbeat TIMESTAMP, available_space BIGINT)
- `files` (file_id TEXT PRIMARY KEY, filename TEXT, size INTEGER, checksum TEXT, created_at TIMESTAMP)
- `replicas` (id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT, node_id TEXT, path TEXT, created_at TIMESTAMP)
- `upload_history` (id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT, action TEXT, detail TEXT, ts TIMESTAMP)

Contoh SQL ditaruh di `database_schema.py` (jalankan untuk inisialisasi DB pada environment development).

Checksum: SHA256 digunakan untuk validasi integritas. Field `checksum` di tabel `files` menyimpan hex digest.

---

## API Lengkap

Semua endpoint diasumsikan default base `http://localhost:5000` untuk naming service.

Naming Service (Coordinator)

- POST /api/upload/request
   - Deskripsi: minta file_id + daftar upload targets
   - Body JSON: { "filename": str, "size": int, "replication_factor": int }
   - Response 200: { "file_id": str, "upload_nodes": [{"node_id":str,"upload_url":str}, ...] }

- POST /api/node/register
   - Deskripsi: Storage node mendaftarkan diri saat start
   - Body JSON: {"node_id":str,"addr":str,"port":int,"available_space":int}
   - Response: 200 ok

- POST /api/node/heartbeat
   - Body JSON: {"node_id":str,"available_space":int,"file_count":int}

- POST /api/replica/confirm
   - Deskripsi: Storage node mengkonfirmasi bahwa replica berhasil disimpan
   - Body JSON: {"file_id":str,"node_id":str,"path":str,"checksum":str}

- GET /api/download/{file_id}
   - Response: {"file_id":str,"filename":str,"size":int,"checksum":str,"replicas":[{"node_id":...,"download_url":...}, ...]}

- GET /api/files
   - List semua files metadata (paginated)

- GET /api/stats
   - Statistik sistem (node counts, total files, replication status)

Storage Node API (contoh base `http://localhost:5001`)

- POST /upload/{file_id}
   - Multipart form-data: `file` field
   - Behaviour: simpan file ke `<storage-dir>/{file_id}`, hitung checksum (SHA256), respond 201 with {"file_id":...,"path":...,"checksum":...}

- GET /download/{file_id}
   - Mengirim file binary sebagai attachment

- GET /health
   - Return JSON {"node_id":...,"status":"healthy","available_space":...}

- POST /internal/delete/{file_id}
   - Internal API untuk menghapus replica (dipakai saat rebalancing/re-replication)

Keamanan & otorisasi
- Saat ini API development tidak menerapkan ACL per-file; direkomendasikan menambahkan token-based auth antara naming service dan storage nodes (shared secret) untuk produksi.

---

## Cara Menjalankan (PowerShell)

1) Buat virtualenv dan install deps (di folder project):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Inisialisasi database (jika belum ada):

```powershell
python database_schema.py
```

3) Buat direktori storage nodes:

```powershell
mkdir .\storage\node1
mkdir .\storage\node2
mkdir .\storage\node3
```

4) Jalankan Naming Service:

```powershell
python naming_service.py
# service akan listen di http://localhost:5000
```

5) Jalankan masing-masing Storage Node di terminal terpisah:

```powershell
python storage_node.py --port 5001 --storage-dir .\storage\node1
python storage_node.py --port 5002 --storage-dir .\storage\node2
python storage_node.py --port 5003 --storage-dir .\storage\node3
```

6) Verifikasi health endpoints (PowerShell example):

```powershell
Invoke-RestMethod -Uri 'http://localhost:5000/health'
Invoke-RestMethod -Uri 'http://localhost:5001/health'
```

7) Upload file via client:

```powershell
python dfs_client.py upload path\to\file.txt
```

8) Download file via client:

```powershell
python dfs_client.py download <file_id> --output .\downloads
```

---

## Replikasi & Strategi Recovery

Replikasi
- Sistem menggunakan replication factor (default 2). Saat upload, Naming Service memilih nodes yang sehat dan memiliki ruang.
- Metadata `replicas` menyimpan daftar nodes yang menyimpan file.

Failure detection & re-replication
- Heartbeat dari nodes: jika Naming Service tidak menerima heartbeat selama `HEARTBEAT_TIMEOUT` (config), node ditandai `offline`.
- Untuk setiap file yang memiliki replica pada node offline, Replication Manager memilih target node baru (healthy & not already replica) dan meminta copy dari replica yang masih hidup.

Recovery flow (single node failure)
1. Detect node down.
2. For each file lost replica, select source replica and new target node.
3. Transfer file: source node `POST /internal/stream/{file_id}` to target node `POST /upload/{file_id}` (or via naming service orchestrator).
4. Target node confirms and Naming Service updates `replicas`.

Advanced recovery (multi-node or corrupted checksum)
- `advanced_recovery.py` mengandung heuristik: preferensi node berdasarkan latency/uptime, progressive re-replication, dan quorum-based validation ketika checksum mismatch.

---

## Storage layout & file format

- Storage root: `<storage-dir>` (passed to storage_node)
- On-disk file path: `<storage-dir>/<file_id>` (binary) and a small JSON meta file `<file_id>.meta.json` containing {filename, checksum, stored_at}

Contoh struktur node1:

```
.\storage\node1\
   ├── 05d6f7d3-...   # binary
   ├── 05d6f7d3-....meta.json
   └── ...
```

---

## Pengujian & Skrip

- Unit tests: `pytest` di file `test_dfs.py`, `test_recovery.py`, `test_advanced_recovery.py`.
- Manual failure test scenario:
   1. Start naming service + 3 storage nodes
   2. Upload file (replication_factor=2)
   3. Kill one storage node process
   4. Wait re-replication to finish (naming service logs)
   5. Verify `replicas` now point to two healthy nodes

---

## Troubleshooting & Logging

- Lihat logs di stdout untuk `naming_service.py` dan `storage_node.py`.
- Common issues:
   - Port already in use: ubah port atau hentikan proses lain
   - Permission error saat menulis file: periksa permission pada folder `storage/`
   - Node tidak terdaftar: periksa call `POST /api/node/register` dari node (logs saat start)

Debugging tips:

```powershell
# cek listening ports
netstat -ano | Select-String ":5000|:5001|:5002|:5003"

# health check
Invoke-RestMethod -Uri 'http://localhost:5000/health'
```

---

## Perintah Git / Deployment singkat

Setelah mengubah dokumentasi, commit & push:

```powershell
git add DokumentasiSistem.md
git commit -m "Docs(DFS): rewrite DokumentasiSistem.md — DFS-focused docs"
git push origin main
```

---

Jika Anda mau, saya bisa juga:
- Memecah dokumentasi ke `docs/` (contoh `docs/overview.md`, `docs/api.md`),
- Menambahkan contoh curl requests untuk setiap endpoint, atau
- Menambahkan checklist deployment ke produksi.
                                    │

┌──────────────────────────────────────────────────────┐

