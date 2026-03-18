"""Quick test to debug Kalshi API authentication."""
import time
import base64
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import config


def test_auth():
    print("=== Kalshi Auth Debug ===\n")

    # 1. Check config values
    key_id = config.KALSHI_API_KEY_ID
    key_path = config.KALSHI_RSA_PRIVATE_KEY_PATH
    base_url = config.KALSHI_BASE_URL

    print(f"API Key ID: {key_id[:8]}...{key_id[-4:]}" if len(key_id) > 12 else f"API Key ID: '{key_id}'")
    print(f"API Key ID length: {len(key_id)}")
    print(f"API Key ID repr: {repr(key_id[:12])}...")
    print(f"Key path: {key_path}")
    print(f"Base URL: {base_url}")
    print()

    # 2. Load private key
    try:
        with open(key_path, "rb") as f:
            raw = f.read()
        print(f"PEM file size: {len(raw)} bytes")
        print(f"PEM starts with: {repr(raw[:40])}")
        private_key = serialization.load_pem_private_key(raw, password=None)
        print(f"Private key loaded OK (type: {type(private_key).__name__})")
        print(f"Key size: {private_key.key_size} bits")
    except Exception as e:
        print(f"FAILED to load private key: {e}")
        return
    print()

    # 3. Try signing and making a request
    method = "GET"
    path = "/trade-api/v2/portfolio/balance"
    timestamp_ms = int(time.time() * 1000)

    message = f"{timestamp_ms}{method}{path}"
    print(f"Signing message: {message[:60]}...")

    try:
        signature = private_key.sign(
            message.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
        sig_b64 = base64.b64encode(signature).decode("utf-8")
        print(f"Signature generated OK ({len(sig_b64)} chars)")
    except Exception as e:
        print(f"FAILED to sign: {e}")
        return
    print()

    # 4. Make the actual request
    url = f"{base_url}/portfolio/balance"
    headers = {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": sig_b64,
        "KALSHI-ACCESS-TIMESTAMP": str(timestamp_ms),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    print(f"Request: GET {url}")
    print(f"Headers sent:")
    print(f"  KALSHI-ACCESS-KEY: {key_id[:8]}...{key_id[-4:]}")
    print(f"  KALSHI-ACCESS-TIMESTAMP: {timestamp_ms}")
    print()

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        print(f"Response status: {resp.status_code}")
        print(f"Response body: {resp.text[:500]}")
    except Exception as e:
        print(f"Request failed: {e}")


if __name__ == "__main__":
    test_auth()
