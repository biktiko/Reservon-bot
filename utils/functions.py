# C:\Reservon Bot\utils\functions.py
def parse_duration_to_minutes(dur_str):
    """
    Convert "00:30:00" or "0:20:00" to integer minutes.
    """
    if not dur_str:
        return 0
    parts = dur_str.split(":")
    if len(parts) < 2:
        return 0
    try:
        hh = int(parts[0])
        mm = int(parts[1])
        return hh*60 + mm
    except:
        return 0
