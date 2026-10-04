#!/usr/bin/env python3
"""Recover Leica M9 1.216 repeating XOR key from public M9 + M Monochrom ciphertexts.

No firmware bytes or historical key bytes are embedded here.

The M9 1.216 and original M Monochrom 1.022 updaters use the same 1021-byte
repeating XOR stream and contain a byte-identical BODY payload at different
file offsets.  For equal plaintext BODY byte P[i]:

    C_m9[A+i] ^ C_mm[B+i]
      = K[(A+i) mod N] ^ K[(B+i) mod N]

With N=1021 and (B-A) mod N = 69, gcd(69,1021)=1.  The equations therefore
form one cycle covering every key byte and determine the key up to a single
constant byte.  Requiring the M9 plaintext to start with the known PWAD magic
resolves that final ambiguity.  Canonical SHA-256 values then independently
verify the recovered key and decrypted firmware.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

PERIOD = 1021
M9_BODY_OFFSET = 0x00451050
MM_BODY_OFFSET = 0x00119350
BODY_SIZE = 143_418

EXPECTED_M9_RAW_SHA256 = "c3d30d7124abe6a3674cf2095719c178454b8773b1454cb70cf54ae468024da4"
EXPECTED_MM_RAW_SHA256 = "53330385edfbfb9beeffa06645bffa2789e27dda614869107698919464f80ad8"
EXPECTED_KEY_SHA256 = "595c49ebabdaafcde7cc6cbd6aa7a37092d7c2ad4ca47d0d8bc57a04a5bed3a1"
EXPECTED_M9_DECRYPTED_SHA256 = "4f962bb7799ad9a6745ab36c2a3ba59757bfcbd205f50472ddf1b904a5756d20"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decrypt(cipher: bytes, key: bytes) -> bytes:
    n = len(key)
    return bytes(value ^ key[i % n] for i, value in enumerate(cipher))


def build_key_edges(m9: bytes, mm: bytes) -> tuple[list[int], int]:
    if len(m9) < M9_BODY_OFFSET + PERIOD:
        raise ValueError("M9 ciphertext is too short for BODY equations")
    if len(mm) < MM_BODY_OFFSET + PERIOD:
        raise ValueError("Monochrom ciphertext is too short for BODY equations")

    delta = (MM_BODY_OFFSET - M9_BODY_OFFSET) % PERIOD
    if math.gcd(delta, PERIOD) != 1:
        raise RuntimeError(f"BODY offset delta {delta} does not span the key period")

    # edge[a] = K[a] XOR K[(a+delta) mod PERIOD]
    edge = [None] * PERIOD
    for i in range(PERIOD):
        a = (M9_BODY_OFFSET + i) % PERIOD
        edge[a] = m9[M9_BODY_OFFSET + i] ^ mm[MM_BODY_OFFSET + i]
    if any(x is None for x in edge):
        raise RuntimeError("incomplete key equation graph")
    return [int(x) for x in edge], delta


def key_from_seed(edge: list[int], delta: int, seed: int) -> bytes:
    key: list[int | None] = [None] * PERIOD
    key[0] = seed
    cur = 0
    for _ in range(PERIOD - 1):
        nxt = (cur + delta) % PERIOD
        if key[nxt] is not None:
            raise RuntimeError("key equation cycle closed early")
        key[nxt] = int(key[cur]) ^ edge[cur]
        cur = nxt

    # Last equation must close back to key[0].
    nxt = (cur + delta) % PERIOD
    if nxt != 0:
        raise RuntimeError("key equation graph did not form a single cycle")
    if (int(key[cur]) ^ edge[cur]) != seed:
        raise RuntimeError("inconsistent shared-BODY equations")
    return bytes(int(x) for x in key)


def recover_key(m9: bytes, mm: bytes) -> tuple[bytes, int, list[int]]:
    edge, delta = build_key_edges(m9, mm)
    candidates: list[tuple[int, bytes]] = []
    for seed in range(256):
        key = key_from_seed(edge, delta, seed)
        if bytes(m9[i] ^ key[i % PERIOD] for i in range(4)) == b"PWAD":
            candidates.append((seed, key))
    if len(candidates) != 1:
        raise RuntimeError(f"expected one PWAD-compatible key, got {len(candidates)}")
    seed, key = candidates[0]
    return key, delta, [seed]


def verify_shared_body(m9_plain: bytes, mm_plain: bytes) -> bool:
    a = m9_plain[M9_BODY_OFFSET:M9_BODY_OFFSET + BODY_SIZE]
    b = mm_plain[MM_BODY_OFFSET:MM_BODY_OFFSET + BODY_SIZE]
    return len(a) == BODY_SIZE and a == b


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("m9_upd", type=Path)
    ap.add_argument("mm_upm", type=Path)
    ap.add_argument("--m9-out", type=Path)
    ap.add_argument("--mm-out", type=Path)
    ap.add_argument("--key-out", type=Path)
    ap.add_argument("--meta-out", type=Path)
    ap.add_argument("--allow-noncanonical", action="store_true")
    args = ap.parse_args()

    m9 = args.m9_upd.read_bytes()
    mm = args.mm_upm.read_bytes()
    m9_raw_hash = sha256(m9)
    mm_raw_hash = sha256(mm)

    if not args.allow_noncanonical:
        if m9_raw_hash != EXPECTED_M9_RAW_SHA256:
            raise SystemExit(f"M9 raw SHA mismatch: {m9_raw_hash}")
        if mm_raw_hash != EXPECTED_MM_RAW_SHA256:
            raise SystemExit(f"Monochrom raw SHA mismatch: {mm_raw_hash}")

    key, delta, seeds = recover_key(m9, mm)
    key_hash = sha256(key)
    if not args.allow_noncanonical and key_hash != EXPECTED_KEY_SHA256:
        raise SystemExit(f"recovered key SHA mismatch: {key_hash}")

    m9_plain = decrypt(m9, key)
    mm_plain = decrypt(mm, key)
    m9_plain_hash = sha256(m9_plain)
    shared_body = verify_shared_body(m9_plain, mm_plain)

    if m9_plain[:4] != b"PWAD" or mm_plain[:4] != b"PWAD":
        raise SystemExit("decryption did not yield PWAD headers")
    if not shared_body:
        raise SystemExit("decrypted M9 and Monochrom BODY payloads do not match")
    if not args.allow_noncanonical and m9_plain_hash != EXPECTED_M9_DECRYPTED_SHA256:
        raise SystemExit(f"M9 decrypted SHA mismatch: {m9_plain_hash}")

    meta = {
        "schema": "m9.sharedbody-key-recovery.v1",
        "period": PERIOD,
        "m9_body_offset": hex(M9_BODY_OFFSET),
        "mm_body_offset": hex(MM_BODY_OFFSET),
        "body_size": BODY_SIZE,
        "offset_delta_mod_period": delta,
        "gcd_delta_period": math.gcd(delta, PERIOD),
        "pw_ad_seed_candidates": seeds,
        "m9_raw_sha256": m9_raw_hash,
        "mm_raw_sha256": mm_raw_hash,
        "key_sha256": key_hash,
        "m9_decrypted_sha256": m9_plain_hash,
        "mm_decrypted_sha256": sha256(mm_plain),
        "shared_body_exact": shared_body,
        "m9_magic": m9_plain[:4].decode("ascii", "replace"),
        "mm_magic": mm_plain[:4].decode("ascii", "replace"),
    }

    print(json.dumps(meta, indent=2))
    if args.m9_out:
        args.m9_out.write_bytes(m9_plain)
    if args.mm_out:
        args.mm_out.write_bytes(mm_plain)
    if args.key_out:
        args.key_out.write_bytes(key)
    if args.meta_out:
        args.meta_out.write_text(json.dumps(meta, indent=2) + "\n")


if __name__ == "__main__":
    main()
