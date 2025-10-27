from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.contrib.auth.views import LoginView
from django.template import loader

from .models import Attendance, FaceChangeRequest, LeaveRequest, PendingFaceUpdate , UserFace
from .forms import RegistrationForm

from django.contrib.auth import authenticate, login
from .forms import CustomLoginForm

from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.contrib import messages

from django.views.decorators.csrf import csrf_exempt
import requests
import json
import traceback
from django.http import JsonResponse

import csv

import calendar
from datetime import datetime, timedelta, date

import base64, os, cv2, numpy as np
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.timezone import now

from .utils import mark_user_attendance

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .face_system import add_face_image, decode_base64_image, recognize_logged_in_user

@login_required
@csrf_exempt
def face_view(request):
    user = request.user

    # 1️⃣ Registered / Approved face (from UserFace)
    user_face = UserFace.objects.filter(user=user).first()
    old_face_url = user_face.face_image.url if user_face and user_face.face_image else None

    # 2️⃣ Pending face (from FaceChangeRequest)
    pending_obj = FaceChangeRequest.objects.filter(user=user, status="Pending").order_by("-created_at").first()
    pending_face_url = None
    if pending_obj and pending_obj.new_face_path:
        path = pending_obj.new_face_path
        if os.path.isabs(path):
            relative = os.path.relpath(path, settings.MEDIA_ROOT)
            pending_face_url = settings.MEDIA_URL + relative.replace("\\", "/")
        else:
            pending_face_url = settings.MEDIA_URL + path.replace("\\", "/")

    # 3️⃣ Rejected face (from FaceChangeRequest)
    rejected_obj = FaceChangeRequest.objects.filter(user=user, status="Rejected").order_by("-created_at").first()
    rejected_face_url = None
    if rejected_obj and rejected_obj.new_face_path:
        path = rejected_obj.new_face_path
        if os.path.isabs(path):
            relative = os.path.relpath(path, settings.MEDIA_ROOT)
            rejected_face_url = settings.MEDIA_URL + relative.replace("\\", "/")
        else:
            rejected_face_url = settings.MEDIA_URL + path.replace("\\", "/")

    context = {
        "user": user,
        "old_face": old_face_url,
        "pending_face": pending_face_url,
        "rejected_face": rejected_face_url,
        "has_face": bool(user_face and user_face.face_image),
    }

    return render(request, "face_view.html", context)

    
@login_required
def face_scan(request):
    user = request.user
    today = datetime.today().date()

    try:
        attendance = Attendance.objects.get(user=user, date=today)
    except Attendance.DoesNotExist:
        attendance = None

    # Determine today's status safely
    if not attendance:
        today_status = "Welcome! Please check in."
        disable_verify = False
    else:
        if attendance.check_in and not attendance.check_out:
            today_status = f"Checked in at {attendance.check_in.strftime('%H:%M:%S')}. You can check out now."
            disable_verify = False
        elif attendance.check_in and attendance.check_out:
            today_status = f"Already checked in at {attendance.check_in.strftime('%H:%M:%S')} and checked out at {attendance.check_out.strftime('%H:%M:%S')}."
            disable_verify = True
        else:  # attendance exists but check_in is None
            today_status = "Welcome! Please check in."
            disable_verify = False

    return render(request, "face_scan.html", {
        "today_status": today_status,
        "disable_verify": disable_verify
    })
    
@csrf_exempt
@login_required
def mark_attendance_ajax(request):
    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request"})

    data = json.loads(request.body)
    image_data = data.get("image_data")
    if not image_data:
        return JsonResponse({"status": "error", "message": "No image received"})

    frame = decode_base64_image(image_data)

    # Recognize face → returns username string
    username = recognize_logged_in_user(frame, request.user.username)
    if not username:
        return JsonResponse({"status": "error", "message": "No face detected or unclear."})

    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        user_obj = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({"status": "error", "message": "User not found"})

    from .utils import mark_user_attendance
    status, time, check_in_time = mark_user_attendance(user_obj)

    # Safely create/update today's attendance
    attendance, created = Attendance.objects.get_or_create(
        user=user_obj,
        date=date.today(),
        defaults={
            "status": status,
            "check_in": check_in_time,
        }
    )

    # If record exists but only check_in is missing (user already has Absent)
    if not created and not attendance.check_in:
        attendance.check_in = check_in_time
        attendance.status = status
        attendance.save()

    return JsonResponse({
        "status": "success",
        "username": username,
        "type": status,
        "time": time,
        "check_in": check_in_time.strftime("%H:%M:%S") if check_in_time else None
    })

