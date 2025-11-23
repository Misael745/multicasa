from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import base64
import re
import requests
from time import sleep

def validar_codigo_postal(value):
    """
    Valida que el código postal tenga formato mexicano (5 dígitos)
    """
    if value and not re.match(r'^\d{5}$', value):
        raise ValidationError('El código postal debe tener exactamente 5 dígitos.')

def validar_precio_positivo(value):
    """
    Valida que el precio sea positivo
    """
    if value <= 0:
        raise ValidationError('El precio debe ser mayor a 0.')

def validar_superficie_positiva(value):
    """
    Valida que la superficie sea positiva
    """
    if value and value <= 0:
        raise ValidationError('La superficie debe ser mayor a 0.')

def validar_habitaciones_positivas(value):
    """
    Valida que el número de habitaciones sea positivo
    """
    if value and value <= 0:
        raise ValidationError('El número de habitaciones debe ser mayor a 0.')

def validar_banos_positivos(value):
    """
    Valida que el número de baños sea positivo
    """
    if value and value <= 0:
        raise ValidationError('El número de baños debe ser mayor a 0.')

def validar_latitud(value):
    """
    Valida que la latitud esté en rango válido (-90 a 90)
    """
    if value and (value < -90 or value > 90):
        raise ValidationError('La latitud debe estar entre -90 y 90.')

def validar_longitud(value):
    """
    Valida que la longitud esté en rango válido (-180 a 180)
    """
    if value and (value < -180 or value > 180):
        raise ValidationError('La longitud debe estar entre -180 y 180.')

def geocodificar_direccion(direccion, municipio, estado, codigo_postal):
    """
    Obtiene latitud y longitud automáticamente usando Nominatim (OpenStreetMap)
    """
    # Construir la dirección completa para geocodificación
    partes_direccion = []
    if direccion:
        partes_direccion.append(direccion)
    if municipio:
        partes_direccion.append(municipio)
    if estado:
        partes_direccion.append(estado)
    if codigo_postal:
        partes_direccion.append(codigo_postal)
    
    if not partes_direccion:
        return None, None
    
    direccion_completa = ", ".join(partes_direccion) + ", México"
    
    try:
        # API de Nominatim (OpenStreetMap) - Gratuita
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': direccion_completa,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'mx'  # Limitar a México
        }
        
        # Headers para ser un buen ciudadano de la API
        headers = {
            'User-Agent': 'Multicasa/1.0 (contacto@multicasa.com)'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        # Respuesta amigable con la API
        sleep(1)
        
        if response.status_code == 200:
            data = response.json()
            if data:
                lat = float(data[0]['lat'])
                lon = float(data[0]['lon'])
                return lat, lon
        
        return None, None
        
    except Exception as e:
        print(f"Error en geocodificación: {e}")
        return None, None

class Casa(models.Model):
    """
    Modelo que representa una propiedad o vivienda en la base de datos.
    """
    ESTATUS_CHOICES = [
        ('en venta', 'En Venta'),
        ('vendida', 'Vendida'),
    ]

    # --- Campos Principales con Validaciones ---
    id_casa = models.AutoField(primary_key=True)
    titulo = models.CharField(
        max_length=255,
        help_text="Título descriptivo de la propiedad"
    )
    descripcion = models.TextField(
        null=True, 
        blank=True,
        help_text="Descripción detallada de la propiedad"
    )
    precio = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[validar_precio_positivo],
        help_text="Precio en pesos mexicanos"
    )
    
    # --- Campos de Ubicación con Validaciones ---
    direccion = models.CharField(
        max_length=255, 
        null=True, 
        blank=True,
        help_text="Dirección completa de la propiedad"
    )
    municipio = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="Municipio",
        help_text="Municipio donde se encuentra la propiedad"
    )
    estado = models.CharField(
        max_length=100, 
        null=True, 
        blank=True, 
        verbose_name="Estado",
        help_text="Estado donde se encuentra la propiedad"
    )
    codigo_postal = models.CharField(
        max_length=10, 
        null=True, 
        blank=True, 
        verbose_name="Código Postal",
        validators=[validar_codigo_postal],
        help_text="Código postal de 5 dígitos"
    )
    
    latitud = models.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        null=True, 
        blank=True,
        validators=[validar_latitud],
        help_text="Coordenada de latitud (-90 a 90) - Se llena automáticamente"
    )
    longitud = models.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        null=True, 
        blank=True,
        validators=[validar_longitud],
        help_text="Coordenada de longitud (-180 a 180) - Se llena automáticamente"
    )

    # --- Campos de Características con Validaciones ---
    estatus = models.CharField(
        max_length=10, 
        choices=ESTATUS_CHOICES, 
        default='en venta'
    )
    habitaciones = models.IntegerField(
        null=True, 
        blank=True,
        validators=[validar_habitaciones_positivas],
        help_text="Número de habitaciones"
    )
    banos = models.IntegerField(
        null=True, 
        blank=True,
        validators=[validar_banos_positivos],
        help_text="Número de baños"
    )
    superficie_m2 = models.IntegerField(
        null=True, 
        blank=True,
        validators=[validar_superficie_positiva],
        help_text="Superficie en metros cuadrados"
    )
    
    fecha_publicacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

    def clean(self):
        """
        Validación adicional a nivel de modelo
        """
        super().clean()
        
        # Validar que si hay coordenadas, ambas estén presentes
        if (self.latitud is not None and self.longitud is None) or \
           (self.latitud is None and self.longitud is not None):
            raise ValidationError({
                'latitud': 'Si proporciona coordenadas, debe incluir tanto latitud como longitud.',
                'longitud': 'Si proporciona coordenadas, debe incluir tanto latitud como longitud.'
            })
        
        # Validar que el municipio y estado vayan juntos
        if (self.municipio and not self.estado) or (not self.municipio and self.estado):
            raise ValidationError({
                'municipio': 'Si proporciona municipio, debe incluir también el estado.',
                'estado': 'Si proporciona estado, debe incluir también el municipio.'
            })

    def geocodificar_automaticamente(self):
        """
        Geocodifica automáticamente la dirección si no hay coordenadas
        """
        if not self.latitud or not self.longitud:
            if self.direccion or self.municipio or self.estado:
                lat, lon = geocodificar_direccion(
                    self.direccion, 
                    self.municipio, 
                    self.estado, 
                    self.codigo_postal
                )
                if lat and lon:
                    self.latitud = lat
                    self.longitud = lon
                    return True
        return False

    def ubicacion_completa(self):
        """
        Devuelve la ubicación completa formateada
        """
        partes = []
        if self.direccion:
            partes.append(self.direccion)
        if self.municipio:
            partes.append(self.municipio)
        if self.estado:
            partes.append(self.estado)
        if self.codigo_postal:
            partes.append(f"CP: {self.codigo_postal}")
        return ", ".join(partes) if partes else "Ubicación no especificada"

    def save(self, *args, **kwargs):
        """
        Sobrescribir save para ejecutar validaciones y geocodificación automática
        """
        self.full_clean()  # Ejecuta todas las validaciones
        
        # Intentar geocodificación automática si no hay coordenadas
        if not self.latitud or not self.longitud:
            self.geocodificar_automaticamente()
        
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Casa"
        verbose_name_plural = "Casas"


