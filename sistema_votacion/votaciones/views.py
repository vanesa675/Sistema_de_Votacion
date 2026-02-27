import matplotlib
matplotlib.use('Agg')  # 👈 Evita que intente abrir una GUI
import matplotlib.pyplot as plt
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
from votaciones.models import Estudiante, Grado  # Asegúrate de que sea el nombre correcto de tu app

LOGO_PATH = os.path.join(settings.BASE_DIR, "static","img","logo.png")

# Función para verificar si el usuario es administrador
def es_admin(user):
    return user.is_staff  # Solo los administradores pueden acceder

def index(request):
    candidatos = Candidato.objects.all()
    return render(request, 'index.html', {'candidatos': candidatos})

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
                    estudiante = Estudiante(
                        nombre=nombre,
                        grado=grado,
                        candidato=candidato,
                        mesa=mesa
                    )
                    estudiante.save()
                    messages.success(request, "✅ ¡Votación exitosa! Tu voto ha sido registrado.")
                    return redirect('index')

            except (Grado.DoesNotExist, Candidato.DoesNotExist, Mesa.DoesNotExist):
                messages.error(request, "⚠️ Hubo un problema con los datos seleccionados.")

    # 🔥 ESTO ES LO QUE FALTABA
    grados = sorted(Grado.objects.all(), key=extraer_numero)
    mesas = Mesa.objects.all()
    candidatos = Candidato.objects.all().order_by("tarjeton")

    return render(request, "votaciones/index.html", {
        "grados": grados,
        "mesas": mesas,
        "candidatos": candidatos
    })

    # Obtener grados y mesas
    grados = sorted(Grado.objects.all(), key=extraer_numero)
    mesas = Mesa.objects.all()
    return render(request, "votaciones/index.html", {"grados": grados, "mesas": mesas})



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
@user_passes_test(lambda u: u.is_staff)  # Solo administradores
def descargar_pdf(request, grado):
    """Genera un PDF con gráficos y datos de votaciones solo para el grado seleccionado."""
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_votaciones_grado_{grado}.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter)
    elementos = []
    styles = getSampleStyleSheet()
    centered_style = ParagraphStyle(name="Centered", parent=styles['Heading2'], alignment=1)

    # 📌 Agregar el logo
    try:
        logo = Image(LOGO_PATH, width=100, height=100)
        elementos.append(logo)
    except Exception:
        elementos.append(Paragraph("[Logo no disponible]", styles['Italic']))

    # 📌 Agregar título y subtítulo
    elementos.append(Paragraph("Gimnasio Minuto de Dios", styles['Title']))
    elementos.append(Paragraph(f"Votaciones 2025 - Grado {grado}", centered_style))
    elementos.append(Spacer(1, 12))

    # 📌 Obtener resultados de votaciones del grado específico
    votos = obtener_resultados_votaciones(grado)

    if votos:
        # 🥧 Agregar gráfico de torta
        buffer_torta = generar_grafico_torta(votos)
        img_torta = Image(buffer_torta, width=400, height=300)
        elementos.append(Paragraph("Distribución de Votos en el Grado", styles['Heading2']))
        elementos.append(img_torta)
        elementos.append(Spacer(1, 10))

        # 🏆 Determinar el candidato con más votos en el grado
        candidato_ganador = max(votos, key=votos.get)
        total_votos = votos[candidato_ganador]
        elementos.append(Paragraph(f"🏆 Candidato más votado en este grado: {candidato_ganador} ({total_votos} votos)", styles['Heading2']))
        elementos.append(Spacer(1, 20))
    else:
        elementos.append(Paragraph("⚠ No hay votos registrados para este grado.", styles['Italic']))
        elementos.append(Spacer(1, 20))

    # 📌 Agregar tabla de estudiantes del grado
    try:
        grado_obj = Grado.objects.get(id=grado)
        estudiantes = Estudiante.objects.filter(grado=grado_obj).select_related('candidato', 'mesa').order_by('nombre')

        elementos.append(Paragraph(f"🔹 Grado: {grado_obj.nombre}", styles['Heading2']))
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

    except Grado.DoesNotExist:
        elementos.append(Paragraph("⚠ Error: El grado seleccionado no existe.", styles['Italic']))

    elementos.append(Spacer(1, 20))
    doc.build(elementos)
    return response

# 📌 Función para obtener los votos por candidato en un grado específico
def obtener_resultados_votaciones(grado):
    """Devuelve un diccionario con los votos de cada candidato en el grado seleccionado."""
    votos = {}
    estudiantes = Estudiante.objects.filter(grado=grado)

    for estudiante in estudiantes:
        candidato = estudiante.candidato.nombre
        votos[candidato] = votos.get(candidato, 0) + 1

    return votos

# 🥧 Función para generar el gráfico de torta
def generar_grafico_torta(votos):
    """Genera un gráfico de torta con la distribución de votos."""
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.pie(votos.values(), labels=votos.keys(), autopct='%1.1f%%', colors=['blue', 'red', 'green', 'purple'])
    ax.set_title("Distribución de Votos")

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return buffer

