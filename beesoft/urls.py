"""
URL configuration for beesoft project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from beeauth.views import login_view, logout_view
from beeapi.views import index
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('',  view=login_required(index)),
    path('admin/', admin.site.urls),
    path('beedude/', include('beeapi.urls')),
    path('login/', view=login_view, name='login'),
    path('logout/', view=logout_view, name='logout'),
]
