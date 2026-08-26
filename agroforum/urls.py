from django.urls import path
from . import views

app_name = "agroforum"
urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("topics/", views.topic_list, name="topic_list"),
    path("topics/<slug:slug>/", views.topic_detail, name="topic"),
    path("new/", views.post_create, name="post_create"),
    path("<int:pk>/", views.post_detail, name="post_detail"),
    path("<int:pk>/edit/", views.post_edit, name="post_edit"),
    path("<int:pk>/delete/", views.post_delete, name="post_delete"),
    path("<int:pk>/like/", views.post_like, name="post_like"),
    path("comment/<int:pk>/like/", views.comment_like, name="comment_like"),
    path("comment/<int:pk>/reply-form/", views.comment_reply_form, name="comment_reply_form"),
    path("comment/<int:pk>/delete/", views.comment_delete, name="comment_delete"),
]