# FNB-UPC AIS processing

Scripts that turn the raw NMEA* files of the Barcelona School of Nautical Studies AIS
station (doi:10.34810/DATA3419) into decoded and filtered tables (doi:10.34810/DATA2026).

## Scope
This repository contains the algorithms that decode the raw NMEA* dataset
(doi:10.34810/DATA3419) and a first filtering step. It does **not** contain the processing that
produces the database of doi:10.34810/DATA2026 as described in Table 5 of the paper (ISO
`receiver_timestamp`, `accuracy`, `device`, `eta`, speed in knots, ...).

| Stage | Code | Output | Units of speed and ROT |
|---|---|---|---|
| 1. Decoding | `fnb_ais.decode` (this repository) | `decoded_*.txt` | speed in 1/10 knot, ROT raw AIS code |
| 2. Filtering | `fnb_ais.preprocess` (this repository) | `filtered_*.csv`, `static_*.csv` | same as stage 1 |

## Input format
Hourly files `YYYYMMDDHHAIS.txt`; each line is one NMEA sentence followed by four digits
`mmss` (minute and second of reception, local Raspberry Pi clock):
`!AIVDM,1,1,,B,4028jJ1vM=aTN09cHDGdgrg028B8,0*303630`

## Usage
    pip install -r requirements.txt            # Python >= 3.11
    python -m fnb_ais.fetch_pyaism             # downloads pyAISm from GitHub (pinned commit)
    python -m fnb_ais.decode     --raw-dir data/raw --out-dir data/interim
    python -m fnb_ais.preprocess --interim-dir data/interim --out-dir data/processed --class ClassA
    python -m fnb_ais.preprocess --interim-dir data/interim --out-dir data/processed --class ClassB
    pytest

`decode` writes `decoded_{4,123,5,18,24A,24B}.txt` and `decode_summary.json` (a count of every
outcome: written, skipped, undecodable). `preprocess` writes `filtered_<Class>.csv`,
`static_<Class>.csv` and a summary of rows removed at each step.
Parameters (message types, geographic box, not-available codes) are in `config/default.toml`. The geographic box is the one given in the paper (34.98 < lat < 44.60, -3.51 < lon < 11.07).

## Units
Speed: 1/10 knot as decoded; ROT: raw AIS code (Class A); course, heading: degrees;
lat/lon: decimal degrees; dimensions: metres.

## Provenance and checks
The refactoring was verified to give byte-identical outputs to the original scripts (run with their own narrower geographic box) on a full
hour of data (`tests/` holds a 3000-line excerpt). See `KNOWN_ISSUES.md` for behaviour that was
kept deliberately and `NOTICE.md` for third-party code. 
## Licence
MIT (see `LICENSE`); The decoder pyAISm (MIT, P. Payen) is downloaded from GitHub, not redistributed here.

## Layout
    fnb_ais/decode.py          step 1: NMEA* -> decoded_*.txt
    fnb_ais/preprocess.py      step 2: decoded_*.txt -> filtered_*.csv, static_*.csv
    fnb_ais/ais_backend.py     loads pyAISm from external/ and applies three run-time changes
    fnb_ais/fetch_pyaism.py    downloads pyAISm from GitHub (pinned commit, SHA-256 checked)
    fnb_ais/rows.py            output row formats
    config/default.toml        parameters
    tests/                     regression tests and a 3000-line excerpt of one hour
    KNOWN_ISSUES.md, NOTICE.md, CITATION.cff, LICENSE
`pip install -e .` also installs the commands `fnb-ais-fetch-pyaism`, `fnb-ais-decode` and
`fnb-ais-preprocess`. The tests need pyAISm to be downloaded first.

## How to cite
If you use this code, please cite the raw dataset that it decodes:

Mujal-Colilles, Anna; Fonollosa, Jordi; Vigo, Marc; Castells-Sanabra, Marcella; Llull, Toni (2026).
*AIS NMEA raw messages from the Barcelona School of Nautical Studies (FNB-UPC)*, V1.
CORA.Repositori de Dades de Recerca. https://doi.org/10.34810/DATA3419

and this repository (see `CITATION.cff`; the DOI is given by Zenodo for each release).
