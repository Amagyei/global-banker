from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CountryViewSet, BankViewSet, AccountViewSet

router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'banks', BankViewSet, basename='bank')
router.register(r'accounts', AccountViewSet, basename='account')

urlpatterns = [
    path('', include(router.urls)),
]

