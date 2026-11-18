"""Step 1: decode hourly NMEA* files into 'interim' text files.

Input : hourly files named YYYYMMDDHHAIS.txt. Every line is one NMEA sentence followed by
        four digits mmss (minute and second of reception, added by the Raspberry Pi), e.g.
        !AIVDM,1,1,,B,4028jJ1vM=aTN09cHDGdgrg028B8,0*303630
Output: decoded_4.txt, decoded_123.txt, decoded_5.txt, decoded_18.txt, decoded_24A.txt, decoded_24B.txt
        and decode_summary.json (counts of every outcome) in the output directory.

Usage : python -m fnb_ais.decode --raw-dir RAW_DIR --out-dir OUT_DIR [--config FILE]
"""
import argparse
import json
import re
import sys
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

from .ais_backend import pyAISm
from .config import load_config
from .rows import (format_row_4, format_row_123, format_row_5, format_row_18,
                   format_row_24A, format_row_24B)

OUTPUT_FILES = {'4': 'decoded_4.txt', '123': 'decoded_123.txt', '5': 'decoded_5.txt', '18': 'decoded_18.txt',
                '24A': 'decoded_24A.txt', '24B': 'decoded_24B.txt'}


def split_line(line):
    """Split a logged line into (sentence, mmss).

    The usual layout after '*' is two checksum digits followed by four mmss digits. If fewer
    than six characters follow the '*' (a checksum cut to one digit), the sentence keeps one
    checksum digit only. The trailing newline is part of `mmss` and is removed by the caller.
    """
    star = line.find('*')
    if len(line[star + 1:-1]) < 6:
        return line[0:star + 2], line[star + 2:]
    return line[0:star + 3], line[star + 3:]


def has_short_tail(line):
    """True if fewer than six characters follow the '*' (see split_line)."""
    return len(line[line.find('*') + 1:-1]) < 6


def payload_bits(sentence):
    """Payload of a sentence as a string of bits (6 bits per character)."""
    return pyAISm.decod_payload(pyAISm.get_payload(sentence))


def screen_sentence(sentence):
    """Decide whether a sentence is passed to the decoder.

    Returns (ok, reason). Reasons: 'not_aivdm_or_aivdo', 'malformed_sentence',
    'empty_payload', 'type5_single_sentence_168_bits'. A message of type 5 needs 424 bits
    (two sentences); a single-sentence type 5 with 168 bits is truncated and is dropped.
    """
    if pyAISm.get_msg_type(sentence) not in ('!AIVDM', '!AIVDO'):
        return False, 'not_aivdm_or_aivdo'
    try:
        bits = payload_bits(sentence)
    except IndexError:
        return False, 'malformed_sentence'
    if bits == '':
        return False, 'empty_payload'
    if int(bits[0:6], 2) == 5 and len(bits) == 168:
        return False, 'type5_single_sentence_168_bits'
    return True, None


def part_of_message_24(sentence):
    """'A' or 'B' for a type 24 message, from the part-number bits."""
    return 'B' if payload_bits(sentence)[38:40] == '01' else 'A'


def decode_file(path, outputs, analysed_types, counts):
    """Decode one hourly file; write rows to `outputs`; update the Counter `counts`."""
    hour_prefix = path.name[0:10]
    with open(path, 'r', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            counts['lines_read'] += 1
            sentence, mmss = split_line(line)
            if has_short_tail(line):
                counts['lines_with_fewer_than_6_chars_after_star'] += 1
            reception_time = (hour_prefix + mmss).rstrip('\n')

            ok, reason = screen_sentence(sentence)
            if not ok:
                counts['skipped_' + reason] += 1
                continue
            try:
                data = pyAISm.decod_ais(sentence.strip())
            except Exception as exc:
                counts['decoder_exception_' + type(exc).__name__] += 1
                continue
            if len(data) == 1:
                if 'none' in data:
                    counts['multipart_fragment_waiting_for_next_sentence'] += 1
                else:
                    counts['type_not_supported_by_decoder_%d' % data['type']] += 1
                continue

            kind = data['type']
            if kind not in analysed_types:
                counts['decoded_but_not_written_type_%d' % kind] += 1
                continue
            if kind == 4:
                outputs['4'].write(reception_time + format_row_4(data))
                counts['written_4'] += 1
            elif kind in (1, 2, 3):
                outputs['123'].write(reception_time + format_row_123(data))
                counts['written_123'] += 1
            elif kind == 5:
                outputs['5'].write(reception_time + ',' + format_row_5(data))
                counts['written_5'] += 1
            elif kind == 18:
                outputs['18'].write(reception_time + format_row_18(data))
                counts['written_18'] += 1
            elif kind == 24:
                if part_of_message_24(sentence) == 'A':
                    # Part A rows carry no reception time (as in the original scripts).
                    outputs['24A'].write(format_row_24A(data))
                    counts['written_24A'] += 1
                else:
                    outputs['24B'].write(reception_time + ',' + format_row_24B(data))
                    counts['written_24B'] += 1


def run(raw_dir, out_dir, cfg=None, pattern='*.txt', quiet=False):
    """Decode every hourly file in `raw_dir`; return the counts as a dict."""
    cfg = cfg or load_config()
    analysed = set(cfg['analysed_message_types'])
    raw_dir, out_dir = Path(raw_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = Counter()
    files = sorted(p for p in raw_dir.glob(pattern) if p.is_file())
    with ExitStack() as stack:
        outputs = {k: stack.enter_context(open(out_dir / v, 'w', encoding='utf-8'))
                   for k, v in OUTPUT_FILES.items()}
        for path in files:
            if not re.match(r'\d{10}', path.name):
                print('skipping %s: the name must start with YYYYMMDDHH' % path.name,
                      file=sys.stderr)
                continue
            if not quiet:
                print('decoding', path.name)
            counts['files_read'] += 1
            decode_file(path, outputs, analysed, counts)

    summary = dict(sorted(counts.items()))
    with open(out_dir / 'decode_summary.json', 'w', encoding='utf-8') as fh:
        json.dump(summary, fh, indent=2)
        fh.write('\n')
    return summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--raw-dir', required=True, help='folder with the hourly NMEA* .txt files')
    ap.add_argument('--out-dir', required=True, help='folder for the decoded files')
    ap.add_argument('--pattern', default='*.txt', help='file pattern (default: *.txt)')
    ap.add_argument('--config', help='TOML file (default: config/default.toml)')
    ap.add_argument('--quiet', action='store_true')
    args = ap.parse_args(argv)
    summary = run(args.raw_dir, args.out_dir, load_config(args.config), args.pattern, args.quiet)
    width = max(len(k) for k in summary) if summary else 0
    for key, value in summary.items():
        print('%-*s %8d' % (width, key, value))


if __name__ == '__main__':
    main()
