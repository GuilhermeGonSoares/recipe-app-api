from core.models import Ingredient
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from recipe.serializers import IngredientSerializer
from rest_framework import status
from rest_framework.test import APIClient

INGREDIENTS_URL = reverse('recipe:ingredient-list')

def detail_url(ingredient_id):
    return reverse('recipe:ingredient-detail', args=[ingredient_id])

def create_user(email='user@example.com', password='testpass123'):
    return get_user_model().objects.create_user(email=email, password=password)

class PublicIngredientApiTests(TestCase):
    """Teste: Solicitações(Requests) à API sem autenticação"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Testa se autenticação é necessária para recuperar ingredientes"""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateIngredientApiTests(TestCase):
    """Testa as requests autenticadas"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)
    
    def test_retrieve_ingredients(self):
        """Teste: Recuperar uma lista dos igredientes do usuário"""
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Vanilla')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """Teste: Lista de ingredientes está limitada aos usuários autenticados."""
        user2 = create_user(email='user2@example.com')
        ingredient1 = Ingredient.objects.create(user=user2, name='Salt')
        Ingredient.objects.create(user=self.user, name='Salt')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.filter(user=self.user).order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertNotIn(ingredient1, serializer.data)

    def test_update_ingredient(self):
        """Teste: Atualização de ingredientes"""
        ingredient = Ingredient.objects.create(user=self.user, name='Salt')
        payload = {'name': 'Vanilla'}

        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])
    
    def test_delete_ingredient(self):
        """Teste: Deletar ingrediente"""
        i1 = Ingredient.objects.create(user=self.user, name='Salt')
        i2 = Ingredient.objects.create(user=self.user, name='Vanilla')

        url = detail_url(i2.id)
        res = self.client.delete(url)

        ingredients = Ingredient.objects.filter(user=self.user)
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn(i2, serializer.data)
        self.assertEqual(ingredients.count(), 1)
