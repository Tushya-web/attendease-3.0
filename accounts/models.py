from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings  

# Create your models here.

class CustomUser(AbstractUser):
    enrollment_no = models.CharField(max_length=11 , null=True , unique=True , blank=True)
    # institute_email = models.EmailField(unique=True)
    user_type = models.CharField(
        max_length=10,
        choices=(("student", "Student") , ("faculty", "Faculty")),
        default="student"
    )
    is_approved = models.BooleanField(default=False)  #For check wheather the user is approved or not
    has_face_data = models.BooleanField(default=False)  

class PendingFaceUpdate(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    new_image = models.ImageField(upload_to="pending_faces/")
    old_image = models.ImageField(upload_to="faces/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=[("Pending","Pending"), ("Approved","Approved"), ("Rejected","Rejected")], default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)    

class FaceChangeRequest(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    new_face_path = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)


LEAVE_TYPES = [
    ("sick leave", "Sick Leave"),
    ("casual leave", "Casual Leave"),
    ("vacation", "Vacation"),
    ("emergency", "Emergency"),
    ("other", "Other"),
]

class LeaveRequest(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leave_requests")
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.CharField(max_length=50)
    reason = models.TextField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.user.user_type}) - {self.leave_type} [{self.status}]"
    
    
class Attendance(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.date}"