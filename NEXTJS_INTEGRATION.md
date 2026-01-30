# Next.js Integration Guide

This document outlines how the Next.js application should integrate with the FastAPI PDF Worker.

## Architecture Overview
- **FastAPI Worker**: Runs in a separate container, handles PDF processing.
- **Shared Volume**: Both apps share a volume path (`/shared` inside containers) to exchange files.
- **Communication**: Next.js calls FastAPI via internal HTTP requests (Docker Network).

## 1. Docker Configuration (Critical)
Update your `docker-compose.yml` to mount the shared volume created by the worker service.

```yaml
services:
  your_nextjs_app:
    # ... your config ...
    volumes:
      # Mount the named volume to the same path inside your container
      - pdf_shared_volume:/shared

# Define the external volume existing from the worker project
volumes:
  pdf_shared_volume:
    external: true
```

## 2. API Endpoints (FastAPI)
Base URL: `http://pdf_worker:8000` (Internal Docker Hostname)

### A. Trigger Processing
Next.js should upload the PDF to `/shared/inbox/{filename}.pdf` **before** calling this API.

- **Endpoint**: `POST /process/{job_id}`
- **Param**: `job_id` (e.g., `tax-2568-1`). Note: System extracts the year from this string (e.g. "2568").
- **Example**:
  ```typescript
  // 1. Save uploaded file to /shared/inbox/tax-2568-001.pdf
  // 2. Call API
  await fetch('http://pdf_worker:8000/process/tax-2568-001', { method: 'POST' });
  ```

### B. Setup File Retrieval (Metadata Check)
Use this to confirm file existence before serving it to the user.

- **Endpoint**: `GET /files/{year}/{cid}`
- **Response**:
  ```json
  {
    "status": "found",
    "year": "2568",
    "cid": "1234567890123",
    "filename": "1234567890123.pdf",
    "full_path": "/shared/output/2568/1234567890123.pdf"
  }
  ```

### C. Output Listing
Tools for auditing processed files and checking availability.

#### List Years (Folders)
- **Endpoint**: `GET /output`
- **Response**: `["2568", "2569"]`
- Use this to create a "Select Year" dropdown in your admin UI.

#### List Files in Year
- **Endpoint**: `GET /output/{year}`
- **Response**: `["1234.pdf", "5678.pdf"]`

### D. Maintenance & Cleanup

#### Clear Output by Year
- **Endpoint**: `DELETE /output/{year}`
- **Action**: Deletes the **entire folder** for that year in `/shared/output`. Use with caution.
- **Example**: `DELETE /output/2568`

#### Inbox Management
- **List Inbox Files**: `GET /inbox`
  - Returns: `["file1.pdf", "file2.pdf"]`
- **Delete Inbox File**: `DELETE /inbox/{filename}`
  - Example: `DELETE /inbox/tax-2568-1.pdf`

## 3. Serving Files Securely (The "Right Way")
**Do NOT** expose the shared volume publicly. Create a Next.js API Route to acting as a secure proxy.

**File**: `app/api/pdf/[year]/[cid]/route.ts`

```typescript
import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
// import { auth } from '@/auth'; // Your auth library

export async function GET(
  request: NextRequest,
  { params }: { params: { year: string; cid: string } }
) {
  // 1. SECURITY CHECK (Crucial!)
  // const session = await auth();
  // if (!session || (session.user.cid !== params.cid && !session.user.isAdmin)) {
  //   return new NextResponse("Forbidden", { status: 403 });
  // }

  // 2. Metadata Check (Optional but recommended)
  // You can call the FastAPI worker to verify logic/logging if needed, 
  // or just check file existence directly since we have the volume mounted.
  
  // 3. Read File from Shared Volume
  // Note: We use the path directly because we mounted the volume.
  const filePath = path.join('/shared/output', params.year, `${params.cid}.pdf`);

  if (!fs.existsSync(filePath)) {
    return new NextResponse("File not found", { status: 404 });
  }

  // 4. Stream File to Browser
  const fileBuffer = fs.readFileSync(filePath);
  
  return new NextResponse(fileBuffer, {
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `inline; filename="${params.cid}.pdf"`,
    },
  });
}
```

## Summary Checklist for Next.js Team
- [ ] Add `pdf_shared_volume` to `docker-compose.yml`.
- [ ] Implement file upload logic to save to `/shared/inbox`.
- [ ] Implement `POST` call to trigger processing.
- [ ] Implement `DELETE /inbox/...` to clean up input files after processing (optional).
- [ ] Implement Secure API Route (`/api/pdf/...`) to serve files from `/shared/output`.
- [ ] **Ensure strict permission checks** in the API Route to prevent IDOR attacks.
- [ ] Use `GET /output` to populate year selection UI.
- [ ] Use `GET /output/{year}` to audit processed files.
