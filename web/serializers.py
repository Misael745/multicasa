from rest_framework import serializers
from .models import Casa, ImagenCasa

class ImagenCasaSerializer(serializers.ModelSerializer):
    """ Serializador para las imágenes de una casa """

    class Meta:
        model = ImagenCasa
        fields = ['imagen', 'texto_alternativo']


class CasaListSerializer(serializers.ModelSerializer):
    """
    Serializador para mostrar la lista de casas en la API.
    """
    # 'imagenes' es el 'related_name' que definimos en el modelo
    imagenes = ImagenCasaSerializer(many=True, read_only=True)

    class Meta:
        model = Casa
        # Definimos los campos que queremos exponer en la API
        fields = [
            'id_casa',
            'titulo',
            'precio',
            'estatus',
            'habitaciones',
            'banos',
            'superficie_m2',
            'imagenes'  # Añadimos las imágenes
        ]

class CasaDetailSerializer(serializers.ModelSerializer):
        """
        Serializador para mostrar TODOS los detalles de una casa
        """
        imagenes = ImagenCasaSerializer(many=True, read_only=True)

        class Meta:
            model = Casa
            fields = [
            'id_casa', 'titulo', 'descripcion', 'precio', 'direccion',
            'latitud', 'longitud', 'estatus', 'habitaciones', 'banos',
            'superficie_m2', 'fecha_publicacion', 'imagenes'
        ]
            
class CasaCreateSerializer(serializers.ModelSerializer):
    """
    Serializador para CREAR y ACTUALIZAR casas
    """
    class Meta:
        model = Casa
        fields = [
            'titulo', 'descripcion', 'precio', 'direccion',
            'latitud', 'longitud', 'estatus', 'habitaciones', 
            'banos', 'superficie_m2'
        ]