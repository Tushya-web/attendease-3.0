import os
import cv2
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.shortcuts import render
from django.utils.html import format_html  # ✅ use this
from .models import Attendance, CustomUser, FaceChangeRequest, LeaveRequest, PendingFaceUpdate
from django.contrib.admin.views.decorators import staff_member_required


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "enrollment_no", "user_type", "is_approved", "has_face_data")
    list_filter = ("is_approved", "user_type", "has_face_data")
    actions = ["approve_users"]

    def approve_users(self, request, queryset):
        queryset.update(is_approved=True)
    approve_users.short_description = "Approve selected users"


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "user_type", "start_date", "end_date", "leave_type", "created_at", "status")
    list_filter = ("status", "leave_type", "user__user_type")
    search_fields = ("user__username", "user__enrollment_no")

    def user_type(self, obj):
        return obj.user.user_type

    actions = ["approve_leaves", "reject_leaves"]

    def approve_leaves(self, request, queryset):
        queryset.update(status="Approved")
    approve_leaves.short_description = "Approve selected leave requests"

    def reject_leaves(self, request, queryset):
        queryset.update(status="Rejected")
    reject_leaves.short_description = "Reject selected leave requests"


@staff_member_required
def all_attendance(request):
    records = Attendance.objects.select_related("user").order_by("-date")
    return render(request, "attendance/all_attendance.html", {"records": records})


# @admin.register(PendingFaceUpdate)
# class PendingFaceUpdateAdmin(admin.ModelAdmin):
#     list_display = ("user", "status", "created_at")
#     list_filter = ("status",)
#     actions = ["approve_update", "reject_update"]

#     def approve_update(self, request, queryset):
#         for pending in queryset:
#             user_folder = os.path.join(settings.MEDIA_ROOT, "faces", pending.user.username)
#             os.makedirs(user_folder, exist_ok=True)
#             new_img_path = os.path.join(user_folder, "face_updated.jpg")
#             with open(pending.new_image.path, "rb") as f:
#                 with open(new_img_path, "wb") as new_f:
#                     new_f.write(f.read())

#             pending.user.has_face_data = True
#             pending.user.save()

#             pending.status = "Approved"
#             pending.save()

#     approve_update.short_description = "Approve selected face updates"

#     def reject_update(self, request, queryset):
#         queryset.update(status="Rejected")
#     reject_update.short_description = "Reject selected face updates"


@admin.register(FaceChangeRequest)
class FaceChangeRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "created_at", "preview_old", "preview_new")
    actions = ["approve_request", "reject_request"]

    def preview_old(self, obj):
        if hasattr(obj, "old_image") and obj.old_image:
            return format_html("<img src='{}' width='50'/>", obj.old_image.url)
        user_path = f"{settings.MEDIA_URL}faces/{obj.user.username}/{obj.user.username}_1.jpg"
        return format_html("<img src='{}' width='50'/>", user_path)
    preview_old.short_description = "Old Face"

    def preview_new(self, obj):
        if hasattr(obj, "new_image") and obj.new_image:
            return format_html("<img src='{}' width='50'/>", obj.new_image.url)
        elif obj.new_face_path:
            relative_path = obj.new_face_path.replace(str(settings.MEDIA_ROOT), "").lstrip("/")
            return format_html("<img src='{}{}' width='50'/>", settings.MEDIA_URL, relative_path)
        return "No Image"
    preview_new.short_description = "New Face"

    def approve_request(self, request, queryset):
        for obj in queryset:
            if obj.status == "Pending":
                from .face_system import add_face_image
                # Apply the new face image
                if hasattr(obj, "new_image") and obj.new_image:
                    add_face_image(obj.user.username, cv2.imread(obj.new_image.path))
                elif obj.new_face_path:
                    add_face_image(obj.user.username, cv2.imread(obj.new_face_path))
                obj.status = "Approved"
                obj.save()
    approve_request.short_description = "Approve selected face changes"

    def reject_request(self, request, queryset):
        for obj in queryset:
            if obj.status == "Pending":
                # Do NOT call add_face_image; old face remains active
                obj.status = "Rejected"
                obj.save()
    reject_request.short_description = "Reject selected face changes"