# Deployment Strategy & CI/CD Guide

This document outlines the "Hybrid Remote Build" strategy used in this project. It combines the convenience of a local build script with the power of cloud-based CI/CD.

## 📌 Concept Overview

Instead of building Docker images locally and pushing them (which uses local bandwidth and resources), we offload the build process to **GitHub Actions**, but we trigger it **manually from the local machine** when we are ready.

**The Flow:**
1.  **Dev Machine**: You run `./build.sh` (wraps `gh` CLI).
2.  **GitHub Actions**: Receives the trigger, builds the Docker image, and pushes it to **GHCR** (GitHub Container Registry).
3.  **Production Server**: Pulls the image from GHCR and runs it.

---

## 🛠️ Components

### 1. GitHub Actions Workflow
**File:** `.github/workflows/docker-publish.yml`
This file defines the build pipeline. Key configuration:
- **Trigger**: `workflow_dispatch` (allows manual trigger).
- **Permissions**: `packages: write` (to push to GHCR).
- **Image Name**: Matches the repository name (e.g., `ghcr.io/user/repo`) to avoid permission issues.

### 2. Local Trigger Script
**File:** `build.sh`
A convenience script that replaces `docker build`.
- Checks if you have `gh` CLI installed.
- Reads `.env` to inject build arguments.
- Runs `gh workflow run` to start the process on GitHub.

### 3. Production Configuration
**File:** `docker-compose.prod.yml`
Optimized for the server.
- **Image**: uses the full GHCR path (`ghcr.io/...`).
- **Restart**: `always` (auto-restart on crash/reboot).
- **No Build**: Does not contain `build: context`.

---

## 🚀 How to Setup in a New Project

### Step 1: Initialize Files
Copy the following files from this project:
- `.github/workflows/docker-publish.yml`
- `build.sh` (Running `chmod +x build.sh` is required)
- `docker-compose.prod.yml`

### Step 2: Configure GitHub Repository
1.  Go to **Settings** > **Actions** > **General**.
2.  Scroll to **Workflow permissions**.
3.  Select **Read and write permissions**.
4.  Save.

### Step 3: Deployment (On Server)
1.  Copy `docker-compose.prod.yml` to the server as `docker-compose.yml`.
2.  **Login to Registry**:
    ```bash
    # You need a Personal Access Token (PAT) with 'read:packages' scope
    echo $CR_PAT | docker login ghcr.io -u YOUR_USERNAME --password-stdin
    ```
3.  **Start Services**:
    ```bash
    docker compose pull
    docker compose up -d
    ```

---

## 💡 Why this approach?
- **Speed**: Doesn't upload the context from your machine; GitHub pulls the code directly.
- **Consistency**: Builds always happen in a clean environment (Linux/AMD64).
- **Storage**: Images are stored in GHCR, not clogging up your local disk.
- **Simplicity**: You still just run one command (`./build.sh`) to release.