def auto_mark_absent(user):
    """Automatically create missing 'Absent' records safely."""
    today = date.today()
    first_date = user.date_joined.date()

    # Fetch existing dates once
    existing_dates = set(
        Attendance.objects.filter(user=user).values_list('date', flat=True)
    )

    current = first_date
    while current <= today:
        if current not in existing_dates:
            Attendance.objects.get_or_create(
                user=user,
                date=current,
                defaults={"status": "Absent"}
            )
        current += timedelta(days=1)
        
@login_required
def attendance_report(request):
    # Auto-mark absent safely
    auto_mark_absent(request.user)

    # Fetch attendance
    records = Attendance.objects.filter(user=request.user).order_by('-date')
    return render(request, "attendance_report.html", {"records": records})


@login_required
def download_attendance_csv(request):
    # Step 1: Auto-create missing "Absent" records first
    auto_mark_absent(request.user)

    # Step 2: Fetch all attendance for the logged-in user
    records = Attendance.objects.filter(user=request.user).order_by("-date")

    # Step 3: Prepare CSV response
    response = HttpResponse(
        content_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{request.user.username}_attendance.csv"'
        },
    )

    # Step 4: Write CSV header
    writer = csv.writer(response)
    writer.writerow(["Date", "Check In", "Check Out", "Status"])

    # Step 5: Write attendance rows
    for record in records:
        date_str = record.date.strftime("%Y-%m-%d")

        check_in_str = record.check_in.strftime("%H:%M:%S") if record.check_in else "--"
        check_out_str = record.check_out.strftime("%H:%M:%S") if record.check_out else "--"

        # Ensure consistency with database status field
        if hasattr(record, "status") and record.status:
            status = record.status
        else:
            if record.check_in and record.check_out:
                status = "Present"
            elif record.check_in and not record.check_out:
                status = "Absent (No Check-Out)"
            else:
                status = "Absent"

        writer.writerow([date_str, check_in_str, check_out_str, status])

    return response


# @login_required
# def save_face(request):
#     if request.method == "POST":
#         img_data = request.POST.get("image_data")
#         if img_data:
#             header, encoded = img_data.split(",", 1)
#             img_bytes = base64.b64decode(encoded)
#             nparr = np.frombuffer(img_bytes, np.uint8)
#             img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

#             # Save to pending folder
#             pending_dir = os.path.join(settings.MEDIA_ROOT, "pending_faces")
#             os.makedirs(pending_dir, exist_ok=True)
#             pending_path = os.path.join(pending_dir, f"{request.user.username}_pending.jpg")
#             cv2.imwrite(pending_path, img)

#             # Create or update pending request
#             from .models import FaceChangeRequest
#             FaceChangeRequest.objects.update_or_create(
#                 user=request.user,
#                 defaults={"status": "Pending", "new_face_path": pending_path}
#             )

#             return JsonResponse({"status": "success", "message": "Face submitted for admin approval"})


def help_support(request):
    return render(request, "help_support.html")

