from datetime import timedelta
def next_weekday(value):
    while value.weekday()>=5:value+=timedelta(days=1)
    return value
