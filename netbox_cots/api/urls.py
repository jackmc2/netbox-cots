from netbox.api.routers import NetBoxRouter
from .views import ApplicationViewSet, SoftwareVersionViewSet, InstallationViewSet

router = NetBoxRouter()
router.register("applications", ApplicationViewSet)
# basename must follow the model name for NetBox hyperlinked serializers.
router.register("versions", SoftwareVersionViewSet, basename="softwareversion")
router.register("installations", InstallationViewSet)
urlpatterns = router.urls
