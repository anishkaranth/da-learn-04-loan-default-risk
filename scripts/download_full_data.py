#!/usr/bin/env python3
"""Download the complete Lending Club 2007-2011 loan file into data/raw_full/ (git-ignored).

Source: Kaggle "Lending Club Loan Dataset 2007-2011" (imsparsh/lending-club-loan-dataset-2007-2011), i.e. the
LoanStats3a export that LendingClub published. No Kaggle API key is needed: the identical file is mirrored on GitHub.
"""
import hashlib, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data/raw_full"
MIRRORS = [
    "https://raw.githubusercontent.com/anushkaparadkar/lending-club-case-study/master/loan.csv",
    "https://raw.githubusercontent.com/akashkriplani/lending-club-case-study/main/loan.csv",
]
SHA256 = "a57286c2a5f329930c875366790c8f5291be7525b7b4e2355dcbfb2e73af6f04"  # 34,813,575 bytes, 39,717 loans x 111 columns


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / "loan.csv"
    if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == SHA256:
        print("already present:", dest); return
    for url in MIRRORS:
        try:
            print("downloading", url)
            data = urllib.request.urlopen(url, timeout=120).read()
        except Exception as e:  # try the next mirror
            print("  failed:", e); continue
        digest = hashlib.sha256(data).hexdigest()
        if digest != SHA256:
            print("  checksum mismatch", digest); continue
        dest.write_bytes(data)
        print(f"saved {dest} ({len(data):,} bytes, sha256 ok)"); return
    sys.exit("all mirrors failed")


if __name__ == "__main__":
    main()