class ImagenBase(models.Model):
    """
    Galería central de imágenes disponibles para todas las casas
    """
    id_imagen = models.AutoField(primary_key=True)
    nombre = models.CharField(
        max_length=255, 
        help_text="Nombre descriptivo de la imagen"
    )
    imagen_data = models.BinaryField(verbose_name="Datos de la imagen")
    tipo_contenido = models.CharField(
        max_length=100, 
        help_text="Tipo MIME (ej: image/jpeg, image/png)"
    )
    categoria = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        help_text="Categoría (ej: exterior, interior, jardín)"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.nombre
    
    def get_image_src(self):
        """
        Genera el src para usar en etiquetas img HTML
        """
        if self.imagen_data and self.tipo_contenido:
            base64_data = base64.b64encode(self.imagen_data).decode('utf-8')
            return f"data:{self.tipo_contenido};base64,{base64_data}"
        return None

    class Meta:
        verbose_name = "Imagen de Galería"
        verbose_name_plural = "Imágenes de Galería"
        ordering = ['nombre']


class ImagenCasa(models.Model):
    """
    Relación entre casas e imágenes de la galería central
    """
    id_imagen_casa = models.AutoField(primary_key=True)
    casa = models.ForeignKey(Casa, on_delete=models.CASCADE, related_name='imagenes')
    imagen_base = models.ForeignKey(ImagenBase, on_delete=models.CASCADE, verbose_name="Imagen de la galería")
    texto_alternativo = models.CharField(max_length=100, null=True, blank=True)
    orden = models.IntegerField(default=0)

    def __str__(self):
        return f"Imagen de {self.casa.titulo} - {self.imagen_base.nombre}"

    def get_image_src(self):
        return self.imagen_base.get_image_src()

    class Meta:
        verbose_name = "Imagen de Casa"
        verbose_name_plural = "Imágenes de Casas"
        ordering = ['orden']