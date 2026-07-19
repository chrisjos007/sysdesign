from django.urls import path

from . import views

app_name = 'learn'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('book/<slug:book_slug>/', views.book_detail, name='book_detail'),
    path('chapter/<slug:chapter_slug>/', views.chapter_detail, name='chapter_detail'),
    path('concept/<slug:concept_slug>/', views.concept_detail, name='concept_detail'),
    path('concept/<slug:concept_slug>/quiz/', views.concept_quiz, name='concept_quiz'),
    path('review/', views.review_queue, name='review_queue'),
    path('badges/', views.badges_view, name='badges'),
    path('toggle-unlock-all/', views.toggle_unlock_all, name='toggle_unlock_all'),
    path('signup/', views.signup, name='signup'),
    path('build/<slug:challenge_slug>/', views.design_challenge, name='design_challenge'),
    path('match/<slug:challenge_slug>/', views.matching_challenge, name='matching_challenge'),
    path('order/<slug:challenge_slug>/', views.ordering_challenge, name='ordering_challenge'),
]
