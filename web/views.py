from django.shortcuts import render, get_object_or_404, redirect
from .models import Casa  # Importamos el modelo Casa
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import io
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.core.mail import send_mail
from django.contrib import messages
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import CasaListSerializer
from django.utils import timezone  # NUEVO IMPORT


def render_to_pdf(template_src, context_dict={}):
    """
    Función para renderizar un template HTML a un PDF.
    """
    template = get_template(template_src)
    html = template.render(context_dict)

    # Creamos el PDF en memoria
    result = io.BytesIO()

    # Convertimos el HTML a PDF
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)

    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None


def homepage(request):
    """
    Vista para la página de inicio.
    Maneja la búsqueda (GET) y el formulario de contacto (POST).
    """

    # --- 1. LÓGICA DE CONTACTO (SI ES POST) ---
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email_origen = request.POST.get('email')
        mensaje = request.POST.get('mensaje')

        asunto = f'Nuevo mensaje de Contacto de: {nombre}'
        cuerpo_mensaje = f"Nombre: {nombre}\nEmail: {email_origen}\n\nMensaje:\n{mensaje}"
        email_destino = 'admin@multicasa.com'

        try:
            send_mail(
                asunto,
                cuerpo_mensaje,
                email_origen,
                [email_destino],
                fail_silently=False,
            )
            messages.success(request, '¡Mensaje enviado con éxito! Te responderemos pronto.')
        except Exception as e:
            messages.error(request, f'Hubo un error al enviar el mensaje: {e}')

        return redirect('homepage')

    # --- 2. LÓGICA DE BÚSQUEDA (SI ES GET) ---
    # CAMBIO: Agregar prefetch_related para optimizar consultas de imágenes
    casas = Casa.objects.filter(estatus='en venta').order_by('-fecha_publicacion').prefetch_related('imagenes')

    # NUEVOS FILTROS - Reemplazando los anteriores
    municipio = request.GET.get('municipio')
    if municipio:
        casas = casas.filter(municipio__icontains=municipio)

    estado = request.GET.get('estado')
    if estado:
        casas = casas.filter(estado__icontains=estado)

    # NUEVO FILTRO: Código Postal
    codigo_postal = request.GET.get('codigo_postal')
    if codigo_postal:
        casas = casas.filter(codigo_postal__icontains=codigo_postal)

    habitaciones = request.GET.get('habitaciones')
    if habitaciones and habitaciones != "":
        casas = casas.filter(habitaciones=habitaciones)

    banos = request.GET.get('banos')
    if banos and banos != "":
        casas = casas.filter(banos=banos)

    min_precio = request.GET.get('min_precio')
    if min_precio:
        casas = casas.filter(precio__gte=min_precio)

    max_precio = request.GET.get('max_precio')
    if max_precio:
        casas = casas.filter(precio__lte=max_precio)

    # --- 3. ÚLTIMOS MOVIMIENTOS ---
    # Obtener las últimas 5 casas (vendidas o en venta) ordenadas por fecha de modificación
    ultimos_movimientos = Casa.objects.all().order_by('-fecha_publicacion')[:5]

    # --- 4. CONTEXTO FINAL ---
    contexto = {
        'lista_casas': casas,
        'ultimos_movimientos': ultimos_movimientos,  # NUEVO: agregar al contexto
        'titulo_pagina': 'Bienvenido a Multicasa',
        'valores_filtro': request.GET
    }

    return render(request, 'publico/index.html', contexto)


# --- Nueva Vista ---
def detalle_casa(request, id_casa):
    """
    Muestra el detalle completo de una casa específica.
    """
    # CAMBIO: Agregar prefetch_related para cargar todas las imágenes
    casa = get_object_or_404(Casa.objects.prefetch_related('imagenes'), pk=id_casa)

    contexto = {
        'casa': casa,
        'titulo_pagina': casa.titulo
    }
    return render(request, 'publico/detalle_casa.html', contexto)


def generar_pdf_casa(request, id_casa):
    """
    Genera la ficha técnica de una casa en formato PDF.
    """
    # 1. Obtenemos la casa con sus imágenes
    casa = get_object_or_404(Casa.objects.prefetch_related('imagenes'), pk=id_casa)

    # 2. Definimos el contexto (datos que irán al HTML)
    contexto = {
        'casa': casa,
    }

    # 3. Usamos nuestra función auxiliar para crear el PDF
    pdf = render_to_pdf('publico/ficha_tecnica.html', contexto)

    if pdf:
        # 4. Preparamos la respuesta HTTP para que sea una descarga
        response = HttpResponse(pdf, content_type='application/pdf')

        # El nombre del archivo que se descargará
        filename = f"Ficha_Tecnica_Casa_{id_casa}.pdf"

        # Le decimos al navegador que es una descarga
        content = f"attachment; filename={filename}"
        response['Content-Disposition'] = content
        return response

    # Si falla, regresamos un error
    return HttpResponse("Error al generar el PDF", status=400)


