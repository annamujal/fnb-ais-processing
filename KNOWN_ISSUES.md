# Known issues (kept on purpose: fixing them would change released data)

1. **Destination is cut at 19 characters** and read from payload bits 302-420 (`ais_backend.py`);
   the AIS field is 20 characters at bits 302-422.
2. **Empty-payload sentences** (about a quarter of the lines in a sample hour) are skipped
   without being decoded. They are counted as `skipped_empty_payload` in `decode_summary.json`.
3. **Latitude/longitude "not available" (91/181) rows are removed by the geographic box**,
   before the NaN conversion, so that conversion never applies to them.
4. **Static data are replaced by the per-MMSI mode** over the whole processed period
   (dimensions, and IMO for Class A), not only outliers.
5. **Speed is written in 1/10 knot and ROT as the raw AIS code** by both scripts; no unit conversion is applied here.
6. **Message 24 part A rows carry no reception time.**
7. **Ship names** can contain trailing padding; destination commas are removed;
   auxiliary craft (MMSI 98xxxxxxx) get `*` as dimensions.
8. **Hour convention of the file name** (UTC or local) is not verified by this code.
