"""
Testes para API usuários
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')
ME_URL = reverse('user:me')

PAYLOAD = {
    'email': 'test@example.com',
    'password': 'testpass123',
    'name': 'Test Name',
}

def create_user(**params):
    """Criando e retornando um novo usuário para realizar os testes."""
    user = get_user_model().objects.create_user(**params)
    return user

class PublicUserApiTests(TestCase):
    """Testar os recursos, que não precisão de autenticação, para os usuários."""

    def setUp(self):
        self.client = APIClient()
    
    def test_create_user_success(self):
        """Testando se a criação de um usuário foi um sucesso"""

        res = self.client.post(CREATE_USER_URL, PAYLOAD)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=PAYLOAD['email'])
        self.assertTrue(user.check_password(PAYLOAD['password']))
        self.assertNotIn('password', res.data)

    def test_user_with_email_exists_error(self):
        """Testando se há o retorno de um erro quando criamos um user com email já existente"""
        create_user(**PAYLOAD)
        res = self.client.post(CREATE_USER_URL, PAYLOAD)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """Testando se a senha tem um comprimento mínimo"""
        PAYLOAD['password'] = 'pw'

        res = self.client.post(CREATE_USER_URL, PAYLOAD)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        user_exists = get_user_model().objects.filter(
            email=PAYLOAD['email']
        ).exists()
        self.assertFalse(user_exists)
    
    def test_create_token_for_user(self):
        """Testando a geração de token para a validar as credenciais"""
        create_user(**PAYLOAD)
        payload = {
            'email': PAYLOAD['email'],
            'password': PAYLOAD['password']
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """Testa o retorno de erro se as credenciais são inválidas"""
        create_user(email='test@example.com', password='goodpass')

        payload = {'email':'test@example.com','password': 'badpass'}
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_create_token_blank_password(self):
        """Test posting a blank password returns an error"""
        payload = {'email':'test@example.com','password': ''}
        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_user_unauthorized(self):
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateUserApiTests(TestCase):
    """Testar os recursos, que precisão de autenticação, para os usuários."""

    def setUp(self):
        self.user = create_user(
            email='test@example.com',
            password='testpass123',
            name='Test name'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, {
            'name': self.user.name,
            'email': self.user.email,
        })