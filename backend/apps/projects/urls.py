from rest_framework.routers import DefaultRouter

from .views import MilestoneViewSet, ProjectMemberViewSet, ProjectViewSet

router = DefaultRouter()
router.register("projects", ProjectViewSet, basename="project")
router.register("project-members", ProjectMemberViewSet, basename="project-member")
router.register("milestones", MilestoneViewSet, basename="milestone")
urlpatterns = router.urls
