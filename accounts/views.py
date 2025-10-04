from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.contrib.auth.views import LoginView
from django.template import loader

from .models import Attendance, FaceChangeRequest, LeaveRequest, PendingFaceUpdate 
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
from datetime import datetime, timedelta

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
def face_view(request):
    user = request.user
    old_face_url = None
    new_face_url = None
    face_status = None
    pending_face = False

    # Step 1: Determine the last approved face
    # First, check if there is any Approved PendingFaceUpdate
    latest_approved = PendingFaceUpdate.objects.filter(user=user, status="Approved").order_by('-created_at').first()
    if latest_approved:
        # Use the approved new_image or new_face_path
        if latest_approved.new_image:
            old_face_url = latest_approved.new_image.url
        elif latest_approved.new_face_path:
            relative_path = latest_approved.new_face_path.replace(str(settings.MEDIA_ROOT), "").lstrip("/")
            old_face_url = f"{settings.MEDIA_URL}{relative_path}"
    else:
        # If no approved updates, fallback to the first image in user folder
        user_folder = os.path.join(settings.MEDIA_ROOT, "faces", user.username)
        if os.path.exists(user_folder) and len(os.listdir(user_folder)) > 0:
            old_face_file = os.listdir(user_folder)[0]
            old_face_url = os.path.join(settings.MEDIA_URL, "faces", user.username, old_face_file)

    # Step 2: Determine the latest pending or rejected request
    latest_request = PendingFaceUpdate.objects.filter(user=user).exclude(status="Approved").order_by('-created_at').first()
    if latest_request:
        pending_face = True
        face_status = latest_request.status

        if latest_request.new_image:
            new_face_url = latest_request.new_image.url
        elif latest_request.new_face_path:
            relative_path = latest_request.new_face_path.replace(str(settings.MEDIA_ROOT), "").lstrip("/")
            new_face_url = f"{settings.MEDIA_URL}{relative_path}"

    context = {
        "user": user,
        "old_face_url": old_face_url,       # Always last approved image
        "pending_face": pending_face,       # True if any pending/rejected exists
        "new_face_url": new_face_url,       # Pending or rejected image
        "face_status": face_status,         # Pending or Rejected
    }

    return render(request, "face_view.html", context)


def face_scan(request):
    user = request.user
    today = datetime.today().date()

    try:
        attendance = Attendance.objects.get(user=user, date=today)
    except Attendance.DoesNotExist:
        attendance = None

    # Determine today status
    if not attendance:
        today_status = "Welcome! Please check in."
        disable_verify = False    
    # elif attendance.check_in and not attendance.check_out:
    else:
        today_status = f"Checked in at {attendance.check_in.strftime('%H:%M:%S')}. You can check out now."
        disable_verify = False
    # else:
    #     today_status = "Today’s attendance already marked."
    #     disable_verify = True

    return render(request, "face_scan.html", {
        "today_status": today_status,
        "disable_verify": disable_verify
    })
 
@csrf_exempt
@login_required
def mark_attendance_ajax(request):
    if request.method == "POST":
        data = json.loads(request.body)
        image_data = data.get("image_data")
        if not image_data:
            return JsonResponse({"status": "error", "message": "No image received"})

        frame = decode_base64_image(image_data)

        # Recognize face → returns username string
        username = recognize_logged_in_user(frame, request.user.username)

        if not username:
            return JsonResponse({"status": "error", "message": "No face detected or unclear. Please try again."})

        # ✅ Get User object first
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse({"status": "error", "message": "User not found"})

        # Mark attendance
        from .utils import mark_user_attendance
        status, time, check_in_time = mark_user_attendance(user_obj)

        return JsonResponse({
            "status": "success",
            "username": username,
            "type": status,
            "time": time,
            "check_in": check_in_time.strftime("%H:%M:%S") if check_in_time else None
        })

    return JsonResponse({"status": "error", "message": "Invalid request"})


@login_required
def attendance_report(request):
    from .models import Attendance
    records = Attendance.objects.filter(user=request.user).order_by("-date")
    return render(request, "attendance_report.html", {"records": records})

  
