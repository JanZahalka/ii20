"""tetris URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.2/topics/http/urls/
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

import aimodel.views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', aimodel.views.index),
    path('main', aimodel.views.main),
    path('analytics_session', aimodel.views.analytics_session),
    path('login', aimodel.views.log_in),
    path('logout', aimodel.views.log_out),
    path('bucket_info', aimodel.views.bucket_info),
    path('create_bucket', aimodel.views.create_bucket),
    path('delete_bucket', aimodel.views.delete_bucket),
    path('rename_bucket', aimodel.views.rename_bucket),
    path('swap_buckets', aimodel.views.swap_buckets),
    path('toggle_bucket', aimodel.views.toggle_bucket),
    path('interaction_round', aimodel.views.interaction_round),
    path('bucket_view_data', aimodel.views.bucket_view_data),
    path('toggle_mode', aimodel.views.toggle_mode),
    path('grid_set_size', aimodel.views.grid_set_size),
    path('transfer_images', aimodel.views.transfer_images),
    path('fast_forward', aimodel.views.fast_forward),
    path('ff_commit', aimodel.views.ff_commit),
    path('end_session', aimodel.views.end_session),
]
