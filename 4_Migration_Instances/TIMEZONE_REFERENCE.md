# Timezone Reference for extract_instances.py

## Overview

The `--timezone` parameter accepts IANA timezone names for converting AS_OF_TIMESTAMP values to UTC.

## Common Timezones

### Asia-Pacific
- `Asia/Singapore` (UTC+8, default)
- `Asia/Hong_Kong` (UTC+8)
- `Asia/Tokyo` (UTC+9)
- `Asia/Seoul` (UTC+9)
- `Asia/Shanghai` (UTC+8)
- `Asia/Kuala_Lumpur` (UTC+8)
- `Asia/Bangkok` (UTC+7)
- `Asia/Jakarta` (UTC+7)
- `Asia/Manila` (UTC+8)
- `Australia/Sydney` (UTC+10/+11 with DST)
- `Pacific/Auckland` (UTC+12/+13 with DST)

### Americas
- `America/New_York` (UTC-5/-4 with DST)
- `America/Chicago` (UTC-6/-5 with DST)
- `America/Denver` (UTC-7/-6 with DST)
- `America/Los_Angeles` (UTC-8/-7 with DST)
- `America/Toronto` (UTC-5/-4 with DST)
- `America/Sao_Paulo` (UTC-3/-2 with DST)
- `America/Mexico_City` (UTC-6/-5 with DST)

### Europe
- `Europe/London` (UTC+0/+1 with DST)
- `Europe/Paris` (UTC+1/+2 with DST)
- `Europe/Berlin` (UTC+1/+2 with DST)
- `Europe/Madrid` (UTC+1/+2 with DST)
- `Europe/Rome` (UTC+1/+2 with DST)
- `Europe/Amsterdam` (UTC+1/+2 with DST)
- `Europe/Zurich` (UTC+1/+2 with DST)

### Middle East & Africa
- `Asia/Dubai` (UTC+4)
- `Asia/Riyadh` (UTC+3)
- `Africa/Johannesburg` (UTC+2)
- `Africa/Cairo` (UTC+2)

### Other
- `UTC` (UTC+0, no DST)

## Usage Examples

```bash
# Default (Singapore time)
python extract_instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023

# New York time
python extract_instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --timezone "America/New_York"

# Tokyo time
python extract_instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --timezone "Asia/Tokyo"

# Already in UTC
python extract_instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --timezone "UTC"
```

## Full Timezone List

For a complete list of supported timezones, see:
- **Online:** https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
- **Python command:** `python -c "import pytz; print('\n'.join(pytz.all_timezones))"`

## Notes

- DST = Daylight Saving Time (some timezones shift UTC offset during summer months)
- The script automatically handles DST transitions
- Use the exact timezone name (case-sensitive)
- Quotes are required around timezone names in command line (especially on Windows)