@login_required
@user_passes_test(lambda u: u.is_staff)  # Solo administradores
def descargar_excel(request, grado=None):
    """Genera un Excel con los estudiantes organizados por grado, mostrando Nombre, Mesa, Tarjetón, gráfica de torta y el candidato con más votos."""
    
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

        # 📌 Obtener resultados de votaciones del grado
        votos = obtener_resultados_votaciones(grado)

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

        # 🥧 Agregar gráfico de torta si hay votos
        if votos:
            buffer_torta = generar_grafico_torta(votos)
            imagen_path = f"grafico_grado_{grado.nombre}.png"
            
            with open(imagen_path, "wb") as f:
                f.write(buffer_torta.getvalue())

            worksheet.insert_image("E2", imagen_path, {'x_scale': 0.5, 'y_scale': 0.5})

            # 🏆 Determinar el candidato con más votos
            candidato_ganador = max(votos, key=votos.get)
            total_votos = votos[candidato_ganador]
            worksheet.write(20, 0, f"🏆 Candidato más votado: {candidato_ganador} ({total_votos} votos)")
        else:
            worksheet.write(20, 0, "⚠ No hay votos registrados en este grado.")

    writer.close()
    output.seek(0)

    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

# 📌 Función para obtener los votos de un grado específico
def obtener_resultados_votaciones(grado):
    """Devuelve un diccionario con los votos de cada candidato en un grado específico."""
    votos = {}
    estudiantes = Estudiante.objects.filter(grado=grado)

    for estudiante in estudiantes:
        candidato = estudiante.candidato.nombre
        votos[candidato] = votos.get(candidato, 0) + 1

    return votos

# 🥧 Función para generar el gráfico de torta
def generar_grafico_torta(votos):
    """Genera un gráfico de torta con la distribución de votos en un grado específico."""
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.pie(votos.values(), labels=votos.keys(), autopct='%1.1f%%', colors=['blue', 'red', 'green', 'purple'])
    ax.set_title("Distribución de Votos")

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return buffer


@login_required
@user_passes_test(lambda u: u.is_staff)  # Solo administradores
def descargar_todos_pdf(request):
    """Genera un PDF con los estudiantes de todos los grados y una gráfica de torta al inicio."""
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reporte_todos_los_grados.pdf"'
    doc = SimpleDocTemplate(response, pagesize=letter)
    elementos = []
    styles = getSampleStyleSheet()
    centered_style = ParagraphStyle(name="Centered", parent=styles['Heading2'], alignment=1)

    # 📌 Agregar el logo en la portada
    try:
        imagen = Image(LOGO_PATH, width=100, height=100)
        elementos.append(imagen)
    except Exception:
        elementos.append(Paragraph("[Logo no disponible]", styles['Italic']))

    # 📌 Agregar título y subtítulo
    elementos.append(Paragraph("Gimnasio Minuto de Dios", styles['Title']))
    elementos.append(Paragraph("Votaciones 2025", centered_style))
    elementos.append(Spacer(1, 12))

    # 📌 Obtener los votos de todos los grados
    votos = obtener_resultados_votaciones_todos()

    if votos:
        # 🥧 Agregar gráfico de torta con los votos totales al inicio
        buffer_torta = generar_grafico_torta(votos)
        img_torta = Image(buffer_torta, width=400, height=300)
        elementos.append(Paragraph("Gráfico de Torta - Distribución de Votos en Todos los Grados", styles['Heading2']))
        elementos.append(img_torta)
        elementos.append(Spacer(1, 10))

        # 🏆 Determinar el candidato con más votos
        candidato_ganador = max(votos, key=votos.get)
        total_votos = votos[candidato_ganador]
        elementos.append(Paragraph(f"🏆 Candidato con más votos: {candidato_ganador} ({total_votos} votos)", styles['Heading2']))
        elementos.append(Spacer(1, 20))
    else:
        elementos.append(Paragraph("⚠ No hay votos registrados en ningún grado.", styles['Italic']))
        elementos.append(Spacer(1, 20))

    # 📌 Obtener y ordenar los grados correctamente
    grados = ordenar_grados(Grado.objects.all())

    for grado in grados:
        estudiantes = Estudiante.objects.filter(grado=grado).select_related('candidato', 'mesa').order_by('nombre')
        elementos.append(Paragraph(f"🔹 Grado: {grado.nombre}", styles['Heading2']))
        elementos.append(Spacer(1, 10))

        if estudiantes.exists():
            data = [["Estudiante", "Mesa", "Tarjetón"]]  # Encabezado de la tabla
            for estudiante in estudiantes:
                data.append([estudiante.nombre, estudiante.mesa.nombre, estudiante.candidato.tarjeton])

            # 📌 Aplicar diseño a la tabla
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

