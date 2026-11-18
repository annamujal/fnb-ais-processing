"""Format decoded AIS messages as comma-separated rows (the 'interim' text files).

Each function returns one line of text ending in a newline. The field order and the number
formatting are those of the original scripts and must not be changed without changing the
column names used in preprocess.py.
"""
from .ais_backend import pyAISm


def _second_as_text(data):
    """The second field of the vessel's time stamp as a 2-character string ('05', '59')."""
    text = '{}'.format(data['second'])
    if len(text) == 1:
        text = '0' + text
    return text


def format_row_123(data):
    """Messages 1, 2, 3 (Class A dynamic).

    Columns after the 14-digit reception time: second_sent, type, mmsi, status, turn, speed,
    lon, lat, course, heading.
    """
    fields = ['type', 'mmsi', 'status', 'turn', 'speed', 'lon', 'lat', 'course', 'heading']
    values = [_second_as_text(data)] + [data[f] for f in fields]
    return ',{:2s},{},{},{:2d},{:6.1f},{:6.1f},{:.5f},{:.5f},{:5.1f},{:3d}\n'.format(*values)


def format_row_5(data):
    """Message 5 (Class A static and voyage data).

    Columns after the reception time: type, mmsi, imo, shipname, shiptype, to_bow, to_stern,
    to_port, to_starboard, draught, destination. Commas are removed from the destination.
    """
    fields = ['type', 'mmsi', 'imo', 'shipname', 'shiptype', 'to_bow', 'to_stern',
              'to_port', 'to_starboard', 'draught', 'destination']
    values = [data[f] for f in fields]
    if "," in values[10]:
        values[10] = values[10].replace(",", "")
    return '{},{},{},{:20s},{:3d},{:5.1f},{:5.1f},{:5.1f},{:5.1f},{:5.1f},{}\n'.format(*values)


def format_row_18(data):
    """Message 18 (Class B dynamic).

    Columns after the reception time: second_sent, type, mmsi, speed, lon, lat, course, heading.
    """
    fields = ['type', 'mmsi', 'speed', 'lon', 'lat', 'course', 'heading']
    values = [_second_as_text(data)] + [data[f] for f in fields]
    return ',{:2s},{},{},{:6.1f},{:9.5f},{:9.5f},{:5.1f},{:3d}\n'.format(*values)


def format_row_24A(data):
    """Message 24 part A (Class B name). Columns: type, mmsi, shipname ('NoName' if absent)."""
    values = [data[f] if f in data else 'NoName' for f in ('type', 'mmsi', 'shipname')]
    return '{},{},{:20s}\n'.format(*values)


def format_row_24B(data):
    """Message 24 part B (Class B static data).

    Craft that are auxiliary to a mother ship have no dimensions: their four dimension
    columns are written as '*'.
    """
    if not pyAISm.is_auxiliary_craft(data['mmsi']):
        fields = ['type', 'mmsi', 'shiptype', 'to_bow', 'to_stern', 'to_port', 'to_starboard']
        values = [data[f] if f in data else 0 for f in fields]
        return '{},{},{:3d},{:5.1f},{:5.1f},{:5.1f},{:5.1f}\n'.format(*values)
    fields = ['type', 'mmsi', 'shiptype', 'mothership_mmsi']
    values = [data[f] if f in data else 0 for f in fields]
    return '{},{},{:3d},{:6s},{:6s},{:6s},{:6s}\n'.format(values[0], values[1], values[2],
                                                          '*', '*', '*', '*')


def format_row_4(data):
    """Message 4 (base station report: UTC date and time and position of the base station).

    Columns after the reception time: type, mmsi, base_utc (YYYYMMDDHHMMSS), lon, lat, epfd.
    base_utc is written from the raw fields, so 'not available' values stay visible
    (year 0000, hour 24, minute 60, second 60); lon 181 and lat 91 are not available either.
    The reception time is compared with base_utc to check the receiver clock.
    """
    utc = '{:04d}{:02d}{:02d}{:02d}{:02d}{:02d}'.format(
        data['year'], data['month'], data['day'], data['hour'], data['minute'], data['second'])
    return ',{},{},{},{:.5f},{:.5f},{}\n'.format(data['type'], data['mmsi'], utc,
                                                data['lon'], data['lat'], data['epfd'])
