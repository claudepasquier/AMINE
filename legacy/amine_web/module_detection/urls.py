from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('results/<query_id>/', views.results, name='results'),
    path('results/<query_id>/download/', views.download_file),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]
