import os
import tempfile
from decimal import Decimal

from core.models import Ingredient, Recipe, Tag
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from recipe.serializers import RecipeDetailSerializer, RecipeSerializer
from rest_framework import status
from rest_framework.test import APIClient

RECIPES_URL = reverse('recipe:recipe-list')

def image_upload_url(recipe_id):
    """Create and return a recipe detail URL."""
    return reverse('recipe:recipe-upload-image', args=[recipe_id])

def detail_url(recipe_id):
    return reverse('recipe:recipe-detail', args=[recipe_id])

def create_recipe(user, **params):
    """Criando e retornando uma receita para os testes"""
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 13,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe

class PublicRecipeAPITests(TestCase):
    "Testes para solicitações não autenticadas para a API."

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Testa se é necessária a autenticação para uma chamada da API"""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateRecipeAPITests(TestCase):
    
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email='test@example.com',
            password='testpass123',
        )
        self.client.force_authenticate(self.user) 


    def test_retrive_recipes(self):
        """Testa a lista de receitas."""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Testa se a lista de receitas é limitada a usuários autenticados."""
        other_user = get_user_model().objects.create_user(
            'test2@example.com',
            'testpass123',
        )
        create_recipe(other_user)
        create_recipe(self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)
    
    def test_get_recipe_detail(self):
        """Testa o GET para uma receita específica."""
        recipe = create_recipe(user=self.user)

        res = self.client.get(detail_url(recipe.id))

        serializer = RecipeDetailSerializer(recipe)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Teste: Criar uma receita."""
        payload = {
            'title': 'Sample recipe',
            'time_minutes': 13,
            'price': Decimal('5.25'),
        }

        res = self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        
        recipe = Recipe.objects.get(id=res.data['id'])
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_create_recipe_with_new_tags(self):
        """Teste: Criar receita com a criação da tag também."""
        payload = {
            'title': 'Thai Prawn Curry',
            'time_minutes': 30,
            'price': Decimal('2.50'),
            'tags':[{'name': 'Thai'}, {'name': 'Dinner'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        """Teste: Criar uma receita com tags já existentes"""
        tag_indian = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Pongal',
            'time_minutes': 60,
            'price': Decimal('4.50'),
            'tags': [{'name': 'Indian'}, {'name': 'Breakfast'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indian, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags.filter(
                name=tag['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)
    
    def test_create_tag_on_update(self):
        """Teste: Criar tag quando atualizamos uma receita"""
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assing_tag(self):
        """Teste: Atribuir uma tag existente ao atualizar uma receita"""
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        
        tag_lunch = Tag.objects.create(user=self.user, name='Lunch')
        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())
        self.assertEqual(recipe.tags.count(), 1)

    def test_clear_recipe_tags(self):
        """Teste: remover todas as tags da receita"""
        tag = Tag.objects.create(user=self.user, name='Dessert')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)
        
        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_ingredients(self):
        """Teste: Criar receitas com novos ingredients."""
        payload = {
        'title': 'Cauliflower Tacos',
        'time_minutes': 60,
        'price': Decimal('5.25'),
        'ingredients': [{'name': 'Cauliflower'}, {'name': 'Salt'}],
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf',
        }

        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        for ingredient in payload['ingredients']:
            exist = recipe.ingredients.filter(name=ingredient['name'], user=self.user).exists()
            self.assertTrue(exist)

    def test_create_recipe_with_existing_ingredients(self):
        """Teste: Criar receita com igredientes já cadastrados."""
        Ingredient.objects.create(user=self.user, name='Salt')
        payload = {
        'title': 'Cauliflower Tacos',
        'time_minutes': 60,
        'price': Decimal('5.25'),
        'ingredients': [{'name': 'Cauliflower'}, {'name': 'Salt'}],
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf',
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)

    def test_create_ingredient_on_update(self):
        """Teste: Criação de um ingrediente ao atualizar uma receita"""
        recipe = create_recipe(user=self.user) 
        payload = {'ingredients': [{'name': 'Salt'}, {'name': 'Vanilla'}]}

        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_ingredient = Ingredient.objects.get(user=self.user, name='Salt')
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assing_ingredient(self):
        """Teste: Atribuir um ingrediente existente ao atualizar uma receita."""
        ingredient1 = Ingredient.objects.create(user=self.user, name='Salt')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name='Vanilla')
        payload = {'ingredients': [{'name': 'Vanilla'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Ingredient.objects.filter(user=self.user).count(), 2)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())
    
    def test_clear_recipe_ingredient(self):
        """Teste: Atualizar a receita com nenhum ingrediente cadastrado."""
        ingrediente1 = Ingredient.objects.create(user=self.user, name='Pepper')
        ingrediente2 = Ingredient.objects.create(user=self.user, name='Chili')
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingrediente1)
        recipe.ingredients.add(ingrediente2)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotIn(ingrediente1, recipe.ingredients.all())
        self.assertNotIn(ingrediente2, recipe.ingredients.all())
        self.assertEqual(recipe.ingredients.count(), 0)

class ImageUploadTests(TestCase):
    """Teste para o upload da API image"""
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'password123',
        )
        self.client.force_authenticate(self.user)
        self.recipe = create_recipe(user=self.user)

    def tearDown(self):
        """É chamado no final do teste com o objetivo de limpar a imagem que foi associada ao teste, uma vez que não queremos acumular imagens teste no servidor."""
        self.recipe.image.delete()

    def test_upload_image(self):
        """Test uploading an image to a recipe."""
        url = image_upload_url(self.recipe.id)
        with tempfile.NamedTemporaryFile(suffix='.jpg') as image_file:
            img = Image.new('RGB', (10, 10))
            img.save(image_file, format='JPEG')
            image_file.seek(0)
            payload = {'image': image_file}
            res = self.client.post(url, payload, format='multipart')

        self.recipe.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn('image', res.data)
        self.assertTrue(os.path.exists(self.recipe.image.path))


