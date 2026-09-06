#!/usr/bin/env python3
"""PLACEMENTOPENING1A — read-only BRIGHT diagnostic.

Adds preview->finished luma placement deltas to the existing LOWKEY cohort audit.
The values compare two different pipeline spaces, so they are proxies only.
They MUST NOT be interpreted as capture EV or used as live authority.
"""
from __future__ import annotations
import argparse, importlib.util, json, math
from pathlib import Path


def load_auditor(path: Path):
    spec = importlib.util.spec_from_file_location("lowkey_audit1a", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load cohort auditor")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def log2_ratio(dst, src):
    if dst is None or src is None or dst <= 0 or src <= 0:
        return None
    return math.log2(float(dst) / float(src))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--auditor", type=Path,
                    default=Path(__file__).with_name("m9edgeplacementbestfit1a_bright_lowkey_cohort_audit1a.py"))
    args = ap.parse_args()
    result = load_auditor(args.auditor).audit(args.root)
    rows = []
    for row in result["rows"]:
        r = dict(row)
        r["finishedVsPreviewMedianProxyEv"] = log2_ratio(
            r.get("finishedGlobalMedianY"), r.get("previewGlobalMedianY"))
        r["finishedVsPreviewQ95ProxyEv"] = log2_ratio(
            r.get("finishedGlobalQ95Y"), r.get("previewGlobalQ95Y"))
        rows.append(r)
    print(json.dumps({
        "schema": "m9edgeplacementbestfit1a.bright_placementopening1a.research.v1",
        "mode": "offline_diagnostic_only_no_capture_or_pixel_mutation",
        "authority": "none_proxy_only",
        "warning": "preview and finished Y are different pipeline spaces; deltas are placement proxies, not exposure EV",
        "rows": rows,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
