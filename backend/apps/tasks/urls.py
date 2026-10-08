from rest_framework.routers import DefaultRouter

from .views import AttachmentViewSet, CommentViewSet, SprintViewSet, TaskDependencyViewSet, TaskViewSet

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("sprints", SprintViewSet, basename="sprint")
router.register("task-dependencies", TaskDependencyViewSet, basename="task-dependency")
router.register("attachments", AttachmentViewSet, basename="attachment")
router.register("comments", CommentViewSet, basename="comment")
urlpatterns = router.urls
