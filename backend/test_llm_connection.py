"""
LLM Connection Validation Script
==========================================
Standalone test for LM Studio connectivity with phi-3.1-mini-4k-instruct.

Usage:
    cd general-agent
    python -m backend.test_llm_connection

Checks:
  1. GET /v1/models  -- confirm server is up and model is listed
  2. POST /v1/chat/completions -- confirm inference works + measure latency
  3. Print model name, response preview, and latency
"""

import os
import sys
import time
import json
import httpx
from dotenv import load_dotenv

# Load .env from backend directory
_here = os.path.dirname(__file__)
load_dotenv(os.path.join(_here, ".env"))

BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1").rstrip("/")
MODEL    = os.getenv("LLM_MODEL",    "phi-3.1-mini-4k-instruct")
TIMEOUT  = int(os.getenv("LLM_TIMEOUT", 120))

DIVIDER = "-" * 60


def check_models() -> bool:
    """Step 1: GET /v1/models and verify model is listed."""
    print(f"\n{DIVIDER}")
    print("STEP 1: Checking LM Studio /v1/models")
    print(DIVIDER)
    url = f"{BASE_URL}/models"
    try:
        resp = httpx.get(url, timeout=6)
        resp.raise_for_status()
        data = resp.json()
        ids = [m.get("id", "") for m in data.get("data", [])]
        print(f"  Server URL : {BASE_URL}")
        print(f"  HTTP status: {resp.status_code} OK")
        print(f"  Models     : {ids}")

        loaded = any(MODEL in i or i in MODEL for i in ids)
        if loaded:
            print(f"  [PASS] Target model '{MODEL}' is listed")
            return True
        else:
            print(f"  [FAIL] Target model '{MODEL}' NOT found in list above")
            return False
    except httpx.ConnectError:
        print(f"  [FAIL] Cannot connect to {BASE_URL}")
        print("         -> Is LM Studio running?")
        return False
    except Exception as e:
        print(f"  [FAIL] Unexpected error: {e}")
        return False


def check_inference() -> bool:
    """Step 2: POST /v1/chat/completions and measure latency."""
    print(f"\n{DIVIDER}")
    print("STEP 2: Testing inference (expect <5s for phi-3.1-mini)")
    print(DIVIDER)

    url = f"{BASE_URL}/chat/completions"

    # NOTE: "stream" key intentionally omitted — LM Studio returns 400 with stream=False on some models
    # phi-3.1-mini supports system role natively
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are SANDHYA.AI autonomous agent."},
            {"role": "user",   "content": "Say exactly: PHI_READY"},
        ],
        "temperature": 0.1,
        "max_tokens": 16,
    }

    print(f"  Endpoint  : POST {url}")
    print(f"  Model     : {MODEL}")
    print(f"  Timeout   : {TIMEOUT}s")
    print(f"  Sending   : 'Say exactly: PHI_READY'")
    print(f"  Payload   : {json.dumps(payload, indent=2)[:400]}")
    print(f"  Note: 2 attempts with 5s wait if first request fails")

    MAX_ATTEMPTS = 2

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n  Attempt {attempt}/{MAX_ATTEMPTS} — Waiting for response...")
        t_start = time.monotonic()
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})

            latency = time.monotonic() - t_start

            if resp.status_code == 400:
                err = resp.json().get("error", resp.text)[:200]
                print(f"  Attempt {attempt} FAIL — HTTP 400: {err}")
                if attempt < MAX_ATTEMPTS:
                    print(f"  Waiting 10s for LM Studio to reload Mixtral...")
                    time.sleep(10)
                continue

            if resp.status_code != 200:
                print(f"\n  [FAIL] HTTP {resp.status_code}")
                print(f"  Error body: {resp.text[:600]}")
                return False

            result = resp.json()
            text = result["choices"][0]["message"]["content"].strip()
            model_used = result.get("model", MODEL)

            print(f"\n  [PASS] Inference succeeded! (attempt {attempt})")
            print(f"  Model name : {model_used}")
            print(f"  Latency    : {latency:.2f}s")
            print(f"  Response   : {text[:200]}")
            return True

        except httpx.TimeoutException:
            latency = time.monotonic() - t_start
            print(f"\n  Attempt {attempt} TIMED OUT after {latency:.1f}s")
            if attempt < MAX_ATTEMPTS:
                print(f"  Waiting 5s before retry...")
                time.sleep(5)
        except httpx.ConnectError:
            print(f"\n  [FAIL] Connection refused at {BASE_URL}")
            return False
        except Exception as e:
            print(f"\n  Attempt {attempt} ERROR: {type(e).__name__}: {e}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(5)

    print(f"\n  [FAIL] All {MAX_ATTEMPTS} attempts failed")
    return False


def main():
    print("=" * 60)
    print("  LLM CONNECTION TEST -- SANDHYA.AI")
    print("=" * 60)
    print(f"  Base URL : {BASE_URL}")
    print(f"  Model    : {MODEL}")
    print(f"  Timeout  : {TIMEOUT}s")

    ok1 = check_models()
    if not ok1:
        print(f"\n[ABORT] Cannot reach LM Studio. Skipping inference test.")
        sys.exit(1)

    ok2 = check_inference()

    print(f"\n{DIVIDER}")
    print("SUMMARY")
    print(DIVIDER)
    print(f"  Model check  : {'PASS' if ok1 else 'FAIL'}")
    print(f"  Inference    : {'PASS' if ok2 else 'FAIL'}")

    if ok1 and ok2:
        print("\n  ALL CHECKS PASSED - Backend LLM is ready!")
        sys.exit(0)
    else:
        print("\n  SOME CHECKS FAILED - See details above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
