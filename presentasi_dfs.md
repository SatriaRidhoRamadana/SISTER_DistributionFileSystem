# Presentasi: Distributed File System (DFS)

**Judul:** Distributed File System (DFS)
**Versi:** 1.2
**Tanggal:** 1 Desember 2025

---

## Slide 1 — Ringkasan Singkat

- Sistem penyimpanan file terdistribusi (DFS).
- Fitur utama: replikasi otomatis, toleransi kegagalan, checksum (SHA256) untuk integritas.
- Komponen utama: Naming Service (koordinator), Storage Nodes, CLI Client, Replication Manager.

---

## Slide 2 — Tujuan & Use-cases

- Menyediakan penyimpanan terdistribusi untuk file besar dan kecil.
- Use-cases: backup terdistribusi, penyimpanan asset aplikasi, sistem eksperimen/learning.
- Keunggulan: mudah dijalankan di laptop/devbox, replikasi otomatis, recovery terprogram.

---

## Slide 3 — Komponen Utama

- Naming Service (`naming_service.py`) — metadata, scheduling replikasi, health monitor (port 5000).
- Storage Node (`storage_node.py`) — menyimpan file, melayani upload/download, heartbeat (port 5001-5003).
- DFS Client (`dfs_client.py`) — upload/download/list/delete CLI.
- Replication Manager (`replication_manager.py`) — re-replication saat node turun.
- Advanced Recovery (`advanced_recovery.py`) — heuristik recovery untuk kasus kompleks.

---

## Slide 4 — Alur Upload / Download (ringkas)

1. Client -> POST `/api/upload/request` ke Naming Service.
2. Naming Service buat `file_id` dan kembalikan `upload_nodes`.
3. Client POST multipart ke `POST /upload/{file_id}` pada Storage Node.
4. Storage Node hitung checksum, simpan, lalu konfirmasi ke Naming Service.
5. Untuk download: Client minta `GET /api/download/{file_id}` → pilih replica → `GET /download/{file_id}`.

---

## Slide 5 — Skema Metadata (inti)

- Tabel `nodes`: node_id, addr, port, status, last_heartbeat, available_space.
- Tabel `files`: file_id, filename, size, checksum, created_at.
- Tabel `replicas`: file_id, node_id, path, created_at.
- Checksum: SHA256 pada file.

---

## Slide 6 — Replikasi & Recovery

- Default replication factor: 2 (configurable).
- Heartbeat memantau node; jika offline → trigger re-replication.
- Recovery flow: pilih source replica → transfer ke target → update metadata.
- Advanced recovery: checksum validation, quorum, progressive re-replication.

---

## Slide 7 — Cara Menjalankan (singkat)

```powershell
# buat virtualenv & install deps
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# inisialisasi DB (jika perlu)
python database_schema.py

# buat storage dirs
mkdir .\storage\node1; mkdir .\storage\node2; mkdir .\storage\node3

# start naming service
python naming_service.py

# start storage nodes (3 terminal terpisah)
python storage_node.py --port 5001 --storage-dir .\storage\node1
python storage_node.py --port 5002 --storage-dir .\storage\node2
python storage_node.py --port 5003 --storage-dir .\storage\node3
```

---

## Slide 8 — Contoh Demo Cepat

1. Upload file via client:
```powershell
python dfs_client.py upload path\to\file.txt
```
2. Catat `file_id` yang dikembalikan.
3. Download:
```powershell
python dfs_client.py download <file_id> --output .\downloads
```
4. Periksa checksum & keberadaan replicas pada `dfs.db`.

---

## Slide 9 — Troubleshooting & Tips

- Cek health: `GET http://localhost:5001/health` dan `http://localhost:5000/health`.
- Jika replikasi tidak berjalan: periksa logs naming service & replication manager.
- Pastikan `storage/` permission memungkinkan penulisan.

---

## Slide 10 — Next Steps & Pengembangan

- Tambah authentication antara Naming Service dan Storage Nodes.
- Tambah monitoring/metrics (Prometheus + Grafana).
- Tambah tests e2e dan simulasi chaos (kill node otomatis).
- Pertimbangkan storage tiering dan erasure coding untuk skala.

---

## Kontak / Referensi

- Repo: https://github.com/SatriaRidhoRamadana/SISTER_DistributionFileSystem
- File referensi: `DokumentasiSistem.md`, `naming_service.py`, `storage_node.py`, `dfs_client.py`

---

*Presentasi ini dibuat dari dokumentasi proyek dan disusun untuk demo/overview teknis.*
