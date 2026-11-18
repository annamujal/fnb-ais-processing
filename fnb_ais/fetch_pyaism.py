"""Download the pyAISm decoder from GitHub at a pinned commit.

pyAISm (https://github.com/pirpyn/pyAISm, MIT licence, (c) 2016 Pierre Payen) is a single
file without installer, so it is not on PyPI. This script saves the version used for the
datasets into external/pyAISm/ and checks its SHA-256.

Usage: python -m fnb_ais.fetch_pyaism
"""
import hashlib
import sys
import urllib.request
from pathlib import Path

REPO = 'https://github.com/pirpyn/pyAISm'
COMMIT = 'b4c727ca6b785da715c15572bcf083345fffc9f5'
SHA256 = '15dc1bd1f3a5e9278d0c6421fe590ebcd7d68bd3c80a14de20698bbe00f55644'
FILES = ('pyAISm.py', 'LICENSE')
DEFAULT_DIR = Path(__file__).resolve().parent.parent / 'external' / 'pyAISm'


def fetch(dest_dir=DEFAULT_DIR):
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        url = 'https://raw.githubusercontent.com/pirpyn/pyAISm/%s/%s' % (COMMIT, name)
        with urllib.request.urlopen(url, timeout=60) as resp:
            content = resp.read()
        if name == 'pyAISm.py' and hashlib.sha256(content).hexdigest() != SHA256:
            raise SystemExit('SHA-256 of %s does not match the pinned commit; not saved.' % url)
        (dest_dir / name).write_bytes(content)
        print('saved', dest_dir / name)
    return dest_dir / 'pyAISm.py'


if __name__ == '__main__':
    fetch(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DIR)
