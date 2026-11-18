"""Regression tests. The expected files were produced by the original scripts' logic
(verified byte-identical on a full hour of data) from the excerpt in tests/data/raw."""
import filecmp
from pathlib import Path

import pytest

from fnb_ais import decode, preprocess

HERE = Path(__file__).parent / "data"
DECODED = ["decoded_4.txt", "decoded_123.txt", "decoded_5.txt", "decoded_18.txt", "decoded_24A.txt", "decoded_24B.txt"]


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    d = tmp_path_factory.mktemp("out")
    decode.run(HERE / "raw", d, quiet=True)
    for c in ("ClassA", "ClassB"):
        preprocess.run(d, d, c)
    return d


@pytest.mark.parametrize("name", DECODED + ["filtered_ClassA.csv", "filtered_ClassB.csv",
                                            "static_ClassA.csv", "static_ClassB.csv"])
def test_identical_to_expected(out, name):
    assert filecmp.cmp(out / name, HERE / "expected" / name, shallow=False)


def test_split_line_two_and_one_digit_checksum():
    assert decode.split_line("!AIVDM,1,1,,A,xx,0*26" "3630\n") == ("!AIVDM,1,1,,A,xx,0*26", "3630\n")
    assert decode.split_line("!AIVDM,1,1,,A,xx,0*2" "3630\n")[0].endswith("*2")


def test_edge_lines_are_counted_not_fatal(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "2023042709AIS.txt").write_text(
        "!AIVDM,1,1,,A,,0*263630\n$GPGGA,foo*003630\n!AIVDM,1,1,,B,1,0*03630\n")
    s = decode.run(raw, tmp_path / "o", quiet=True)
    assert s["skipped_empty_payload"] == 1
    assert s["skipped_not_aivdm_or_aivdo"] == 1


def test_upstream_pyaism_with_patches():
    from fnb_ais.ais_backend import pyAISm
    good = "!AIVDM,1,1,,B,4028jJ1vM=aTN09cHDGdgrg028B8,0*30"
    assert pyAISm.decod_ais(good)["type"] == 4
    # checksum cut to one digit: compared on its first digit only
    assert pyAISm.decod_ais(good[:-1])["type"] == 4
    # four extra digits after the checksum are not compared
    assert pyAISm.decod_ais(good + "3630")["type"] == 4
    with pytest.raises(pyAISm.BadChecksumError):
        pyAISm.decod_ais(good[:-2] + "FF")


def test_truncated_24_part_b_is_rejected():
    from fnb_ais.ais_backend import pyAISm
    sentence = "!AIVDM,1,1,,B,H7GP6oHJvV63d2BbRL0W400<0:P,4*6A"   # part number 2, truncated
    with pytest.raises(ValueError):
        pyAISm.decod_ais(sentence)