@login_required
@csrf_exempt
def face_add(request):
    user = request.user

    # Check if user already has a face
    user_face = UserFace.objects.filter(user=user).first()
    has_face = True if user_face and user_face.face_image else False

    if request.method == "POST":
        import json
        data = json.loads(request.body)
        img_data = data.get("image_data")
        if img_data:
            # Prepare image path
            faces_dir = os.path.join(settings.MEDIA_ROOT, "faces", user.username)
            os.makedirs(faces_dir, exist_ok=True)
            img_path = os.path.join(faces_dir, f"{user.username}_1.jpg")

            # Decode base64 image
            header, encoded = img_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            cv2.imwrite(img_path, img)

            if not has_face:
                # First-time face → save directly to UserFace
                UserFace.objects.update_or_create(
                    user=user,
                    defaults={"face_image": f"faces/{user.username}/{user.username}_1.jpg"}
                )
                return JsonResponse({"status": "success", "message": "Face captured successfully!"})
            else:
                # Existing user → create/update pending FaceChangeRequest
                FaceChangeRequest.objects.update_or_create(
                    user=user,
                    defaults={"status": "Pending", "new_face_path": img_path}
                )
                return JsonResponse({"status": "success", "message": "Face submitted for admin approval."})

        return JsonResponse({"status": "error", "message": "No image data received."})

    # GET request → render template
    old_face_url = user_face.face_image.url if has_face else None

    # Check if there’s a pending change request
    pending_obj = FaceChangeRequest.objects.filter(user=user, status="Pending").first()
    pending_face_url = pending_obj.new_face_path.replace(settings.MEDIA_ROOT, settings.MEDIA_URL) if pending_obj else None

    return render(request, "face_add.html", {
        "user": user,
        "old_face": old_face_url,
        "pending_face": pending_face_url,
        "has_face": has_face,
    })

OPENROUTER_API_KEY = "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"  # Store in settings.py for safety

# GEMINI_API_KEY = "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"

# Render the chat page
def chatbot_view(request):
    return render(request, "chatbot.html")


@csrf_exempt
def chatbot_api(request):
    if request.method == "POST":
        data = json.loads(request.body)
        question = data.get("question")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }

        # Strict System Prompt + Few-shot examples  
        messages = [
            {
                "role": "system",
                "content": (
                    "You are AttendEase Assistant.\n"
                    "Rules:\n"
                    "- Only answer questions related to AttendEase project or its creator.\n"
                    "- Keep answers short, clear, and formal.\n"
                    "- Use bullet points where possible.\n"
                    "- If unrelated, respond: 'I can only help with AttendEase-related questions.'"
                )
            },

            # Few-shot examples: Project
            {"role": "user", "content": "What technologies does project use?"},
            {"role": "assistant", "content": (
                "Technologies Used\n"
                "- Backend: Django (Python)"
                "- Frontend: HTML, CSS, JS"
                "- Database: SQLite"
                "- AI: OpenCV + face_recognition"
            )},
            {"role": "user", "content": "How does AttendEase mark attendance?"},
            {"role": "assistant", "content": (
                "Attendance Process:\n"
                "- Detects face using OpenCV\n"
                "- Matches encoding with stored profiles\n"
                "- Marks entry/exit time in SQLite"
            )},
            {"role": "user", "content": "How is attendance report generated?"},
            {"role": "assistant", "content": (
                "Attendance Report:\n"
                "- Data stored in SQLite\n"
                "- Summarized by date and user\n"
                "- Exportable in CSV or PDF or sheet"
            )},

            # Few-shot examples: About Creator
            {"role": "user", "content": "Who created AttendEase?"},
            {"role": "assistant", "content": (
                "AttendEase was created by Yash & Tushy, "
                "a BCA Semester 6 student at Ganpat University."
            )},
            {"role": "user", "content": "Tell me about the creator."},
            {"role": "assistant", "content": (
                "Creator Information:\n"
                "- Name: Yash and Tushya\n"
                "- Education: BCA Semester 6\n"
                "- University: Ganpat University\n"
                "- Role: Developer of AttendEase"
            )},
            
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": (
                "Hello I am ChatBot Assistent of AttendEase? How Can i help you.."
            )},


            # Non-relevant example
            {"role": "user", "content": "Tell me about cricket."},
            {"role": "assistant", "content": "I can only help with AttendEase-related questions."},

            # Actual user question
            {"role": "user", "content": question}
        ]


        payload = {"model": "nvidia/nemotron-nano-9b-v2:free", "messages": messages}

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        answer = data["choices"][0]["message"]["content"]

        return JsonResponse({"answer": answer})

    return JsonResponse({"error": "Invalid request"}, status=400)

def admin_view(request):
    return render(request, "admin.html")

def index(request):
    template = loader.get_template("index.html")
    return HttpResponse(template.render({}, request))

User = get_user_model()

def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data["password"])
            user.is_active = True
            user.is_approved = False
            user.save()
            messages.success(request, "Registration request sent. Wait for admin approval.")
            return redirect('userlogin')
    else:
        form = RegistrationForm()

    return render(request, "register.html", {"form": form}) 

