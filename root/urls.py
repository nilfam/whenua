import django_js_reverse.views
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.urls import include

from root import views, userviews

urlpatterns = [
    url(r'^tz_detect/', include('tz_detect.urls')),
    url(r'^jsreverse/$', django_js_reverse.views.urls_js, name='js_reverse'),
    url(r'^send-request/(?P<type>[0-9a-z-_]+)/$', views.send_request, name='send-request'),
    url(r'^send-request/(?P<module>[0-9a-z-_]+)/(?P<type>[0-9a-z-]+)/$', views.send_request,
        name='send-request'),
    url(r'^login$', userviews.UserSignInView.as_view(), name='login'),
    url(r'^register$', userviews.UserRegistrationView.as_view(), name='register'),
    url(r'^reset', userviews.UserResetPasswordView.as_view(), name='reset-password'),
    url(r'^forget', userviews.UserForgetPasswordView.as_view(), name='forget-password'),
    url(r'^logout$', userviews.sign_out, name='logout'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