@login_required(login_url='/admin/login/')  # Redirige al login del admin si no está logueado
def admin_dashboard(request):
    """
    Vista para el dashboard privado de administración con gráficos.
    """
    # --- Gráfico 1: Casas por Estatus (En Venta vs. Vendidas) ---
    # Contamos las casas agrupadas por 'estatus'
    estatus_data = Casa.objects.values('estatus').annotate(
        cantidad=Count('id_casa')
    ).order_by('estatus')

    # Preparamos los datos para Chart.js
    estatus_labels = [item['estatus'].title() for item in estatus_data]
    estatus_valores = [item['cantidad'] for item in estatus_data]

    # --- Gráfico 2: Casas por Rango de Costo ---
    # Definimos nuestros rangos de precio
    rangos_precio = {
        'Menos de $1M': Q(precio__lt=1000000),
        '$1M - $2M': Q(precio__range=(1000000, 2000000)),
        '$2M - $3M': Q(precio__range=(2000001, 3000000)),
        'Más de $3M': Q(precio__gt=3000000),
    }

    # Creamos un diccionario para guardar los conteos
    costo_data = {}
    for nombre, rango_q in rangos_precio.items():
        # Contamos cuántas casas caen en cada rango
        costo_data[nombre] = Casa.objects.filter(rango_q).count()

    # Preparamos los datos para Chart.js
    costo_labels = list(costo_data.keys())
    costo_valores = list(costo_data.values())

    # --- Preparamos el contexto final ---
    contexto = {
        'titulo_pagina': 'Dashboard de Administración',

        # Datos para el gráfico de estatus
        'estatus_labels': estatus_labels,
        'estatus_valores': estatus_valores,

        # Datos para el gráfico de costos
        'costo_labels': costo_labels,
        'costo_valores': costo_valores,
    }

    # Renderizamos la nueva plantilla
    return render(request, 'admin/dashboard.html', contexto)


def contact_view(request):
    """
    Vista para el formulario de contacto.
    """
    if request.method == 'POST':
        # 1. Si el formulario fue enviado (POST), procesamos los datos
        nombre = request.POST.get('nombre')
        email_origen = request.POST.get('email')
        mensaje = request.POST.get('mensaje')

        # 2. Preparamos el email
        asunto = f'Nuevo mensaje de Contacto de: {nombre}'
        cuerpo_mensaje = f"Nombre: {nombre}\n"
        cuerpo_mensaje += f"Email: {email_origen}\n\n"
        cuerpo_mensaje += f"Mensaje:\n{mensaje}"

        email_destino = 'admin@multicasa.com'  # Email al que "llegaría"

        try:
            # 3. Enviamos el email (que se imprimirá en la consola)
            send_mail(
                asunto,
                cuerpo_mensaje,
                email_origen,  # From
                [email_destino],  # To
                fail_silently=False,
            )
            # 4. Mostramos un mensaje de éxito
            messages.success(request, '¡Mensaje enviado con éxito! Te responderemos pronto.')
        except Exception as e:
            messages.error(request, f'Hubo un error al enviar el mensaje: {e}')

        # Redirigimos a la misma página para evitar re-envíos
        return redirect('contacto')

    # 5. Si es GET (o la primera vez), solo mostramos la página
    contexto = {
        'titulo_pagina': 'Contacto'
    }
    return render(request, 'publico/contacto.html', contexto)


# --- VISTA DE API REST ---

@api_view(['GET'])
def casa_api_list(request):
    """
    API REST para listar todas las casas en venta.
    """
    try:
        # 1. Obtenemos las casas con sus imágenes
        casas = Casa.objects.filter(estatus='en venta').prefetch_related('imagenes')

        # 2. Las pasamos por el serializador
        serializer = CasaListSerializer(casas, many=True)

        # 3. Devolvemos la respuesta JSON
        return Response(serializer.data)

    except Exception as e:
        return Response({'error': str(e)}, status=500)


# --- NUEVA VISTA PARA REPORTE DE VENTAS ---
@login_required(login_url='/admin/login/')
def reporte_ventas_pdf(request):
    """
    Genera un PDF con el reporte de ventas de todas las casas.
    """
    # Obtener todas las casas
    casas = Casa.objects.all().order_by('estatus', '-fecha_publicacion')
    
    # Calcular totales
    casas_en_venta = casas.filter(estatus='en venta')
    casas_vendidas = casas.filter(estatus='vendida')
    
    total_en_venta = sum(casa.precio for casa in casas_en_venta if casa.precio)
    total_vendidas = sum(casa.precio for casa in casas_vendidas if casa.precio)
    total_general = total_en_venta + total_vendidas
    
    # Contexto para el template
    contexto = {
        'casas': casas,
        'casas_en_venta': casas_en_venta,
        'casas_vendidas': casas_vendidas,
        'total_en_venta': total_en_venta,
        'total_vendidas': total_vendidas,
        'total_general': total_general,
        'fecha_reporte': timezone.now(),
    }
    
    # Generar PDF
    pdf = render_to_pdf('admin/reporte_ventas.html', contexto)
    
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"Reporte_Ventas_Multicasa_{timezone.now().strftime('%Y-%m-%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    
    return HttpResponse("Error al generar el PDF", status=400)