#!/usr/bin/env bash
# สั่งให้ script หยุดทำงานทันทีเมื่อเกิด error (set -e), ใช้ตัวแปรที่ยังไม่ประกาศ (set -u), หรือ command ใน pipe ล้มเหลว (set -o pipefail)
set -euo pipefail

# กำหนดค่าเริ่มต้นให้กับตัวแปรต่างๆ (ถ้ามี ENV ส่งมาจะใช้ค่าที่ส่งมา ถ้าไม่มีจะใช้ค่า default เหล่านี้)
IMAGE=${IMAGE:-ghcr.io/yuinakorn/pdf-split-worker}
PLATFORM=${PLATFORM:-linux/amd64}
VERSION=${VERSION:-}
ENV_FILE=${ENV_FILE:-.env}
WORKFLOW=${WORKFLOW:-docker-publish.yml}
REF=${REF:-}

# ตรวจสอบว่าในเครื่องมี GitHub CLI ติดตั้งอยู่หรือไม่ (ใช้สำหรับ trigger GitHub Actions)
if ! command -v gh >/dev/null 2>&1; then
  echo "error: GitHub CLI (gh) not found" >&2
  exit 1
fi

# ตรวจสอบว่าอยู่ใน git repo เพื่อหา ref ที่จะให้ GitHub build
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "error: git repository not found" >&2
  exit 1
fi

# ถ้าไม่ได้กำหนด REF มา ให้ใช้ชื่อ branch ปัจจุบัน
if [[ -z "$REF" ]]; then
  REF=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
  if [[ -z "$REF" || "$REF" == "HEAD" ]]; then
    REF="main"
  fi
fi

# เตรียมรายการ build args สำหรับส่งให้ GitHub Actions
declare -a BUILD_ARGS=()

# เช็คว่าถ้าไม่เจอไฟล์ .env แต่เจอ .env.local ให้ใช้ .env.local แทน
if [[ ! -f "$ENV_FILE" && "$ENV_FILE" == ".env" && -f ".env.local" ]]; then
  echo "info: env file '.env' not found; falling back to '.env.local'" >&2
  ENV_FILE=".env.local"
fi

# อ่านไฟล์ Environment (.env หรือ .env.local) เพื่อดึงค่าตัวแปร
if [[ -f "$ENV_FILE" ]]; then
  while IFS='=' read -r raw_key raw_value; do
    # ข้ามบรรทัดว่างหรือบรรทัดที่เป็น comment (#)
    if [[ -z "$raw_key" || "$raw_key" =~ ^[[:space:]]*# ]]; then
      continue
    fi

    # ตัดช่องว่างหน้า-หลัง key และ value ออก
    key=$(echo "$raw_key" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    value=$(echo "${raw_value:-}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

    # กรองเอาเฉพาะตัวแปรที่ขึ้นต้นด้วย NEXT_PUBLIC_ เท่านั้นเพื่อความปลอดภัย
    # หมายเหตุ: สำหรับโปรเจค Python/FastAPI อาจจะไม่มี NEXT_PUBLIC_ แต่โค้ดนี้ copy มาจากต้นแบบ
    # ถ้าต้องการส่งค่าอื่นๆ อาจจะต้องปรับแก้ pattern ตรงนี้
    if [[ "$key" == NEXT_PUBLIC_* ]]; then
      # ลบเครื่องหมายคำพูด (quotes) ที่อาจจะครอบ value อยู่ออก
      dq='"'
      sq="'"
      if [[ ${value} == ${dq}*${dq} ]]; then
        value=${value#${dq}}
        value=${value%${dq}}
      fi
      if [[ ${value} == ${sq}*${sq} ]]; then
        value=${value#${sq}}
        value=${value%${sq}}
      fi

      # เพิ่มตัวแปรลงในรายการ build arguments
      BUILD_ARGS+=("$key=$value")
    fi
  done < "$ENV_FILE"
else
  echo "warn: env file '$ENV_FILE' not found; skipping NEXT_PUBLIC_* build args" >&2
fi

# รวม build args ให้เป็น multiline string สำหรับ workflow input
BUILD_ARGS_INPUT=""
if [[ ${#BUILD_ARGS[@]} -gt 0 ]]; then
  BUILD_ARGS_INPUT=$(printf '%s\n' "${BUILD_ARGS[@]}")
fi

# สั่ง trigger GitHub Actions ให้ build และ push image แทนการ build ในเครื่อง
declare -a GH_ARGS=(workflow run "$WORKFLOW" --ref "$REF" -f "image=$IMAGE" -f "platform=$PLATFORM")
if [[ -n "$VERSION" ]]; then
  GH_ARGS+=(-f "version=$VERSION")
fi
if [[ -n "$BUILD_ARGS_INPUT" ]]; then
  GH_ARGS+=(-f "build_args=$BUILD_ARGS_INPUT")
fi

echo "info: triggering GitHub Actions build on ref '$REF' using workflow '$WORKFLOW'" >&2
gh "${GH_ARGS[@]}"
