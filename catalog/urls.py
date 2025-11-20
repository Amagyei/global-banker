from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CountryViewSet, BankViewSet, AccountViewSet, FullzViewSet, FullzPackageViewSet

router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'banks', BankViewSet, basename='bank')
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'fullzs', FullzViewSet, basename='fullz')
router.register(r'fullz-packages', FullzPackageViewSet, basename='fullz-package')

urlpatterns = [
    path('', include(router.urls)),
]

