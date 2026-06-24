"""URL configuration for the bookstore example.

Routes:
- /admin/        Django admin (django.contrib.admin)
- /api/          DRF browsable API + ViewSets registered on a DefaultRouter
- /api/token/    obtain a DRF auth token (POST username/password)
- /api-auth/     session login/logout for the browsable API
"""

from django.contrib import admin
from django.urls import include
from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from bookstore.views import AuthorViewSet
from bookstore.views import BookViewSet
from bookstore.views import CategoryViewSet
from bookstore.views import book_list

router = DefaultRouter()
router.register("authors", AuthorViewSet)
router.register("categories", CategoryViewSet)
router.register("books", BookViewSet)

urlpatterns = [
    path("", book_list, name="book_list"),
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/token/", obtain_auth_token, name="api_token"),
    path("api-auth/", include("rest_framework.urls")),
]
