"""
Download official CDC NHANES (1999-2000 through 2009-2010) SAS XPT files
and NCHS 2019 Public-Use Linked Mortality Files (.dat) plus official read-in script.

All URLs were verified directly from CDC NHANES data pages and
https://www.cdc.gov/nchs/linked-data/mortality-files/index.html.
Raw files are cached locally under data/nhanes_raw/ (gitignored) and every
downloaded URL, HTTP status, byte size, and SHA-256 is logged to
data/nhanes_raw/download_manifest.json.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List
import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RAW_DIR = REPO_ROOT / "data" / "nhanes_raw"
MANIFEST_PATH = RAW_DIR / "download_manifest.json"

# Verified official CDC NHANES component files per 2-year cycle
CYCLES: List[Dict[str, str]] = [
    {
        "cycle": "1999_2000",
        "demo": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1999/DataFiles/DEMO.xpt",
        "cbc": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1999/DataFiles/LAB25.xpt",
        "biopro": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1999/DataFiles/LAB18.xpt",
        "crp": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/1999/DataFiles/LAB11.xpt",
        "mortality": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_1999_2000_MORT_2019_PUBLIC.dat",
    },
    {
        "cycle": "2001_2002",
        "demo": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2001/DataFiles/DEMO_B.xpt",
        "cbc": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2001/DataFiles/L25_B.xpt",
        "biopro": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2001/DataFiles/L40_B.xpt",
        "crp": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2001/DataFiles/L11_B.xpt",
        "mortality": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2001_2002_MORT_2019_PUBLIC.dat",
    },
    {
        "cycle": "2003_2004",
        "demo": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/DEMO_C.xpt",
        "cbc": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/L25_C.xpt",
        "biopro": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/L40_C.xpt",
        "crp": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2003/DataFiles/L11_C.xpt",
        "mortality": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2003_2004_MORT_2019_PUBLIC.dat",
    },
    {
        "cycle": "2005_2006",
        "demo": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/DEMO_D.xpt",
        "cbc": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/CBC_D.xpt",
        "biopro": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/BIOPRO_D.xpt",
        "crp": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2005/DataFiles/CRP_D.xpt",
        "mortality": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2005_2006_MORT_2019_PUBLIC.dat",
    },
    {
        "cycle": "2007_2008",
        "demo": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/DEMO_E.xpt",
        "cbc": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/CBC_E.xpt",
        "biopro": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/BIOPRO_E.xpt",
        "crp": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2007/DataFiles/CRP_E.xpt",
        "mortality": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2007_2008_MORT_2019_PUBLIC.dat",
    },
    {
        "cycle": "2009_2010",
        "demo": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/DEMO_F.xpt",
        "cbc": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/CBC_F.xpt",
        "biopro": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/BIOPRO_F.xpt",
        "crp": "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public/2009/DataFiles/CRP_F.xpt",
        "mortality": "https://ftp.cdc.gov/pub/Health_Statistics/NCHS/datalinkage/linked_mortality/NHANES_2009_2010_MORT_2019_PUBLIC.dat",
    },
]

MORTALITY_READIN_URL = (
    "https://ftp.cdc.gov/pub/Health_statistics/NCHS/datalinkage/linked_mortality/R_ReadInProgramAllSurveys.R"
)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _download_file(client: httpx.Client, url: str, dest: Path, force: bool = False) -> Dict[str, Any]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return {
            "url": url,
            "path": str(dest.relative_to(REPO_ROOT)),
            "status": "cached",
            "size_bytes": dest.stat().st_size,
            "sha256": _sha256_file(dest),
        }

    resp = client.get(url)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return {
        "url": url,
        "final_url": str(resp.url),
        "path": str(dest.relative_to(REPO_ROOT)),
        "status": f"downloaded ({resp.status_code})",
        "size_bytes": len(resp.content),
        "sha256": _sha256_file(dest),
    }


def download_all(force: bool = False) -> Dict[str, Any]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    records: List[Dict[str, Any]] = []

    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        # 1. Official NCHS mortality read-in program
        readin_dest = RAW_DIR / "R_ReadInProgramAllSurveys.R"
        print(f"Fetching read-in program: {MORTALITY_READIN_URL}")
        records.append(_download_file(client, MORTALITY_READIN_URL, readin_dest, force=force))

        # 2. All 6 cycles
        for c in CYCLES:
            cycle_name = c["cycle"]
            print(f"\n--- Cycle {cycle_name} ---")
            for comp in ["demo", "cbc", "biopro", "crp", "mortality"]:
                url = c[comp]
                filename = url.rsplit("/", 1)[-1]
                dest = RAW_DIR / cycle_name / filename
                print(f"  [{comp}] {url}")
                rec = _download_file(client, url, dest, force=force)
                rec["cycle"] = cycle_name
                rec["component"] = comp
                records.append(rec)
                print(f"      -> {rec['status']} ({rec['size_bytes']:,} bytes)")

    manifest = {
        "downloaded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_files": len(records),
        "files": records,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest saved to {MANIFEST_PATH}")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download real NHANES + NCHS 2019 mortality files")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()
    try:
        download_all(force=args.force)
    except Exception as exc:
        print(f"ERROR downloading NHANES files: {exc}", file=sys.stderr)
        sys.exit(1)
