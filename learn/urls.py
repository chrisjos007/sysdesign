from django.urls import path

from . import views

app_name = 'learn'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('topic/<slug:topic_slug>/', views.topic_detail, name='topic_detail'),
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
    path('code/<slug:challenge_slug>/', views.coding_challenge, name='coding_challenge'),
    path('flaw/<slug:challenge_slug>/', views.flaw_challenge, name='flaw_challenge'),
    path('flaw/<slug:challenge_slug>/move/', views.flaw_move, name='flaw_move'),
    path('traffic/<slug:challenge_slug>/', views.traffic_challenge, name='traffic_challenge'),
    path('traffic/<slug:challenge_slug>/finish/', views.traffic_finish, name='traffic_finish'),
]
