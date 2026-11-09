"""Download the insurance outbound transcripts (CC BY-NC 4.0, research use) and unpack them.
Usage: python scripts/download.py data/"""
import sys, os, zipfile
from huggingface_hub import hf_hub_download

out = sys.argv[1] if len(sys.argv) > 1 else "data"
os.makedirs(out, exist_ok=True)
path = hf_hub_download("AIxBlock/92k-real-world-call-center-scripts-english", "insurance_outbound.zip",
                       repo_type="dataset", local_dir=out)
with zipfile.ZipFile(path) as z:
    z.extractall(out, members=[m for m in z.namelist() if m.startswith("insurance_outbound/")])
print("unpacked to", os.path.join(out, "insurance_outbound"))