def login_view(request):
    if request.method == "POST":
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)

            if user is not None:
                if user.is_approved: 
                    login(request, user)
                    messages.success(request, f"Welcome, {user.username}!")
                    return redirect('userdash')
                else:
                    messages.error(request, "Your account is pending admin approval.")
            else:
                messages.error(request, "Invalid username or password.")
    else:
        form = CustomLoginForm()

    return render(request, "userlogin.html", {"form": form})

@login_required
def userdash_view(request):
    month = int(request.GET.get('month', datetime.today().month))
    year = int(request.GET.get('year', datetime.today().year))

    cal = calendar.Calendar(firstweekday=0)
    month_days = list(cal.itermonthdays(year, month))
    weeks = [month_days[i:i+7] for i in range(0, len(month_days), 7)]
    day_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    # --- Fetch approved leaves ---
    approved_leaves = LeaveRequest.objects.filter(
        user=request.user,
        status="Approved",
        start_date__year__lte=year,
        end_date__year__gte=year
    )

    # Collect leave days in this month
    leave_days = set()
    for leave in approved_leaves:
        current_day = leave.start_date
        while current_day <= leave.end_date:
            if current_day.month == month:
                leave_days.add(current_day.day)
            current_day += timedelta(days=1)

    # --- Fetch attendance for this month ---
    month_start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    month_end = date(year, month, last_day)

    attendance_qs = Attendance.objects.filter(
        user=request.user,
        date__range=(month_start, month_end)
    )

    day_status_list = []
    
    # Total days in month
    last_day = calendar.monthrange(year, month)[1]
    
    for day in range(1, last_day + 1):
        if day in leave_days:
            status = "Leave"
        elif any(att.date.day == day for att in attendance_qs):
            att_day = next(att for att in attendance_qs if att.date.day == day)
            if att_day.status == "Present":
                status = "Present"
            elif att_day.status == "Checked In":
                status = "Half-Day"
            elif att_day.status == "Absent":
                status = "Absent"
            elif att_day.status == "Holiday":
                status = "Holiday"
            elif att_day.status == "Leave":
                status = "Leave"
            else:
                status = ""
        else:
            status = ""  # No attendance recorded
        day_status_list.append((day, status))
    

    context = {
        "cal_year": year,
        "cal_month": month,
        "cal_month_name": calendar.month_name[month],
        "cal_weeks": weeks,
        "today_day": datetime.today().day,
        "today_month": datetime.today().month,
        "today_year": datetime.today().year,
        "day_names": day_names,
        "day_status_list": day_status_list,
    }

    # If AJAX request, return only the calendar cells
    if request.GET.get('ajax') == '1':
        from django.template.loader import render_to_string
        html = render_to_string('calendar_cells.html', context)
        return HttpResponse(html)

    return render(request, "userdash.html", {"user": request.user, **context})


def logout(request):
    return render(request, "userlogin.html")

def userprofile_view(request):
    return render(request, "user_profile.html" , {"user": request.user})

@login_required
def change_password(request):
    if request.method == "POST":
        new_password = request.POST.get("newPassword")
        confirm_password = request.POST.get("confirmNewPassword")

        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("change_password")

        try:
            password_validation.validate_password(new_password, request.user)
        except ValidationError as e:
            for err in e.messages:
                messages.error(request, err)
            return redirect("change_password")

        # Update password
        request.user.set_password(new_password)
        request.user.save()
        update_session_auth_hash(request, request.user)

        messages.success(request, "Password updated successfully.")
        return redirect("change_password")  # or wherever you want

    return render(request, 'user_profile.html')


@login_required
def leave_request_view(request):
    if request.method == "POST":
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        leave_type = request.POST.get("leave_type")
        reason = request.POST.get("reason")

        LeaveRequest.objects.create(
            user=request.user,
            start_date=start_date,
            end_date=end_date,
            leave_type=leave_type,
            reason=reason,
            status="Pending"
        )

        messages.success(request, "Leave request submitted successfully ✅")
        return redirect("leave_request")  

    leave_requests = LeaveRequest.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "leave_request.html", {"leave_requests": leave_requests})
