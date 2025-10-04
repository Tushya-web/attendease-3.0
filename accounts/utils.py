import os
from datetime import datetime
from django.conf import settings
from .models import Attendance

def mark_user_attendance(user):
    today = datetime.today().date()
    now_time = datetime.now()

    # Get or create attendance record for today
    attendance, created = Attendance.objects.get_or_create(user=user, date=today)

    if not attendance.check_in:
        attendance.check_in = now_time
        attendance.save()
        return "check_in", now_time.strftime("%H:%M:%S"), attendance.check_in
    elif not attendance.check_out:
        attendance.check_out = now_time
        attendance.save()
        return "check_out", now_time.strftime("%H:%M:%S"), attendance.check_in
    else:
        # Already checked in and out
        return "completed", None, attendance.check_in