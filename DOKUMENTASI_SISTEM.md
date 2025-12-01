# DOKUMENTASI SISTEM PORTFOLIO TERDISTRIBUSI

**Versi**: 1.0  
**Tanggal**: 1 Desember 2025  
**Status**: Production Ready

---

## 📋 DAFTAR ISI

1. [Ringkasan Sistem](#ringkasan-sistem)
2. [Arsitektur Sistem](#arsitektur-sistem)
3. [Topologi Multi-Laptop](#topologi-multi-laptop)
4. [Komponen Sistem](#komponen-sistem)
5. [Database Schema](#database-schema)
6. [API Endpoints](#api-endpoints)

---

##  RINGKASAN SISTEM

### Deskripsi
Platform portfolio terdistribusi berbasis microservices yang memungkinkan pengguna untuk membuat, berbagi, dan berkolaborasi pada project portfolio. Sistem ini didesain untuk deployment multi-laptop dengan komunikasi antar-service melalui REST API dan message broker.

### Fitur Utama
-  **Autentikasi & Otorisasi**: JWT-based authentication dengan refresh token
-  **Manajemen Profile**: User profiles dengan avatar upload
-  **Portfolio Projects**: CRUD projects dengan media upload (gambar/video)
-  **Media Processing**: Automatic thumbnail generation untuk gambar
-  **Search Engine**: Full-text search menggunakan Elasticsearch
-  **Likes & Comments**: Engagement system di external service (PHP)
-  **Real-time Analytics**: Project views dan statistics
-  **Responsive UI**: Mobile-friendly frontend

### Teknologi Stack

**Backend:**
- Python 3.11 + Flask
- PostgreSQL 15
- RabbitMQ (Message Broker)
- MinIO (Object Storage)
- Elasticsearch 8.11
- Nginx (Reverse Proxy)

**Frontend:**
- Vanilla JavaScript (ES6+)
- HTML5 & CSS3
- Responsive Design

**External Services:**
- PHP 8.x (Likes & Comments Service)
- Stream Chat API (Coming Soon)

---

##  ARSITEKTUR SISTEM

### Diagram Arsitektur

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER                          │
│                   (HTML/CSS/JS - Port 8080)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    NGINX REVERSE PROXY                          │
│                       (Port 80)                                 │
│  Routes:                                                        │
│    /api/auth/* → Auth Service                                  │
│    /api/profile/* → Profile Service                            │
│    /api/portfolio/* → Portfolio Service                        │
│    /api/media/* → Media Service                                │
│    /api/search/* → Search Service                              │
│    /api/likes/* → External PHP Service (192.168.1.17:8080)    │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Auth Service │ │Profile Service│ │Portfolio Srv │
│  (Port 8001) │ │  (Port 8002)  │ │  (Port 8003) │
└──────┬───────┘ └──────┬────────┘ └──────┬───────┘
       │                │                  │
       ├────────────────┴──────────────────┤
       │                                   │
       ▼                                   ▼
┌──────────────┐                    ┌──────────────┐
│ Media Service│                    │Search Service│
│  (Port 8004) │                    │  (Port 8005) │
└──────┬───────┘                    └──────┬───────┘
       │                                   │
       ▼                                   ▼
┌──────────────────────────────────────────────────┐
│              INFRASTRUCTURE LAYER                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │PostgreSQL│ │ RabbitMQ │ │  MinIO   │        │
│  │  :5432   │ │  :5672   │ │  :9000   │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│  ┌──────────────────────────────────┐          │
│  │      Elasticsearch :9200         │          │
│  └──────────────────────────────────┘          │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│         BACKGROUND WORKERS                       │
│  ┌──────────────────────────────────┐           │
│  │   Thumbnailer Worker             │           │
│  │   (Konsumsi RabbitMQ Queue)      │           │
│  └──────────────────────────────────┘           │
└──────────────────────────────────────────────────┘
```

### Pola Komunikasi

#### 1. **Synchronous (REST API)**
- Frontend ↔ All Services
- Service ↔ Database
- Auth verification antar services

#### 2. **Asynchronous (Message Queue)**
- Portfolio Service → RabbitMQ → Thumbnailer Worker
- Search Service → Elasticsearch indexing
- Event-driven updates

#### 3. **Object Storage**
- Media Service → MinIO (upload/download)
- Thumbnailer Worker → MinIO (thumbnail storage)

---

##  TOPOLOGI MULTI-LAPTOP

### Deployment Configuration

```
┌──────────────────────────────────────────────────────┐
│         LAPTOP A (10.132.78.141)                     │
│  ┌────────────────────────────────────────────┐     │
│  │  Core Infrastructure                       │     │
│  │  - PostgreSQL Database (:5432)             │     │
│  │  - RabbitMQ (:5672)                        │     │
│  │  - Auth Service (:8001)                    │     │
│  └────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
                        ▲
                        │ Network Connection
                        │ (Direct IP: 192.168.1.5 or 10.132.78.141)
                        │
┌──────────────────────────────────────────────────────┐
│         LAPTOP B (192.168.1.17)                      │
│  ┌────────────────────────────────────────────┐     │
│  │  External Services (PHP)                   │     │
│  │  - Likes & Comments Service (:8080)        │     │
│  │  - PostgreSQL Client (connects to A)       │     │
│  └────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────┘
                        ▲
                        │ Network Connection
                        │ (Proxied via Nginx)
                        │
┌──────────────────────────────────────────────────────┐
│         LAPTOP C (Current - Main Server)             │
│  ┌────────────────────────────────────────────┐     │
│  │  Application Layer                         │     │
│  │  - Frontend (:8080)                        │     │
│  │  - Nginx Proxy (:80)                       │     │
│  │  - Profile Service (:8002)                 │     │
│  │  - Portfolio Service (:8003)               │     │
│  │  - Media Service (:8004)                   │     │
│  │  - Search Service (:8005)                  │     │
│  │  - MinIO Storage (:9000)                   │     │
│  │  - Elasticsearch (:9200)                   │     │
│  │  - Thumbnailer Worker                      │     │
│  └────────────────────────────────────────────┘     │
│                                                      │
│  Ngrok Tunnel (Optional):                           │
│  https://xxxxx.ngrok-free.dev → localhost:80        │
└──────────────────────────────────────────────────────┘
```

### Network Configuration

#### Laptop A (Infrastructure)
```bash
IP: 10.132.78.141 (Internal Network)
Public: 192.168.1.5 (Local Network)

Open Ports:
- 5432 (PostgreSQL)
- 5672 (RabbitMQ)
- 15672 (RabbitMQ Management)
- 8001 (Auth Service)

Firewall Rules:
- Allow incoming: 5432, 5672, 8001
- Allow from: Laptop B, Laptop C
```

#### Laptop B (External PHP Service)
```bash
IP: 192.168.1.17

Open Ports:
- 8080 (PHP Service)

Requirements:
- PHP 8.x with curl extension
- PostgreSQL client library
- Network access to Laptop A:5432
```

#### Laptop C (Main Application)
```bash
IP: 192.168.x.x (Dynamic)

Open Ports:
- 80 (Nginx)
- 8080 (Frontend)
- 8002-8005 (Services)
- 9000 (MinIO)

External Access:
- Ngrok tunnel on port 80
- Domain: https://xxxxx.ngrok-free.dev
```

---

##  KOMPONEN SISTEM

### 1. Auth Service (Port 8001)

**Tanggung Jawab:**
- User registration & login
- JWT token generation & validation
- Refresh token management
- User data management

**Teknologi:**
- Flask (Python)
- bcrypt (password hashing)
- PyJWT (token generation)
- PostgreSQL

**Endpoints:**
```
POST   /auth/register          - Register user baru
POST   /auth/login             - Login user
POST   /auth/refresh           - Refresh access token
POST   /auth/logout            - Logout user
GET    /auth/verify            - Verify JWT token (untuk middleware)
GET    /api/users              - List all users (untuk chat sync)
GET    /api/user/:id           - Get user by ID
```

**Environment Variables:**
```env
DATABASE_URL=postgresql://admin:admin123@10.132.78.141:5432/distributed_system
JWT_SECRET=your-super-secret-jwt-key-change-in-production
JWT_EXPIRATION=86400
CHAT_API_KEY=secure-chat-api-key
```

---

### 2. Profile Service (Port 8002)

**Tanggung Jawab:**
- User profile management (name, bio, contact)
- Avatar upload & management
- Social links management
- Profile validation

**Teknologi:**
- Flask (Python)
- PostgreSQL
- File upload handling

**Endpoints:**
```
GET    /profile/me             - Get current user profile
GET    /profile/user/:user_id  - Get profile by user ID
PUT    /profile/update         - Update profile
POST   /profile/avatar         - Upload avatar
GET    /health                 - Health check
```

**Environment Variables:**
```env
DATABASE_URL=postgresql://admin:admin123@postgres:5432/distributed_system
JWT_SECRET=your-super-secret-jwt-key-change-in-production
AUTH_SERVICE_URL=http://auth_service:8000
```

---

### 3. Portfolio Service (Port 8003)

**Tanggung Jawab:**
- Project CRUD operations
- Project ownership management
- Tag management
- Event publishing ke RabbitMQ

**Teknologi:**
- Flask (Python)
- PostgreSQL
- RabbitMQ (pika)

**Endpoints:**
```
POST   /projects               - Create project
GET    /projects               - List all projects (with pagination)
GET    /projects/:id           - Get project by ID
PUT    /projects/:id           - Update project
DELETE /projects/:id           - Delete project
GET    /projects/user/:user_id - Get user's projects
GET    /search                 - Search projects
GET    /health                 - Health check
```

**Environment Variables:**
```env
DATABASE_URL=postgresql://admin:admin123@postgres:5432/distributed_system
JWT_SECRET=your-super-secret-jwt-key-change-in-production
RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672/
```

**RabbitMQ Events:**
- Queue: `thumbnail_queue`
- Event: Project created with images
- Payload: `{project_id, user_id, media_files: [{id, url, type}]}`

---

### 4. Media Service (Port 8004)

**Tanggung Jawab:**
- File upload (images, videos)
- MinIO integration
- Media metadata management
- File deletion

**Teknologi:**
- Flask (Python)
- MinIO client
- PostgreSQL
- Pillow (image validation)

**Endpoints:**
```
POST   /upload                 - Upload single file
POST   /upload/multiple        - Upload multiple files
GET    /file/:file_id          - Get file metadata
DELETE /file/:file_id          - Delete file
GET    /uploads/:path          - Serve file from MinIO
GET    /health                 - Health check
```

**Environment Variables:**
```env
DATABASE_URL=postgresql://admin:admin123@postgres:5432/distributed_system
JWT_SECRET=your-super-secret-jwt-key-change-in-production
RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672/
MINIO_ENDPOINT=minio:9000
MINIO_PUBLIC_URL=http://localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=admin123
MINIO_BUCKET=media-files
```

**Supported Formats:**
- Images: jpg, jpeg, png, gif, webp
- Videos: mp4, webm, mov
- Max size: 100MB

---

### 5. Search Service (Port 8005)

**Tanggung Jawab:**
- Elasticsearch indexing
- Full-text search
- Auto-complete suggestions
- Search analytics

**Teknologi:**
- Flask (Python)
- Elasticsearch
- RabbitMQ consumer

**Endpoints:**
```
GET    /search                 - Search projects
GET    /search/suggestions     - Auto-complete suggestions
POST   /index/project/:id      - Manual index project
DELETE /index/project/:id      - Remove from index
GET    /health                 - Health check
```

**Environment Variables:**
```env
ELASTICSEARCH_URL=http://elasticsearch:9200
RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672/
```

**Search Features:**
- Full-text search on title, description, tags
- Fuzzy matching
- Pagination
- Relevance scoring

---

### 6. Thumbnailer Worker (Background)

**Tanggung Jawab:**
- Generate thumbnails dari gambar
- Update project dengan thumbnail URLs
- Handle queue dari RabbitMQ

**Teknologi:**
- Python
- Pillow (image processing)
- MinIO client
- RabbitMQ consumer

**Workflow:**
1. Listen to `thumbnail_queue`
2. Download image dari MinIO
3. Generate thumbnail (300x300, 800x800)
4. Upload thumbnail ke MinIO
5. Update project di Portfolio Service

**Environment Variables:**
```env
RABBITMQ_URL=amqp://admin:admin123@rabbitmq:5672/
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=admin123
MINIO_BUCKET=media-files
PORTFOLIO_SERVICE_URL=http://portfolio_service:8000
```

---

### 7. External Service - Likes & Comments (PHP)

**Lokasi:** Laptop B (192.168.1.17:8080)

**Tanggung Jawab:**
- Like/unlike projects
- Comment CRUD
- Statistics aggregation
- Top liked/commented projects

**Teknologi:**
- PHP 8.x
- PostgreSQL
- cURL (untuk auth verification)

**Endpoints:**
```
# Likes
GET    /likes/project/:id         - Get likes count
POST   /likes/toggle/:id          - Toggle like
GET    /likes/check/:id           - Check if user liked (requires auth)
GET    /likes/user                - Get user's liked projects (requires auth)

# Comments
GET    /comments/project/:id      - Get project comments
POST   /comments                  - Create comment (requires auth)
PUT    /comments/:id              - Update comment (requires auth)
DELETE /comments/:id              - Delete comment (requires auth)

# Statistics
GET    /stats/project/:id         - Project stats (likes + comments)
GET    /stats/all                 - All projects stats
GET    /stats/top/liked           - Top liked projects
GET    /stats/top/commented       - Top commented projects
```

**Auth Middleware:**
```php
// Verify token dengan Auth Service
$authUrl = "http://192.168.1.5:8001/auth/verify";
$method = "GET"; // PENTING: GET bukan POST!

curl_setopt($ch, CURLOPT_URL, $authUrl);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Authorization: Bearer ' . $token
]);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'GET');
```

**Response Format:**
```json
{
  "success": true,
  "message": "Operation successful",
  "timestamp": "2025-12-01T10:30:00Z",
  "data": {
    // actual data here
  }
}
```

**Database Connection:**
```php
$host = '10.132.78.141'; // Laptop A
$port = '5432';
$dbname = 'distributed_system';
$user = 'admin';
$password = 'admin123';
```

---

### 8. Frontend (Port 8080)

**Lokasi:** `frontend/`

**Struktur:**
```
frontend/
├── index.html              # Landing page
├── login.html              # Login page
├── register.html           # Register page
├── explore.html            # Browse projects
├── profile.html            # User profile
├── edit-profile.html       # Edit profile
├── project-detail.html     # Project detail dengan likes/comments
├── create-project.html     # Create project form
├── edit-project.html       # Edit project form
├── styles.css              # Global styles
├── assets/                 # Images, icons
└── js/
    ├── config.js           # API config & helpers
    ├── auth.js             # Authentication logic
    ├── user-service.js     # User API wrapper
    ├── profile.js          # Profile management
    ├── home.js             # Feed & project cards
    ├── explore.js          # Search & filter
    ├── likes-comments.js   # Likes/Comments API wrapper
    └── chat.js             # Chat integration (future)
```

**Key Features:**

1. **Auto-detection Ngrok/Local:**
```javascript
const isNgrok = window.location.hostname.includes("ngrok");
const BASE_URL = isNgrok ? window.location.origin : "http://localhost";
```

2. **API Helper dengan Auth:**
```javascript
const api = {
  async get(url, options) { /* ... */ },
  async post(url, body, options) { /* ... */ },
  async put(url, body, options) { /* ... */ },
  async delete(url, options) { /* ... */ }
};
```

3. **LocalStorage Caching:**
```javascript
// Cache likes & comments untuk prevent reset
localStorage.setItem(`project_${id}_likes`, count);
localStorage.setItem(`project_${id}_comments`, commentsData);
```

4. **HTTPS Avatar URLs:**
```javascript
// Auto-convert http:// to https:// untuk prevent mixed content
if (avatarUrl && avatarUrl.startsWith('http://')) {
  avatarUrl = avatarUrl.replace('http://', 'https://');
}
```

---

##  DATABASE SCHEMA

### Schema: `distributed_system`

```sql
-- Users (Auth Service)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Refresh Tokens (Auth Service)
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Profiles (Profile Service)
CREATE TABLE profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    bio TEXT,
    contact VARCHAR(255),
    social_links JSONB DEFAULT '{}',
    avatar_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Projects (Portfolio Service)
CREATE TABLE projects (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    tags TEXT[] DEFAULT '{}',
    media_files JSONB DEFAULT '[]',
    thumbnail_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Media Files (Media Service)
CREATE TABLE media_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT,
    minio_path VARCHAR(500),
    url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Likes (External PHP Service)
CREATE TABLE likes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, project_id)
);

-- Comments (External PHP Service)
CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    comment_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analytics (Future)
CREATE TABLE project_views (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(project_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Indexes

```sql
-- Performance indexes
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX idx_projects_tags ON projects USING GIN(tags);
CREATE INDEX idx_likes_project_id ON likes(project_id);
CREATE INDEX idx_likes_user_id ON likes(user_id);
CREATE INDEX idx_comments_project_id ON comments(project_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_media_files_user_id ON media_files(user_id);
```

---

## 🔌 API ENDPOINTS

### Base URLs

**Local Development:**
```
Auth Service:       http://localhost:8001
Profile Service:    http://localhost:8002
Portfolio Service:  http://localhost:8003
Media Service:      http://localhost:8004
Search Service:     http://localhost:8005
Likes Service:      http://localhost/api/likes
```

**Production (Ngrok):**
```
All Services:       https://xxxxx.ngrok-free.dev/api/{service}/
```

### Authentication Flow

**1. Register:**
```bash
POST /auth/register
Content-Type: application/json

{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "securePassword123"
}

Response:
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "user": {
    "id": "uuid",
    "username": "john_doe",
    "email": "john@example.com"
  }
}
```

**2. Login:**
```bash
POST /auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "securePassword123"
}

Response: (same as register)
```

**3. Verify Token (Middleware):**
```bash
GET /auth/verify
Authorization: Bearer {access_token}

Response:
{
  "valid": true,
  "user_id": "uuid",
  "username": "john_doe"
}
```

### Profile Management

**Get Current Profile:**
```bash
GET /profile/me
Authorization: Bearer {access_token}

Response:
{
  "user_id": "uuid",
  "username": "john_doe",
  "name": "John Doe",
  "bio": "Software Developer",
  "contact": "john@example.com",
  "social_links": {
    "github": "github.com/johndoe",
    "linkedin": "linkedin.com/in/johndoe"
  },
  "avatar_url": "https://xxxxx.ngrok-free.dev/media/avatars/xxx.jpg"
}
```

**Update Profile:**
```bash
PUT /profile/update
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "name": "John Doe",
  "bio": "Full Stack Developer",
  "contact": "john@example.com",
  "social_links": {
    "github": "github.com/johndoe"
  }
}
```

### Project Management

**Create Project:**
```bash
POST /projects
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "title": "My Awesome Project",
  "description": "This is a description",
  "tags": ["python", "flask", "react"],
  "media_files": [
    {
      "id": "media-uuid-1",
      "url": "https://.../image1.jpg",
      "type": "image"
    }
  ]
}

Response:
{
  "project_id": "uuid",
  "user_id": "uuid",
  "title": "My Awesome Project",
  "description": "...",
  "tags": ["python", "flask", "react"],
  "media_files": [...],
  "thumbnail_url": null,  // Generated asynchronously
  "created_at": "2025-12-01T10:00:00Z"
}
```

**List Projects:**
```bash
GET /projects?page=1&per_page=10&sort=created_at&order=desc

Response:
{
  "projects": [...],
  "total": 100,
  "page": 1,
  "per_page": 10,
  "pages": 10
}
```

### Media Upload

**Upload Single File:**
```bash
POST /upload
Authorization: Bearer {access_token}
Content-Type: multipart/form-data

file: (binary)

Response:
{
  "id": "uuid",
  "filename": "xxx.jpg",
  "original_filename": "photo.jpg",
  "file_type": "image/jpeg",
  "file_size": 1024000,
  "url": "https://.../media/uploads/user-id/xxx.jpg"
}
```

### Likes & Comments

**Get Project Stats:**
```bash
GET /api/likes/stats/project/{project_id}

Response:
{
  "success": true,
  "data": {
    "project_id": "uuid",
    "total_likes": 42,
    "total_comments": 15
  }
}
```

**Toggle Like:**
```bash
POST /api/likes/likes/toggle/{project_id}
Authorization: Bearer {access_token}

Response:
{
  "success": true,
  "message": "Project liked",
  "data": {
    "action": "liked",  // or "unliked"
    "is_liked": true,
    "total_likes": 43
  }
}
```

**Create Comment:**
```bash
POST /api/likes/comments
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "project_id": "uuid",
  "comment_text": "Great project!"
}

Response:
{
  "success": true,
  "message": "Comment created",
  "data": {
    "id": "uuid",
    "user_id": "uuid",
    "project_id": "uuid",
    "username": "john_doe",
    "comment_text": "Great project!",
    "created_at": "2025-12-01T10:00:00Z"
  }
}
```

**Get Project Comments:**
```bash
GET /api/likes/comments/project/{project_id}?limit=100&offset=0

Response:
{
  "success": true,
  "data": {
    "project_id": "uuid",
    "total_comments": 15,
    "limit": 100,
    "offset": 0,
    "comments": [
      {
        "id": "uuid",
        "user_id": "uuid",
        "username": "john_doe",
        "comment_text": "Great project!",
        "created_at": "2025-12-01T10:00:00Z",
        "updated_at": "2025-12-01T10:00:00Z"
      }
    ]
  }
}
```

---

