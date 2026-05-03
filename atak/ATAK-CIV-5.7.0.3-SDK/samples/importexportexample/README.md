# Import/Export Example Plugin

The Import/Export Example Plugin demonstrates the key APIs involved with the import and export mechanisms provided with ATAK. For purposes of this plugin, a fictituous file format, "ExFmt" is introduced.

## ExFmt Specification

* ExFmt files will utilize an extension of ".exfmt"
* ExFmt files will be encoded using a text-based comma-separated-value (CSV) coding
* ExFmt CSV will utilize the following columns: _uid_, _callsign_, _type_, _latitude_, _longitude_, _altitude_, _remarks_
  | Column | Contents |
  |-----|-----|
  | UID | UID of marker |
  | Callsign | Callsign of marker |
  | Type | CoT type (e.g. `"a-u-G"`) |
  | Latitude | Location latitude, decimal degrees |
  | Longitude | Location longitude, decimal degrees |
  | Altitude | Location altitude, meters HAE (empty if unknown) |
  | Remarks | Remarks string |
* ExFmt CSV will not support escaped comma characters (',') 