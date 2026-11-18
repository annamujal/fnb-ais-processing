"""Load the upstream pyAISm decoder and apply the two changes the datasets rely on.

`from fnb_ais.ais_backend import pyAISm` gives the upstream module (pinned commit, see
fetch_pyaism.py) with these run-time changes; the upstream file itself is not modified:

1. Checksum tolerance. The logger writes the checksum and the four digits mmss one after
   the other; a checksum cut to one digit is compared on its first digit only, and a
   checksum with more than two digits is not compared. Upstream rejects both.
2. Message 5: the field 'destination' (payload bits 302-419) is added. Upstream returns
   only the DTE flag. (The AIS field has 20 characters, bits 302-421; see KNOWN_ISSUES.md.)
3. Message 24 part B (any part number other than 0) of a vessel with fewer than 163 payload
   bits is rejected with a ValueError, because the position-fixing device field (bits
   162-164) is missing. Upstream would decode it as a message without that field.

The path of pyAISm.py can be set with the environment variable FNB_PYAISM_PATH.
"""
import hashlib
import importlib.util
import os
import warnings
from pathlib import Path

from .fetch_pyaism import DEFAULT_DIR, SHA256


def _locate():
    path = Path(os.environ.get('FNB_PYAISM_PATH') or DEFAULT_DIR / 'pyAISm.py')
    if not path.is_file():
        raise ImportError(
            'pyAISm.py not found at %s. Run "python -m fnb_ais.fetch_pyaism" to download it '
            'from GitHub, or set FNB_PYAISM_PATH.' % path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != SHA256:
        warnings.warn('%s is not the pyAISm version used for the datasets (commit pinned in '
                      'fetch_pyaism.py); results may differ.' % path)
    return path


def _patch(m):
    original_get_checksum = m.get_checksum
    original_decod_data = m.decod_data

    def get_checksum(msg):
        received = original_get_checksum(msg)
        computed = m.compute_checksum(msg)
        if len(received) > 2:                  # digits after the checksum: not compared
            return computed
        if len(received) < 2 and computed[0] == received[0]:   # one digit: first digit only
            return computed
        return received

    def decod_data(bits):
        data = original_decod_data(bits)
        if data.get('type') == 5:
            data['destination'] = m.decod_str(bits[302:420])
        elif data.get('type') == 24 and data['partno'] != 0 and len(bits) < 163 \
                and not m.is_auxiliary_craft(data['mmsi']):
            raise ValueError('truncated message 24 part B (%d bits)' % len(bits))
        return data

    m.get_checksum = get_checksum
    m.decod_data = decod_data
    return m


def _load():
    path = _locate()
    spec = importlib.util.spec_from_file_location('pyAISm', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return _patch(module)


pyAISm = _load()
