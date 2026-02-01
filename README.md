# PDF Split Worker (FastAPI)

This project is a dedicated **PDF Processing Worker** built with FastAPI. It is designed to run alongside a main application (like Next.js) to handle heavy PDF splitting and text extraction tasks asynchronously.

## 🏗️ Project Structure

```
.
├── app/                    # FastAPI Application Code
│   ├── main.py             # Entry point / API Routes
│   └── ...
├── build.sh                # Local script to trigger remote GitHub Actions build
├── deploy.txt              # Guide for deploying to production server
├── docker-compose.yml      # Local development configuration
├── docker-compose.prod.yml # Production configuration (uses GHCR image)
├── DEPLOYMENT.md           # Documentation for CI/CD strategy
├── ID_EXTRACTION_LOGIC.md  # Documentation for ID extraction algorithm
├── NEXTJS_INTEGRATION.md   # Guide for integrating with Next.js
└── ...
```

## 🚀 How it Works

1.  **Shared Volume**: This worker shares a Docker volume (`pdf_shared_volume`) with the main Next.js app.
2.  **Input**: The Next.js app saves a PDF to `/shared/inbox`.
3.  **Trigger**: Next.js calls `POST /process/{job_id}` on this worker.
4.  **Processing**: This worker splits the PDF and saves individual pages to `/shared/output`.
5.  **Output**: Next.js reads the processed files from the shared volume.

## 💻 Local Development

1.  **Run with Docker**:
    ```bash
    docker compose up --build
    ```
    The API will be available at `http://localhost:8000`.

2.  **Run with Python (Directly)**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload
    ```

## 🔌 Integration with Next.js

To connect this worker with your Next.js application, both services must share the same **Network** and **Volume**.

### Requirements
1.  **Shared Network**: Create an external network named `pdf_network`.
2.  **Shared Volume**: Create an external volume named `pdf_shared_volume`.

### Setup Steps
1.  Create the shared resources manually first:
    ```bash
    docker network create pdf_network
    docker volume create pdf_shared_volume
    ```

2.  Configure your Next.js `docker-compose.yml` to use them (see `NEXTJS_INTEGRATION.md` for full details).

## 📦 Deployment (Production)

We use a **Hybrid Remote Build** strategy:
1.  Run `./build.sh` on your machine to trigger a build on GitHub Actions.
2.  On the server, run `docker compose pull` and `docker compose up -d` using `docker-compose.prod.yml`.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the full deployment guide.
