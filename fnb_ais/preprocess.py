"""Step 2: filter the decoded files and build the dynamic and static tables.

Input : decoded_123.txt + decoded_5.txt (ClassA) or decoded_18.txt + decoded_24B.txt (ClassB),
        written by fnb_ais.decode.
Output: filtered_<Class>.csv (dynamic messages) and static_<Class>.csv (one row per MMSI and day)
        and preprocess_summary.json (rows removed at each step).

Usage : python -m fnb_ais.preprocess --interim-dir DIR --out-dir DIR --class ClassA|ClassB
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .config import load_config

COLUMNS = {
    'ClassA': {
        'dynamic_file': 'decoded_123.txt',
        'dynamic': ['date', 'second_sent', 'type', 'mmsi', 'status', 'turn', 'speed',
                    'lon', 'lat', 'course', 'heading'],
        'static_file': 'decoded_5.txt',
        'static': ['time_stamp', 'type', 'mmsi', 'imo', 'shipname', 'shiptype', 'to_bow',
                   'to_stern', 'to_port', 'to_starboard', 'draught', 'destination'],
    },
    'ClassB': {
        'dynamic_file': 'decoded_18.txt',
        'dynamic': ['date', 'second_sent', 'type', 'mmsi', 'speed', 'lon', 'lat',
                    'course', 'heading'],
        'static_file': 'decoded_24B.txt',
        'static': ['time_stamp', 'type', 'mmsi', 'shiptype', 'to_bow', 'to_stern',
                   'to_port', 'to_starboard'],
    },
}


def filter_dynamic(mes, cfg, mtype, summary):
    """Apply the geographic box, convert 'not available' codes to NaN, drop empty rows
    and duplicates. Returns the filtered DataFrame."""
    box, nad = cfg['geographic_box'], cfg['not_available']
    summary['dynamic_initial'] = len(mes)

    # Positions outside the box are removed. NaD latitude (91) and longitude (181) lie
    # outside the box, so those messages are removed here, not converted to NaN.
    mes = mes[~((mes.lat < box['lat_min']) | (mes.lat > box['lat_max']))]
    mes = mes[~((mes.lon < box['lon_min']) | (mes.lon > box['lon_max']))]
    summary['dynamic_after_box'] = len(mes)

    mes = mes.copy()
    mes['lat'] = mes['lat'].replace(nad['lat'], np.nan)
    mes['lon'] = mes['lon'].replace(nad['lon'], np.nan)
    mes['speed'] = mes['speed'].replace(nad['sog'], np.nan)
    if mtype == 'ClassA':
        mes['turn'] = mes['turn'].replace(nad['rot'], np.nan)
    mes['course'] = mes['course'].replace(nad['cog'], np.nan)
    mes['heading'] = mes['heading'].replace(nad['hdg'], np.nan)

    checked = ['lat', 'lon', 'speed', 'course', 'heading']
    if mtype == 'ClassA':
        checked.insert(3, 'turn')
    mes = mes[~mes[checked].isna().all(axis=1)].reset_index(drop=True)
    summary['dynamic_after_removing_all_nan'] = len(mes)

    mes = mes.drop_duplicates(subset=['date', 'mmsi', 'lon', 'lat'])
    summary['dynamic_after_duplicates'] = len(mes)
    return mes


def build_static(stat, mtype, summary):
    """One row per MMSI and day. Dimensions (and IMO for Class A) are replaced by the most
    frequent value of that MMSI over the whole processed period."""
    summary['static_initial'] = len(stat)
    stat = stat.copy()
    stat['time_stamp'] = pd.to_datetime(stat['time_stamp'], format='%Y%m%d%H%M%S')
    stat['day'] = stat['time_stamp'].dt.date
    stat = stat.drop(columns='time_stamp')

    def mode(col):
        return stat.groupby(by='mmsi')[col].agg(lambda x: x.value_counts().index[0])

    modes = pd.DataFrame()
    for col in ('to_bow', 'to_stern', 'to_starboard', 'to_port'):
        modes[col] = mode(col)
    if mtype == 'ClassA':
        modes['imo'] = mode('imo')
    modes = modes.reset_index()

    if mtype == 'ClassA':
        subset = ['mmsi', 'imo', 'day', 'to_bow', 'to_stern', 'to_port', 'to_starboard', 'draught']
        replaced = ['imo', 'to_bow', 'to_stern', 'to_port', 'to_starboard']
    else:
        subset = ['mmsi', 'day', 'to_bow', 'to_stern', 'to_port', 'to_starboard']
        replaced = ['to_bow', 'to_stern', 'to_port', 'to_starboard']
    stat = stat.drop_duplicates(subset=subset)
    summary['static_after_first_duplicates'] = len(stat)

    stat = stat.drop(columns=replaced)
    stat = pd.merge(stat, modes, on='mmsi')
    stat = stat.drop_duplicates(subset=['mmsi', 'day'])
    summary['static_final'] = len(stat)
    return stat


def run(interim_dir, out_dir, mtype, cfg=None):
    cfg = cfg or load_config()
    spec = COLUMNS[mtype]
    interim_dir, out_dir = Path(interim_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mes = pd.read_csv(interim_dir / spec['dynamic_file'], names=spec['dynamic'])
    mes = mes.drop(columns=['type'])
    stat = pd.read_csv(interim_dir / spec['static_file'], names=spec['static'])
    stat = stat.drop(columns=['type'])

    summary = {}
    mes = filter_dynamic(mes, cfg, mtype, summary)
    stat = build_static(stat, mtype, summary)

    mes.to_csv(out_dir / ('filtered_%s.csv' % mtype), index=False)
    stat.to_csv(out_dir / ('static_%s.csv' % mtype), index=False)
    with open(out_dir / ('preprocess_summary_%s.json' % mtype), 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2)
        fh.write('\n')
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--interim-dir', required=True, help='folder with the decoded_*.txt files')
    ap.add_argument('--out-dir', required=True, help='folder for filtered_*.csv and static_*.csv')
    ap.add_argument('--class', dest='mtype', required=True, choices=sorted(COLUMNS))
    ap.add_argument('--config', help='TOML file (default: config/default.toml)')
    args = ap.parse_args(argv)
    for key, value in run(args.interim_dir, args.out_dir, args.mtype,
                          load_config(args.config)).items():
        print('%-34s %10d' % (key, value))


if __name__ == '__main__':
    main()
