"""
URL configuration for beegrafo project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from grafo.views import beedude, login_view, logout_view, MapaListView
from django.contrib.auth.decorators import login_required


urlpatterns = [
    #path('', login_required(beedude), name='beedude'),
    path('mapa/<int:pk>/', login_required(beedude), name='mapa-view'),
    path('', login_required(MapaListView.as_view()), name='mapa-list'),
    path('login/', login_view, name='login'),
    path('logout/', login_required(logout_view), name='logout'),
    path('admin/', include('massadmin.urls')),
    path('admin/', admin.site.urls),
]