@login_required
def download_attendance_csv(request):
    # Filter attendance records for the logged-in user
    records = Attendance.objects.filter(user=request.user).order_by("-date")

    # Create the HTTP response with CSV content type
    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{request.user.username}_attendance.csv"'},
    )

    # Create a CSV writer
    writer = csv.writer(response)
    writer.writerow(["Date", "Check In", "Check Out"])

    # Write user attendance rows
    for record in records:
        writer.writerow([
            record.date.strftime("%Y-%m-%d"),
            record.check_in.strftime("%H:%M:%S") if record.check_in else "",
            record.check_out.strftime("%H:%M:%S") if record.check_out else "",
        ])

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
    from .models import FaceChangeRequest
    import os, base64, cv2
    from django.conf import settings
    import json

    user = request.user

    # Check if there’s a pending request
    pending_obj = FaceChangeRequest.objects.filter(user=user, status="Pending").first()
    pending_face = True if pending_obj else False
    pending_face_url = pending_obj.new_face_path.replace(settings.MEDIA_ROOT, settings.MEDIA_URL) if pending_face else None

    if request.method == "POST":
        data = json.loads(request.body)
        img_data = data.get("image_data")
        if img_data and not pending_face:  # Only allow if no pending
            pending_dir = os.path.join(settings.MEDIA_ROOT, "pending_faces")
            os.makedirs(pending_dir, exist_ok=True)
            pending_path = os.path.join(pending_dir, f"{user.username}_pending.jpg")

            # Decode base64 image
            header, encoded = img_data.split(",", 1)
            img_bytes = base64.b64decode(encoded)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            cv2.imwrite(pending_path, img)

            # Create or update pending request
            FaceChangeRequest.objects.update_or_create(
                user=user,
                defaults={"status": "Pending", "new_face_path": pending_path}
            )

            return JsonResponse({"status": "success", "message": "Face submitted for admin approval"})

        return JsonResponse({"status": "error", "message": "Face capture disabled. Pending approval exists."})

    # GET request → render template
    old_face_path = os.path.join(settings.MEDIA_ROOT, "faces", user.username, "1.jpg")
    old_face_url = old_face_path.replace(settings.MEDIA_ROOT, settings.MEDIA_URL) if os.path.exists(old_face_path) else None

    return render(request, "face_add.html", {
        "user": user,
        "old_face": old_face_url,
        "pending_face": pending_face_url,
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
    template = loader.get_template("home.html")
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

def userdash_view(request):
    month = int(request.GET.get('month', datetime.today().month))
    year = int(request.GET.get('year', datetime.today().year))

    cal = calendar.Calendar(firstweekday=0)
    month_days = list(cal.itermonthdays(year, month))
    weeks = [month_days[i:i+7] for i in range(0, len(month_days), 7)]
    day_names = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

    # --- NEW: Fetch approved leaves for the current user ---
    approved_leaves = LeaveRequest.objects.filter(
        user=request.user,
        status="Approved",
        start_date__year__lte=year,
        end_date__year__gte=year
    )

    # Collect all leave days in this month
    leave_days = set()
    for leave in approved_leaves:
        current_day = leave.start_date
        while current_day <= leave.end_date:
            if current_day.month == month:
                leave_days.add(current_day.day)
            current_day += timedelta(days=1)

    context = {
        "cal_year": year,
        "cal_month": month,
        "cal_month_name": calendar.month_name[month],
        "cal_weeks": weeks,
        "today_day": datetime.today().day,
        "today_month": datetime.today().month,
        "today_year": datetime.today().year,
        "day_names": day_names,
        "leave_days": leave_days,   # ✅ pass leave days to template
    }

    # If AJAX request, return only the calendar cells
    if request.GET.get('ajax') == '1':
        from django.template.loader import render_to_string
        html = render_to_string('calendar_cells.html', context)
        return HttpResponse(html)

    # Normal page render
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
def face_view(request):
    user = request.user

    # Check if an approved face exists
    try:
        approved = FaceChangeRequest.objects.get(user=user, status="Approved")
        # Use approved face as the main registered face
        old_face_url = approved.new_face_path.replace(settings.MEDIA_ROOT, settings.MEDIA_URL)
        face_status = "Face updated ✅"
        pending_face = False
    except FaceChangeRequest.DoesNotExist:
        # Fallback: check the original registered face folder
        old_face_path = os.path.join(settings.MEDIA_ROOT, f"faces/{user.username}/1.jpg")
        if os.path.exists(old_face_path):
            old_face_url = os.path.join(settings.MEDIA_URL, f"faces/{user.username}/1.jpg")
            face_status = "Registered Face"
        else:
            old_face_url = None
            face_status = "No face registered"
        pending_face = False

    # Check if there is any pending face request
    try:
        pending = FaceChangeRequest.objects.get(user=user, status="Pending")
        new_face_url = pending.new_face_path.replace(settings.MEDIA_ROOT, settings.MEDIA_URL)
        face_status = "Pending admin approval"
        pending_face = True
    except FaceChangeRequest.DoesNotExist:
        new_face_url = None

    context = {
        "user": user,
        "old_face_url": old_face_url,
        "new_face_url": new_face_url,
        "face_status": face_status,
        "pending_face": pending_face
    }
    return render(request, "face_view.html", context)


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