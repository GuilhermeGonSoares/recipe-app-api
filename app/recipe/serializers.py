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

    def _get_or_create_tags(self, tags, recipe):
        """Lidar com recuperar ou criar tags quando necessário"""
        auth_user = self.context['request'].user
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(
                user=auth_user,
                **tag,
            )
            recipe.tags.add(tag_obj)

    def create(self, validated_data): #Explicação I
        """Criar uma receita"""
        tags = validated_data.pop('tags', []) #Explicação II
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags, recipe)

        return recipe

    def update(self, instance, validated_data):
        """Atualizar uma receita"""
        tags = validated_data.pop('tags', None)
        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags, instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

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