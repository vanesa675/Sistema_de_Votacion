from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import pandas as pd
import re
import io
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from django.contrib import admin
from django.http import FileResponse
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
import matplotlib.pyplot as plt
from .models import Estudiante, Grado, Candidato, Mesa, Voto
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image
from io import BytesIO
import os
from django.conf import settings

LOGO_PATH = os.path.join(settings.BASE_DIR, "static", "img/logo.png")

# Función para verificar si el usuario es administrador
def es_admin(user):
    return user.is_staff  # Solo los administradores pueden acceder

def extraer_numero(grado):
    """ Extrae el número de un grado y lo ordena correctamente. """
    match = re.match(r'\d+', grado.nombre)
    if match:
        numero = int(match.group(0))
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



# ✅ Función para agregar marca de agua en todas las páginas
def agregar_marca_agua(pdf):
    if os.path.exists(LOGO_PATH):
        pdf.saveState()
        pdf.setFillAlpha(0.2)  # Transparencia (0.0 = completamente transparente, 1.0 = sin transparencia)
        pdf.drawImage(LOGO_PATH, 150, 250, width=300, height=300, mask='auto')  # Posición y tamaño
        pdf.setFillAlpha(1)  # Restaurar opacidad para el contenido normal
        pdf.restoreState()
        
def ordenar_grados(grados):
    orden_deseado = {
        "0°": 0, "1°A": 1, "1°B": 2, "2°A": 3, "2°B": 4, "3°": 5, "4°": 6, "5°": 7,
        "601°": 8, "602°": 9, "701°": 10, "702°": 11, "801°": 12, "802°": 13,
        "901°": 14, "902°": 15, "10°": 16, "11°": 17
    }
    return sorted(grados, key=lambda g: orden_deseado.get(g.nombre, 99))

@login_required
@user_passes_test(es_admin)
def descargar_pdf(request):
    """Genera un PDF con los estudiantes organizados en tablas con mejor diseño."""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_votaciones.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elementos = []
    styles = getSampleStyleSheet()
    heading2_centered_style = ParagraphStyle(name="Heading2Centered", parent=styles['Heading2'], alignment=1)

    # Agregar el logo
    try:
        imagen = Image(LOGO_PATH, width=100, height=100)
        elementos.append(imagen)
    except Exception:
        elementos.append(Paragraph("[Logo no disponible]", styles['Italic']))

    # Agregar título y subtítulo centrados
    elementos.append(Paragraph("Gimnasio Minuto de Dios", styles['Title']))
    elementos.append(Paragraph("Votaciones 2025", heading2_centered_style))
    elementos.append(Spacer(1, 12))

    # Obtener y ordenar los grados correctamente
    grados = ordenar_grados(Grado.objects.all())

    for grado in grados:
        estudiantes = Estudiante.objects.filter(grado=grado).select_related('candidato', 'mesa').order_by('nombre')
        elementos.append(Paragraph(f"🔹 Grado: {grado.nombre}", styles['Heading2']))
        elementos.append(Spacer(1, 10))

        if estudiantes.exists():
            data = [["Estudiante", "Mesa", "Tarjetón"]]  # Encabezados de tabla
            for estudiante in estudiantes:
                data.append([estudiante.nombre, estudiante.mesa.nombre, estudiante.candidato.tarjeton])

            tabla = Table(data, colWidths=[200, 100, 100])
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ]))

            elementos.append(tabla)
        else:
            elementos.append(Paragraph("⚠ No hay estudiantes en este grado.", styles['Italic']))

        elementos.append(Spacer(1, 20))

    doc.build(elementos)
    return response

@login_required
@user_passes_test(es_admin)
def descargar_excel(request, grado=None):
    """Genera un Excel con los estudiantes organizados por grado, mostrando Nombre, Mesa y Tarjetón."""
    if grado:
        try:
            grados = [Grado.objects.get(id=grado)]
            filename = f"reporte_grado_{grados[0].nombre}.xlsx"
        except Grado.DoesNotExist:
            return HttpResponse("⚠️ Grado no encontrado.", status=404)
    else:
        grados = sorted(Grado.objects.all(), key=extraer_numero)
        filename = "reporte_todos_los_grados.xlsx"

    if not grados:
        return HttpResponse("⚠️ No hay grados registrados.", status=404)

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    for grado in grados:
        estudiantes = Estudiante.objects.filter(grado=grado).select_related('candidato', 'mesa').values(
            'nombre', 'mesa__nombre', 'candidato__tarjeton'
        ).order_by('nombre')

        if estudiantes:
            df = pd.DataFrame(estudiantes)
            df.rename(columns={'nombre': 'Nombre', 'mesa__nombre': 'Mesa', 'candidato__tarjeton': 'Tarjetón'}, inplace=True)
        else:
            df = pd.DataFrame(columns=['Nombre', 'Mesa', 'Tarjetón'])  # Crear hoja vacía si no hay estudiantes

        df.to_excel(writer, sheet_name=f"Grado {grado.nombre}", index=False)

        # ✅ Mejorar formato del Excel
        workbook = writer.book
        worksheet = writer.sheets[f"Grado {grado.nombre}"]
        header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': 'blue', 'align': 'center'})

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)  # Ajustar ancho de columna

    writer.close()
    output.seek(0)

    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@user_passes_test(es_admin)
