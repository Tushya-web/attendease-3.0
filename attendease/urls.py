from django.contrib import admin
from django.urls import path
from django.conf.urls import include
from .text_face import verify_faces


urlpatterns = [
    path('admin/', admin.site.urls),
    # path("test_facenet/", verify_faces , name="test_facenet"),
    path('', include('accounts.urls')),
    path('accounts/', include('accounts.urls')),
]
