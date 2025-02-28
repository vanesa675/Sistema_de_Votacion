from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import pandas as pd
import io
import re
from .models import Estudiante, Grado, Candidato, Mesa
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image
from io import BytesIO
import os

# Ruta del logo (debe estar en la carpeta estática del proyecto)
LOGO_PATH = os.path.join(os.path.dirname(__file__), "static", "logo.jpg")


# Función para verificar si el usuario es administrador
def es_admin(user):
    return user.is_staff  # Solo los administradores pueden acceder


def extraer_numero(grado):
    """ Extrae el número de un grado (como 1A, 2B, 10, 11) y lo ordena correctamente. """
    match = re.match(r'(\d+)', grado.nombre)
    if match:
        numero = int(match.group(1))
        if numero in [10, 11]:
            numero += 100  
        return (numero, grado.nombre)
    return (float('inf'), grado.nombre)  

def guardar_voto(request):
    """ Guarda el voto de un estudiante y muestra un mensaje de éxito o error. """
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        grado_id = request.POST.get("grado")
        candidato_id = request.POST.get("candidato")
        mesa_id = request.POST.get("mesa")

        if nombre and grado_id and candidato_id and mesa_id:
            try:
                grado = Grado.objects.get(id=grado_id)
                candidato = Candidato.objects.get(id=candidato_id)
                mesa = Mesa.objects.get(id=mesa_id)

                # Verificar si el estudiante ya votó en la mesa
                if Estudiante.objects.filter(nombre=nombre, grado=grado, mesa=mesa).exists():
                    messages.error(request, "⚠️ Este estudiante ya ha votado en esta mesa.")
                else:
                    estudiante = Estudiante(nombre=nombre, grado=grado, candidato=candidato, mesa=mesa)
                    estudiante.save()
                    messages.success(request, "✅ ¡Votación exitosa! Tu voto ha sido registrado.")
                    return redirect('index')  # ✅ Redirige a la vista correcta

            except (Grado.DoesNotExist, Candidato.DoesNotExist, Mesa.DoesNotExist):
                messages.error(request, "⚠️ Hubo un problema con los datos seleccionados.")

    # Obtener grados y mesas
    grados = sorted(Grado.objects.all(), key=extraer_numero)
    mesas = Mesa.objects.all()
    return render(request, "index.html", {"grados": grados, "mesas": mesas})

def generar_pdf(response, grados, titulo):
    """Genera un PDF con estudiantes organizados por grado con mejor diseño."""
    pdf = canvas.Canvas(response, pagesize=letter)
    width, height = letter
    y = height - 50  # Margen superior

    # Encabezado con Logo
    try:
        logo = ImageReader(LOGO_PATH)
        pdf.drawImage(logo, 40, y - 50, width=80, height=80, mask='auto')
    except Exception:
        pass  # Si no se encuentra el logo, continuar sin él

    # Título del Reporte
    pdf.setFont("Helvetica-Bold", 16)
    pdf.setFillColor(colors.darkblue)
    pdf.drawString(150, y, "Reporte de Votaciones")

    # Subtítulo
    pdf.setFont("Helvetica", 12)
    pdf.setFillColor(colors.black)
    pdf.drawString(150, y - 20, titulo)

    # Línea separadora
    pdf.setStrokeColor(colors.black)
    pdf.setLineWidth(1)
    pdf.line(40, y - 30, width - 40, y - 30)

    y -= 60  # Espaciado

    for grado in grados:
        estudiantes = Estudiante.objects.filter(grado=grado).select_related('candidato').order_by('nombre')
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(colors.darkblue)
        pdf.drawString(100, y, f"🔹 Grado: {grado.nombre}")
        y -= 20

        if estudiantes.exists():
            pdf.setFont("Helvetica", 10)
            pdf.setFillColor(colors.black)

            # Crear tabla de estudiantes
            data = [["Estudiante", "Candidato"]]
            for estudiante in estudiantes:
                data.append([estudiante.nombre, estudiante.candidato.nombre])

            # Estilizar tabla
            table = Table(data, colWidths=[250, 200])
            style = TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ])
            table.setStyle(style)

            # Dibujar la tabla
            table.wrapOn(pdf, 100, y)
            table.drawOn(pdf, 100, y - (len(data) * 20))
            y -= (len(data) * 20 + 20)

            if y < 100:  # Salto de página si es necesario
                pdf.showPage()
                y = height - 50
        else:
            pdf.setFillColor(colors.red)
            pdf.drawString(100, y, "⚠ No hay estudiantes en este grado.")
            y -= 30

        y -= 20  # Espaciado entre grados

    # Pie de página con numeración
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.grey)
    pdf.drawString(40, 30, "Sistema de Votación - 2025")
    pdf.drawString(width - 100, 30, f"Página {pdf.getPageNumber()}")

    pdf.showPage()
    pdf.save()


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