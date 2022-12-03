"""
Testes para a API de tag
"""
from decimal import Decimal

from core.models import Recipe, Tag
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from recipe.serializers import TagSerializer
from rest_framework import status
from rest_framework.test import APIClient

TAGS_URL = reverse('recipe:tag-list')

def detail_url(tag_id):
    return reverse('recipe:tag-detail', args=[tag_id])

def create_user(email='user@example.com', password='testpass123'):
    return get_user_model().objects.create_user(email=email, password=password)

class PublicTagsApiTests(TestCase):
    """Testa solicitações a API sem autenticação."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Testa se a autenticação é necessária para recuperar tag"""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTests(TestCase):
    """Testa solicitações a API com autenticação."""
    def setUp(self):
        self.client = APIClient()
        self.user = create_user()

        self.client.force_authenticate(self.user)
    
    def test_retrieve_tags(self):
        """Testa a listagem das tags cadastradas."""
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Dessert')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.data, serializer.data)

    def test_limited_to_user(self):
        """Testa se as tags recuperadas são do usuário que fez a solicitação"""
        other_user = create_user(email='another@example.com', password='testpass123')
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=other_user, name='Dessert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.filter(user=self.user).order_by('-name')
        serializer = TagSerializer(tags, many=True)

        self.assertEqual(res.data, serializer.data)

    def test_update_tag(self):
        """Testa a atualização da tag"""
        tag = Tag.objects.create(user=self.user, name='Vegan')
        
        payload = {'name': 'Dessert'}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag.refresh_from_db()

        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """Testa deletar uma tag"""
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        url = detail_url(tag.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        tags = Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filter_tags_assign_to_recipe(self):
        """Teste: Lista de tags que estão associadas a uma determinada receita"""
        tag1 = Tag.objects.create(user=self.user, name='Vegan')
        tag2 = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = Recipe.objects.create(
            user= self.user,
            title='Apple Crumble',
            time_minutes=5,
            price=Decimal('4.50')
        )
        recipe.tags.add(tag1)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag1)
        s2 = TagSerializer(tag2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        """Teste: Tags filtradas retornam uma lista única sem duplicadas."""
        tag = Tag.objects.create(user=self.user, name='Breakfast')
        Tag.objects.create(user=self.user, name='Dinner')
        recipe1 = Recipe.objects.create(
            user= self.user,
            title='Apple Crumble',
            time_minutes=5,
            price=Decimal('4.50')
        )
        recipe2 = Recipe.objects.create(
            user= self.user,
            title='Pancakes',
            time_minutes=5,
            price=Decimal('5.50')
        )
        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)

