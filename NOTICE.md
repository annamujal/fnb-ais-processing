# Third-party code

The decoder **pyAISm** (https://github.com/pirpyn/pyAISm, MIT licence, Copyright (c) 2016
Pierre Payen) is not included in this repository. `python -m fnb_ais.fetch_pyaism` downloads
commit `b4c727c` into `external/pyAISm/` and checks its SHA-256; its licence is saved next to it.
`fnb_ais/ais_backend.py` loads it and applies two changes at run time (checksum tolerance and
the destination field of message 5); the downloaded file is never modified.
