from django.contrib import admin
from django.urls import path
from django.contrib.auth.decorators import login_required, user_passes_test
from votaciones.views import (
    guardar_voto, descargar_pdf, descargar_excel, descargar_todos_pdf, descargar_todos_excel
)

# Función para verificar si el usuario es administrador
def es_admin(user):
    return user.is_staff  # Solo los administradores pueden acceder

urlpatterns = [
    # Panel de administración
    path('admin/', admin.site.urls),

    # Página principal
    path('', guardar_voto, name='guardar_voto'),

    # 📌 Rutas para descargar reportes **POR GRADO**
    path('descargar-pdf/<int:grado>/', login_required(user_passes_test(es_admin)(descargar_pdf)), name='descargar_pdf'),
    path('descargar-excel/<int:grado>/', login_required(user_passes_test(es_admin)(descargar_excel)), name='descargar_excel'),

    # 📌 Rutas para descargar reportes **DE TODOS LOS GRADOS**
    path('descargar-todos-pdf/', login_required(user_passes_test(es_admin)(descargar_todos_pdf)), name='descargar_todos_pdf'),
    path('descargar-todos-excel/', login_required(user_passes_test(es_admin)(descargar_todos_excel)), name='descargar_todos_excel'),
]
