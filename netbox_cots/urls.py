from django.urls import include, path
from utilities.urls import get_model_urls
from . import views

urlpatterns = [
    path("import/", views.CSVImportView.as_view(), name="csv_import"),
    path("installations/purge/", views.PurgeInstallationsView.as_view(), name="purge_installations"),
]

for route, name, list_view, detail_view, edit_view, delete_view in (
    ("applications", "application", views.ApplicationListView, views.ApplicationView, views.ApplicationEditView, views.ApplicationDeleteView),
    ("versions", "softwareversion", views.SoftwareVersionListView, views.SoftwareVersionView, views.SoftwareVersionEditView, views.SoftwareVersionDeleteView),
    ("role-assignments", "roleassignment", views.RoleAssignmentListView, views.RoleAssignmentView, views.RoleAssignmentEditView, views.RoleAssignmentDeleteView),
):
    urlpatterns += [
        path(f"{route}/", list_view.as_view(), name=f"{name}_list"),
        path(f"{route}/add/", edit_view.as_view(), name=f"{name}_add"),
        path(f"{route}/<int:pk>/", detail_view.as_view(), name=name),
        path(f"{route}/<int:pk>/edit/", edit_view.as_view(), name=f"{name}_edit"),
        path(f"{route}/<int:pk>/delete/", delete_view.as_view(), name=f"{name}_delete"),
        path(f"{route}/<int:pk>/", include(get_model_urls("netbox_cots", name))),
    ]

