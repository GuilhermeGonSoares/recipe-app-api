"""
Serializer for recipe APIs
"""
from core.models import Recipe, Tag
from rest_framework import serializers


class TagSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ['id', 'name']
        read_only_fields = ['id']

class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, required=False)
    class Meta:
        model = Recipe
        fields =  ['id', 'title', 'time_minutes', 'price', 'link', 'tags']
        read_only_fields = ['id']

    def create(self, validated_data): #Explicação I
        """Criar uma receita"""
        tags = validated_data.pop('tags', []) #Explicação II
        recipe = Recipe.objects.create(**validated_data)
        auth_user = self.context.get('request').user
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(
                user=auth_user,
                **tag,
            )
            recipe.tags.add(tag_obj)
        return recipe
class RecipeDetailSerializer(RecipeSerializer):
    
    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']


'''
I)Precisamos sobrescrever o método de criar(create) receita porque estamos usando
serialização aninhada e por padrão ela vem definida como somenete leitura(read_only)

II) Usamos 'pop' porque queremos ter certeza de que removemos as tags antes de
criarmos a receita. Porque se passarmos as tags diretamente para o modelo de
receita, isso não funcionará, porque o modelo de receita espera que as tags
sejam atribuidas como um campo de relacionamento, ou seja, espera que seja criado
separadamente e adicionado como uma relação à receita -> ManyToMany

'''