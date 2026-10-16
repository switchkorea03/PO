from datetime import datetime
from zoneinfo import ZoneInfo
KST=ZoneInfo("Asia/Seoul")
def today_kst(now: datetime):
    return now.astimezone(KST).date()
