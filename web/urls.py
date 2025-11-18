from django.urls import path
from . import views

urlpatterns = [
    # --- RUTAS PARA TEMPLATES (frontend) ---
    path('', views.homepage, name='homepage'),
    path('casa/<int:id_casa>/', views.detalle_casa, name='detalle_casa'),
    path('casa/<int:id_casa>/pdf/', views.generar_pdf_casa, name='generar_pdf_casa'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('contacto/', views.contact_view, name='contacto'),

    # --- RUTAS DE API REST (JSON) - CRUD COMPLETO ---
    # CRUD básico
    path('api/casas/', views.casa_api_list, name='casa_api_list'),
    path('api/casas/<int:id_casa>/', views.casa_api_detail, name='casa_api_detail'),
    
    # Búsqueda y filtros
    path('api/casas/buscar/', views.casa_api_search, name='casa_api_search'),
    path('api/casas/filtrar/', views.casa_api_filter, name='casa_api_filter'),
    path('api/casas/activas/', views.casa_api_activas, name='casa_api_activas'),
]