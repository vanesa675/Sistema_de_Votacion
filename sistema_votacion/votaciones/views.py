from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import pandas as pd
import io
import re
from .models import Estudiante, Grado, Candidato, Mesa

# Función para verificar si el usuario es administrador
def es_admin(user):
    return user.is_staff  # Solo los administradores pueden acceder


def extraer_numero(grado):
    """ Extrae el número de un grado (como 1A, 2B, 10, 11) y lo ordena correctamente. """
    match = re.match(r'(\d+)', grado.nombre)  # Extrae solo los números iniciales del nombre del grado
    if match:
        numero = int(match.group(1))  # Convierte el número a entero
        if numero in [10, 11]:  # Fuerza a que 10 y 11 vayan al final
            numero += 100  
        return (numero, grado.nombre)  # Ordena primero por número y luego por el texto completo
    return (float('inf'), grado.nombre)  # Si no hay número, envía el grado al final


def guardar_voto(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        grado_id = request.POST.get("grado")
        candidato_id = request.POST.get("candidato")
        mesa_id = request.POST.get("mesa")  # 🔹 Obtener la mesa desde el formulario

        if nombre and grado_id and candidato_id and mesa_id:
            try:
                grado = Grado.objects.get(id=grado_id)
                candidato = Candidato.objects.get(id=candidato_id)
                mesa = Mesa.objects.get(id=mesa_id)  # 🔹 Validar la mesa

                # Verifica si el estudiante ya votó en esa mesa
                if Estudiante.objects.filter(nombre=nombre, grado=grado, mesa=mesa).exists():
                    messages.error(request, "⚠️ Este estudiante ya ha votado en esta mesa.")
                else:
                    estudiante = Estudiante(nombre=nombre, grado=grado, candidato=candidato, mesa=mesa)
                    estudiante.save()
                    messages.success(request, "✅ ¡Voto registrado correctamente!")

            except Grado.DoesNotExist:
                messages.error(request, "⚠️ Grado no encontrado.")
            except Candidato.DoesNotExist:
                messages.error(request, "⚠️ Candidato no encontrado.")
            except Mesa.DoesNotExist:
                messages.error(request, "⚠️ Mesa no encontrada.")

    grados = sorted(Grado.objects.all(), key=extraer_numero)
    mesas = Mesa.objects.all()  # 🔹 Obtener todas las mesas disponibles
    return render(request, "index.html", {"grados": grados, "mesas": mesas})


@login_required
@user_passes_test(es_admin)
def descargar_pdf(request, grado=None):
    """ Genera un PDF con los estudiantes por grado o de todos los grados en orden correcto. """
    response = HttpResponse(content_type='application/pdf')

    if grado:
        try:
            grados = [Grado.objects.get(id=grado)]
            filename = f"reporte_grado_{grados[0].nombre}.pdf"
        except Grado.DoesNotExist:
            return HttpResponse("⚠️ Grado no encontrado.", status=404)
    else:
        grados = sorted(Grado.objects.all(), key=extraer_numero)  # Ordena correctamente los grados
        filename = "reporte_todos_los_grados.pdf"

    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    pdf = canvas.Canvas(response, pagesize=letter)
    y = 800

    pdf.drawString(100, y, "📄 Reporte de Votaciones")
    y -= 20

    for grado in grados:
        estudiantes = Estudiante.objects.filter(grado=grado).select_related('candidato').order_by('nombre')
        pdf.drawString(100, y, f"🔹 Grado: {grado.nombre}")
        y -= 20

        if estudiantes.exists():
            for estudiante in estudiantes:
                pdf.drawString(100, y, f"{estudiante.nombre} - {estudiante.candidato.nombre}")
                y -= 20
                if y < 50:  # Salto de página si es necesario
                    pdf.showPage()
                    y = 800
        else:
            pdf.drawString(100, y, "No hay estudiantes en este grado.")
            y -= 20

        y -= 10  # Espaciado entre grados

    pdf.showPage()
    pdf.save()
    return response


@login_required
@user_passes_test(es_admin)
def descargar_excel(request, grado=None):
    """ Genera un Excel con los estudiantes por grado o de todos los grados en orden correcto. """
    if grado:
        try:
            grados = [Grado.objects.get(id=grado)]
            filename = f"reporte_grado_{grados[0].nombre}.xlsx"
        except Grado.DoesNotExist:
            return HttpResponse("⚠️ Grado no encontrado.", status=404)
    else:
        grados = sorted(Grado.objects.all(), key=extraer_numero)  # Ordena correctamente los grados
        filename = "reporte_todos_los_grados.xlsx"

    if not grados:
        return HttpResponse("⚠️ No hay grados registrados.", status=404)

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    for grado in grados:
        estudiantes = Estudiante.objects.filter(grado=grado).select_related('candidato').values(
            'nombre', 'candidato__nombre'
        ).order_by('nombre')

        if estudiantes:
            df = pd.DataFrame(estudiantes)
            df.rename(columns={'nombre': 'Nombre', 'candidato__nombre': 'Candidato'}, inplace=True)
        else:
            df = pd.DataFrame(columns=['Nombre', 'Candidato'])  # Crear hoja vacía si no hay estudiantes

        df.to_excel(writer, sheet_name=f"Grado {grado.nombre}", index=False)

    writer.close()
    output.seek(0)

    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
@user_passes_test(es_admin)
def descargar_todos_pdf(request):
    """Genera un PDF con los estudiantes de todos los grados organizados en orden ascendente."""
    grados = sorted(Grado.objects.all(), key=extraer_numero)  # Ordena correctamente los grados


    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_todos_los_grados.pdf"'

    pdf = canvas.Canvas(response, pagesize=letter)
    y = 800

    pdf.drawString(100, y, "📄 Reporte de Votaciones - Todos los Grados (Ordenados)")
    y -= 20

    for grado in grados:
        estudiantes = grado.estudiante_set.select_related('candidato').order_by('nombre')
        pdf.drawString(100, y, f"🔹 Grado: {grado.nombre}")
        y -= 20

        if estudiantes.exists():
            for estudiante in estudiantes:
                pdf.drawString(100, y, f"{estudiante.nombre} - {estudiante.candidato.nombre}")
                y -= 20
                if y < 50:  # Salto de página si es necesario
                    pdf.showPage()
                    y = 800
        else:
            pdf.drawString(100, y, "No hay estudiantes en este grado.")
            y -= 20

        y -= 10  # Espaciado entre grados

    pdf.showPage()
    pdf.save()
    return response

@login_required
@user_passes_test(es_admin)
def descargar_todos_excel(request):
    """Genera un Excel con los estudiantes de todos los grados organizados por hoja en orden ascendente."""
    grados = sorted(Grado.objects.all(), key=extraer_numero)  # Ordena correctamente los grados


    if not grados:
        return HttpResponse("⚠️ No hay grados registrados.", status=404)

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    for grado in grados:
        estudiantes = grado.estudiante_set.select_related('candidato').values('nombre', 'candidato__nombre').order_by('nombre')

        if estudiantes:
            df = pd.DataFrame(estudiantes)
            df.rename(columns={'nombre': 'Nombre', 'candidato__nombre': 'Candidato'}, inplace=True)
        else:
            df = pd.DataFrame(columns=['Nombre', 'Candidato'])  # Crear hoja vacía si no hay estudiantes

        df.to_excel(writer, sheet_name=f"Grado {grado.nombre}", index=False)

    writer.close()
    output.seek(0)

    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_todos_los_grados.xlsx"'
    return response