def descargar_todos_pdf(request):
    """Genera un PDF con los estudiantes de todos los grados organizados correctamente."""
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_todos_los_grados.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elementos = []
    styles = getSampleStyleSheet()
    heading2_centered_style = ParagraphStyle(name="Heading2Centered", parent=styles['Heading2'], alignment=1)

    # ✅ Agregar el logo en la portada
    try:
        imagen = Image(LOGO_PATH, width=100, height=100)
        elementos.append(imagen)
    except Exception:
        elementos.append(Paragraph("[Logo no disponible]", styles['Italic']))

    # ✅ Agregar título y subtítulo
    elementos.append(Paragraph("Gimnasio Minuto de Dios", styles['Title']))
    elementos.append(Paragraph("Votaciones 2025", heading2_centered_style))
    elementos.append(Spacer(1, 12))

    # ✅ Obtener y ordenar los grados correctamente
    grados = ordenar_grados(Grado.objects.all())

    for grado in grados:
        estudiantes = Estudiante.objects.filter(grado=grado).select_related('candidato', 'mesa').order_by('nombre')
        elementos.append(Paragraph(f"🔹 Grado: {grado.nombre}", styles['Heading2']))
        elementos.append(Spacer(1, 10))

        if estudiantes.exists():
            data = [["Estudiante", "Mesa", "Tarjetón"]]  # Encabezado de la tabla
            for estudiante in estudiantes:
                data.append([estudiante.nombre, estudiante.mesa.nombre, estudiante.candidato.tarjeton])

            # ✅ Aplicar diseño a la tabla
            tabla = Table(data, colWidths=[200, 100, 100])
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), "Helvetica-Bold"),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
            ]))
            elementos.append(tabla)
        else:
            elementos.append(Paragraph("⚠ No hay estudiantes en este grado.", styles['Italic']))
        
        elementos.append(Spacer(1, 20))

    # ✅ Aplicar la marca de agua en todas las páginas
    def agregar_marca_agua_en_pagina(canvas, doc):
        agregar_marca_agua(canvas)  # Agrega la marca de agua en cada página

    doc.build(elementos, onFirstPage=agregar_marca_agua_en_pagina, onLaterPages=agregar_marca_agua_en_pagina)

    return response


@login_required
@user_passes_test(es_admin)
def descargar_todos_excel(request):
    """Genera un Excel con los estudiantes de todos los grados organizados por hoja en el orden personalizado."""
    
    # ✅ Orden personalizado de grados
    def ordenar_grados(grados):
        orden_deseado = {
            "0°": 0, "1°A": 1, "1°B": 2, "2°A": 3, "2°B": 4, "3°": 5, "4°": 6, "5°": 7,
            "601°": 8, "602°": 9, "701°": 10, "702°": 11, "801°": 12, "802°": 13,
            "901°": 14, "902°": 15, "10°": 16, "11°": 17
        }
        return sorted(grados, key=lambda g: orden_deseado.get(g.nombre, 99))

    grados = ordenar_grados(Grado.objects.all())

    if not grados:
        return HttpResponse("⚠️ No hay grados registrados.", status=404)

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')

    for grado in grados:
        estudiantes = grado.estudiante_set.select_related('candidato', 'mesa').values(
            'nombre', 'mesa__nombre', 'candidato__tarjeton'
        ).order_by('nombre')

        if estudiantes:
            df = pd.DataFrame(estudiantes)
            df.rename(columns={'nombre': 'Nombre', 'mesa__nombre': 'Mesa', 'candidato__tarjeton': 'Tarjetón'}, inplace=True)
        else:
            df = pd.DataFrame(columns=['Nombre', 'Mesa', 'Tarjetón'])  # Hoja vacía si no hay estudiantes

        df.to_excel(writer, sheet_name=f"Grado {grado.nombre}", index=False)

        # ✅ Aplicar formato al Excel
        workbook = writer.book
        worksheet = writer.sheets[f"Grado {grado.nombre}"]
        header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': 'blue', 'align': 'center'})

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)  # Ajustar ancho de columna automáticamente

    writer.close()
    output.seek(0)

    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_todos_los_grados.xlsx"'
    return response

