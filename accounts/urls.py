from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Using built-in LoginView
    path('admin/', admin.site.urls),
    
    path("register/", views.register, name="register"),
    path('userlogin/', views.login_view, name='userlogin'),
    
    path('changepasssword/',views.change_password , name='change_password'),
    
    path('',views.index, name="home"),
    path('userprofile/', views.userprofile_view, name='userprofile'),
    path("userdash/", views.userdash_view, name="userdash"),
    
    path('face_add/', views.face_add, name='face_add'),
    # path("save_face/", views.save_face, name="save_face"),
    
    path('face_scan/', views.face_scan, name='face_scan'),
    path('mark_attendance/', views.mark_attendance_ajax, name='mark_attendance'),
    
    path('face_view/', views.face_view , name='face_view'),
    path('leaverequest/', views.leave_request_view , name='leave_request'), 
       
    path('attendance_report' , views.attendance_report , name='attendance_report'),
    # path("attendancemark/", views.mark_attendance_ajax, name="mark_attendance"),
    # path("attendance/my/", views.my_attendance, name="my_attendance"),
    # path("attendance/all/", views.all_attendance, name="all_attendance"),
    
    path("report/", views.attendance_report, name="attendance_report"),
    path("download/", views.download_attendance_csv, name="download_attendance_csv"),
    
    path('help_support/', views.help_support, name='help_support'),
    
    path("chatbot/", views.chatbot_view, name="chatbot"),
    path("chatbot/api/", views.chatbot_api, name="chatbot_api"),

    path("logout/", auth_views.LogoutView.as_view(next_page="userlogin"), name="logout")
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)