from django.contrib import admin
from .models import Casa, ImagenCasa
from django.contrib import messages

# Esta clase nos permitirá añadir/editar imágenes DESDE el admin de Casa
class ImagenCasaInline(admin.StackedInline):
    model = ImagenCasa
    extra = 1  # Cuántos formularios de imagen mostrar por defecto


# Esta es la configuración principal para el modelo Casa
class CasaAdmin(admin.ModelAdmin):
    # Qué campos mostrar en la lista de casas
    list_display = ('titulo', 'precio', 'estatus', 'habitaciones', 'banos', 'fecha_publicacion')

    # Qué campos se pueden usar para filtrar en el admin
    list_filter = ('estatus', 'precio')

    # Qué campos se pueden usar para buscar
    search_fields = ('titulo', 'descripcion')

    # Agrega el editor de imágenes 'en línea' dentro del editor de Casa
    inlines = [ImagenCasaInline]
    
    # Acciones personalizadas para el administrador
    actions = ['eliminar_casas_seleccionadas', 'marcar_como_vendidas']
    
    def eliminar_casas_seleccionadas(self, request, queryset):
        """Acción personalizada para eliminar casas seleccionadas"""
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request, 
            f'✅ {count} casa(s) eliminada(s) exitosamente.', 
            messages.SUCCESS
        )
    
    eliminar_casas_seleccionadas.short_description = "🗑️ Eliminar casas seleccionadas"
    
    def marcar_como_vendidas(self, request, queryset):
        """Acción personalizada para marcar casas como vendidas"""
        updated = queryset.update(estatus='vendida')
        self.message_user(
            request, 
            f'💰 {updated} casa(s) marcada(s) como vendidas.', 
            messages.SUCCESS
        )
    
    marcar_como_vendidas.short_description = "💰 Marcar como vendidas"


# Ahora también registramos ImagenCasa por separado para poder administrarla
class ImagenCasaAdmin(admin.ModelAdmin):
    list_display = ('casa', 'orden', 'texto_alternativo')
    list_filter = ('casa',)
    search_fields = ('casa__titulo', 'texto_alternativo')
    
    # Acciones personalizadas para imágenes
    actions = ['eliminar_imagenes_seleccionadas']
    
    def eliminar_imagenes_seleccionadas(self, request, queryset):
        """Acción personalizada para eliminar imágenes seleccionadas"""
        count = queryset.count()
        queryset.delete()
        self.message_user(
            request, 
            f'✅ {count} imagen(es) eliminada(s) exitosamente.', 
            messages.SUCCESS
        )
    
    eliminar_imagenes_seleccionadas.short_description = "🗑️ Eliminar imágenes seleccionadas"


# --- Registramos los modelos en el admin ---
admin.site.register(Casa, CasaAdmin)
admin.site.register(ImagenCasa, ImagenCasaAdmin)