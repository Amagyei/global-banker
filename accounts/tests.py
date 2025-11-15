from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AuthTests(APITestCase):
    def test_register_success(self):
        url = reverse('register')
        data = {
            'email': 'user@example.com',
            'password': 'StrongPass123!',
            'password_confirm': 'StrongPass123!',
            'first_name': 'Test',
            'last_name': 'User',
        }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', res.data)
        self.assertIn('access', res.data['tokens'])
        self.assertTrue(User.objects.filter(email='user@example.com').exists())

    def test_login_success(self):
        user = User.objects.create_user(
            username='user@example.com', email='user@example.com', password='StrongPass123!'
        )
        url = reverse('login')
        data = { 'email': 'user@example.com', 'password': 'StrongPass123!' }
        res = self.client.post(url, data, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('access', res.data['tokens'])

    def test_login_invalid_credentials(self):
        url = reverse('login')
        res = self.client.post(url, { 'email': 'nope@example.com', 'password': 'bad' }, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_requires_auth(self):
        url = reverse('profile-me')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_get_and_patch(self):
        user = User.objects.create_user(
            username='user2@example.com', email='user2@example.com', password='StrongPass123!'
        )
        login_res = self.client.post(reverse('login'), { 'email': 'user2@example.com', 'password': 'StrongPass123!' }, format='json')
        access = login_res.data['tokens']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')

        # GET
        res_get = self.client.get(reverse('profile-me'))
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(res_get.data['email'], 'user2@example.com')

        # PATCH
        res_patch = self.client.patch(reverse('profile-me'), { 'first_name': 'New' }, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data['first_name'], 'New')

# Create your tests here.
