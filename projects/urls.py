from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.project_list, name='project_list'),
    path('<int:project_id>/', views.project_detail, name='project_detail'),
    path('<int:project_id>/board/', views.project_board, name='project_board'),
    path('<int:project_id>/backlog/', views.project_backlog, name='project_backlog'),
    path('<int:project_id>/sprints/', views.project_sprints, name='project_sprints'),
    path('<int:project_id>/tickets/new/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:ticket_id>/edit/', views.ticket_edit, name='ticket_edit'),
    path('tickets/<int:ticket_id>/cancel/', views.ticket_cancel, name='ticket_cancel'),
    path('tickets/<int:ticket_id>/delete/', views.ticket_delete, name='ticket_delete'),
    path('tickets/<int:ticket_id>/comment/', views.comment_create, name='comment_create'),
    path('tickets/<int:ticket_id>/move-to-sprint/', views.move_ticket_to_sprint, name='move_to_sprint'),
    path('tickets/<int:ticket_id>/update-status/', views.update_ticket_status, name='update_ticket_status'),
    path('sprints/<int:sprint_id>/update-status/', views.update_sprint_status, name='update_sprint_status'),
]