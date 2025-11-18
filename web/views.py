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
from rest_framework import status
from .serializers import CasaListSerializer, CasaDetailSerializer, CasaCreateSerializer


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

        # Redirigimos a 'homepage' para evitar re-envíos (Patrón Post-Redirect-Get)
        return redirect('homepage')

    # --- 2. LÓGICA DE BÚSQUEDA (SI ES GET) ---
    # (Esta parte se mantiene igual que antes)
    casas = Casa.objects.filter(estatus='en venta').order_by('-fecha_publicacion')

    query = request.GET.get('q')
    if query:
        casas = casas.filter(titulo__icontains=query) | casas.filter(descripcion__icontains=query)

    habitaciones = request.GET.get('habitaciones')
    if habitaciones and habitaciones != "":
        casas = casas.filter(habitaciones=habitaciones)

    min_precio = request.GET.get('min_precio')
    if min_precio:
        casas = casas.filter(precio__gte=min_precio)

    max_precio = request.GET.get('max_precio')
    if max_precio:
        casas = casas.filter(precio__lte=max_precio)

    # --- 3. CONTEXTO FINAL ---
    contexto = {
        'lista_casas': casas,
        'titulo_pagina': 'Bienvenido a Multicasa',
        'valores_filtro': request.GET
    }

    return render(request, 'publico/index.html', contexto)


# --- Nueva Vista ---
def detalle_casa(request, id_casa):
    """
    Muestra el detalle completo de una casa específica.
    """
    # Busca la casa por ID o devuelve error 404 si no existe
    casa = get_object_or_404(Casa, pk=id_casa)

    contexto = {
        'casa': casa,
        'titulo_pagina': casa.titulo
    }
    return render(request, 'publico/detalle_casa.html', contexto)


def generar_pdf_casa(request, id_casa):
    """
    Genera la ficha técnica de una casa en formato PDF.
    """
    # 1. Obtenemos la casa
    casa = get_object_or_404(Casa, pk=id_casa)

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
        content = f"attachment; filename='{filename}'"
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


# --- VISTAS DE API REST - CRUD COMPLETO ---

@api_view(['GET', 'POST'])
def casa_api_list(request):
    """
    GET: Listar todas las casas (resumen)
    POST: Crear nueva casa
    """
    if request.method == 'GET':
        casas = Casa.objects.all()
        serializer = CasaListSerializer(casas, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = CasaCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
def casa_api_detail(request, id_casa):
    """
    GET: Obtener detalles completos de una casa
    PUT: Actualizar una casa
    DELETE: Eliminar una casa
    """
    try:
        casa = Casa.objects.get(id_casa=id_casa)
    except Casa.DoesNotExist:
        return Response(
            {'error': 'Casa no encontrada'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = CasaDetailSerializer(casa)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = CasaCreateSerializer(casa, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        casa.delete()
        return Response(
            {'message': 'Casa eliminada correctamente'}, 
            status=status.HTTP_204_NO_CONTENT
        )

@api_view(['GET'])
def casa_api_search(request):
    """
    Buscar casas por título, descripción o dirección
    """
    query = request.GET.get('q', '')
    if query:
        casas = Casa.objects.filter(
            Q(titulo__icontains=query) |
            Q(descripcion__icontains=query) |
            Q(direccion__icontains=query)
        )
    else:
        casas = Casa.objects.all()
    
    serializer = CasaListSerializer(casas, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def casa_api_filter(request):
    """
    Filtrar casas por múltiples criterios
    """
    filters = {}
    
    # Aplicar filtros solo si se proporcionan
    if 'estatus' in request.GET:
        filters['estatus'] = request.GET['estatus']
    if 'min_precio' in request.GET:
        filters['precio__gte'] = request.GET['min_precio']
    if 'max_precio' in request.GET:
        filters['precio__lte'] = request.GET['max_precio']
    if 'habitaciones' in request.GET:
        filters['habitaciones'] = request.GET['habitaciones']
    if 'banos' in request.GET:
        filters['banos'] = request.GET['banos']
    
    casas = Casa.objects.filter(**filters)
    serializer = CasaListSerializer(casas, many=True)
    return Response(serializer.data)

@api_view(['GET'])
def casa_api_activas(request):
    """
    Obtener solo casas con estatus 'en venta'
    """
    casas = Casa.objects.filter(estatus='en venta')
    serializer = CasaListSerializer(casas, many=True)
    return Response(serializer.data)