# 📌 Función para obtener los votos de todos los grados
def obtener_resultados_votaciones_todos():
    """Devuelve un diccionario con los votos de todos los candidatos en todos los grados."""
    votos = {}
    estudiantes = Estudiante.objects.all()

    for estudiante in estudiantes:
        candidato = estudiante.candidato.nombre
        votos[candidato] = votos.get(candidato, 0) + 1

    return votos

# 🥧 Función para generar el gráfico de torta con los votos de todos los grados
def generar_grafico_torta(votos):
    """Genera un gráfico de torta con la distribución de votos en todos los grados."""
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.pie(votos.values(), labels=votos.keys(), autopct='%1.1f%%', colors=['blue', 'red', 'green', 'purple'])
    ax.set_title("Distribución de Votos en Todos los Grados")

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return buffer


@login_required
@user_passes_test(lambda u: u.is_staff)  # Solo administradores
def descargar_todos_excel(request):
    """Genera un Excel con los estudiantes de todos los grados organizados por hoja en el orden personalizado, incluyendo gráfico de torta y candidato más votado."""

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
    workbook = writer.book

    # 📌 Obtener resultados de votaciones de todos los grados
    votos_todos = obtener_resultados_votaciones_todos()

    if votos_todos:
        # 🥧 Generar gráfico de torta con los votos totales
        buffer_torta = generar_grafico_torta(votos_todos)
        imagen_path = "grafico_todos_los_grados.png"
        
        with open(imagen_path, "wb") as f:
            f.write(buffer_torta.getvalue())

        # 🏆 Determinar el candidato con más votos
        candidato_ganador = max(votos_todos, key=votos_todos.get)
        total_votos = votos_todos[candidato_ganador]

        # 📌 Crear hoja de resumen con el gráfico y el candidato más votado
        worksheet_resumen = workbook.add_worksheet("Resumen General")
        worksheet_resumen.insert_image("B2", imagen_path, {'x_scale': 0.5, 'y_scale': 0.5})
        worksheet_resumen.write(20, 1, f"🏆 Candidato más votado en todos los grados: {candidato_ganador} ({total_votos} votos)")
    else:
        worksheet_resumen = workbook.add_worksheet("Resumen General")
        worksheet_resumen.write(2, 1, "⚠ No hay votos registrados en ningún grado.")

    # 📌 Generar hojas por cada grado
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
        worksheet = writer.sheets[f"Grado {grado.nombre}"]
        header_format = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': 'blue', 'align': 'center'})

        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20)  # Ajustar ancho de columna automáticamente

        # 📌 Obtener resultados de votaciones del grado específico
        votos_grado = obtener_resultados_votaciones(grado)

        if votos_grado:
            # 🥧 Generar gráfico de torta para este grado
            buffer_torta_grado = generar_grafico_torta(votos_grado)
            imagen_path_grado = f"grafico_grado_{grado.nombre}.png"
            
            with open(imagen_path_grado, "wb") as f:
                f.write(buffer_torta_grado.getvalue())

            worksheet.insert_image("E2", imagen_path_grado, {'x_scale': 0.5, 'y_scale': 0.5})

            # 🏆 Determinar el candidato con más votos en este grado
            candidato_ganador_grado = max(votos_grado, key=votos_grado.get)
            total_votos_grado = votos_grado[candidato_ganador_grado]
            worksheet.write(20, 0, f"🏆 Candidato más votado en este grado: {candidato_ganador_grado} ({total_votos_grado} votos)")
        else:
            worksheet.write(20, 0, "⚠ No hay votos registrados en este grado.")

    writer.close()
    output.seek(0)

    response = HttpResponse(output.read(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="reporte_todos_los_grados.xlsx"'
    return response

# 📌 Función para obtener los votos de todos los grados
def obtener_resultados_votaciones_todos():
    """Devuelve un diccionario con los votos de todos los candidatos en todos los grados."""
    votos = {}
    estudiantes = Estudiante.objects.all()

    for estudiante in estudiantes:
        candidato = estudiante.candidato.nombre
        votos[candidato] = votos.get(candidato, 0) + 1

    return votos

# 📌 Función para obtener los votos de un grado específico
def obtener_resultados_votaciones(grado):
    """Devuelve un diccionario con los votos de cada candidato en un grado específico."""
    votos = {}
    estudiantes = Estudiante.objects.filter(grado=grado)

    for estudiante in estudiantes:
        candidato = estudiante.candidato.nombre
        votos[candidato] = votos.get(candidato, 0) + 1

    return votos

# 🥧 Función para generar el gráfico de torta con los votos de todos los grados o un grado específico
def generar_grafico_torta(votos):
    """Genera un gráfico de torta con la distribución de votos en un grado o en todos los grados."""
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.pie(votos.values(), labels=votos.keys(), autopct='%1.1f%%', colors=['blue', 'red', 'green', 'purple'])
    ax.set_title("Distribución de Votos")

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)
    return buffer