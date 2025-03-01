from django.contrib import admin
from django.utils.html import format_html
from .models import Grado, Estudiante, Candidato, Voto, Mesa

class GradoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descargar_pdf', 'descargar_excel')

    def descargar_pdf(self, obj):
        return format_html(f'<a href="/descargar-pdf/{obj.id}/" class="button">📄 Descargar PDF</a>')
    descargar_pdf.short_description = "Reporte PDF"

    def descargar_excel(self, obj):
        return format_html(f'<a href="/descargar-excel/{obj.id}/" class="button">📊 Descargar Excel</a>')
    descargar_excel.short_description = "Reporte Excel"
    
class ReporteAdmin(admin.ModelAdmin):
    def obtener_reportes(self):
        return format_html(
            '<a href="/descargar-pdf/" class="button">📄 Descargar TODOS los PDF</a>'
            ' | '
            '<a href="/descargar-excel/" class="button">📊 Descargar TODOS los Excel</a>'
        )

    obtener_reportes.short_description = "Descargar todos los reportes"

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['reporte_botones'] = self.obtener_reportes()
        return super().changelist_view(request, extra_context=extra_context)

admin.site.register(Grado, GradoAdmin)
admin.site.register(Estudiante)
admin.site.register(Candidato)
admin.site.register(Mesa)
admin.site.index_template = "admin/index.html"

