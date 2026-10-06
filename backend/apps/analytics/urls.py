from django.urls import path

from . import views

urlpatterns = [
    path("search/", views.SearchView.as_view()),
    path("overview/", views.OverviewView.as_view()),
    path("projects/<int:pk>/summary/", views.ProjectSummaryView.as_view()),
    path("workload/", views.WorkloadView.as_view()),
    path("velocity/", views.VelocityView.as_view()),
    path("overdue/", views.OverdueTasksView.as_view()),
    path("audit/", views.AuditLogView.as_view()),
]
