from django.urls import include, re_path
from django.contrib.auth import views as auth_views
from django.contrib.flatpages import views as flatpages_views
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView
from django.contrib.auth.views import PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from portal.views import user_detail

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    re_path(r'^', include('portal.urls')),
    re_path(r'^admin/', admin.site.urls),
    #re_path(r'^api/', include('api.urls')),
    re_path(r'^dns/', include('dns.urls')),
    re_path(r'^login/$', LoginView.as_view(), name='login'),
    re_path(r'^accounts/login/$', LoginView.as_view(), name='login'),
    re_path(r'^accounts/logout/$', LogoutView.as_view(), name='logout'),
    re_path(r'^accounts/profile/$', user_detail, name='user_detail'),
    re_path(r'^password/change/$',
        PasswordChangeView.as_view(), name='password_change'),
    re_path(r'^password/change/done/$',
        PasswordChangeDoneView.as_view(), name='password_change_done'),
    re_path(r'^password/reset/$',
        PasswordResetView.as_view(), name='password_reset'),
    re_path(r'^password/reset/done/$',
        PasswordResetDoneView.as_view(), name='password_reset_done'),
    re_path(r'^password/reset/complete/$',
        PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    re_path(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    re_path(r'^(?P<url>.*/)$', flatpages_views.flatpage),
]
