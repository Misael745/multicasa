from django.urls import path
from . import views  # Importamos las vistas (que crearemos a continuación)

urlpatterns = [
    # path(ruta_url, vista_a_llamar, nombre_para_referencia)
    path('', views.homepage, name='homepage'),

    # Nueva ruta que acepta un número entero (int) como id_casa
    path('casa/<int:id_casa>/', views.detalle_casa, name='detalle_casa'),

    path('casa/<int:id_casa>/pdf/', views.generar_pdf_casa, name='generar_pdf_casa'),

    # --- Ruta Privada/Admin ---
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),

    # --- RUTAS DE API REST (JSON) ---
    path('api/casas/', views.casa_api_list, name='casa_api_list'),
    
    # --- NUEVA RUTA PARA REPORTE DE VENTAS (FUERA DEL ADMIN) ---
    path('reporte-ventas/', views.reporte_ventas_pdf, name='reporte_ventas_pdf'),
]