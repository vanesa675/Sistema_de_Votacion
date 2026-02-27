from django.contrib import admin
from django.urls import path, reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from .models import Grado, Estudiante, Candidato, Voto, Mesa


class GradoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descargar_pdf', 'descargar_excel')

    def descargar_pdf(self, obj):
        return format_html(
            '<a href="{}" class="button">📄 Descargar PDF</a>',
            reverse('descargar_pdf', args=[obj.id])
        )
    descargar_pdf.short_description = "Reporte PDF"

    def descargar_excel(self, obj):
        return format_html(
            '<a href="{}" class="button">📊 Descargar Excel</a>',
            reverse('descargar_excel', args=[obj.id])
        )
    descargar_excel.short_description = "Reporte Excel"

    # 🔥 BOTONES SUPERIORES PERSONALIZADOS
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'descargar-todos/',
                self.admin_site.admin_view(self.redireccion_descargas)
            ),
        ]
        return custom_urls + urls

    def redireccion_descargas(self, request):
        return HttpResponseRedirect(reverse('descargar_todos_pdf'))

    # 🔹 Botón Excel por grado
    def descargar_excel(self, obj):
        return format_html(
            '<a href="{}" class="button">📊 Descargar Excel</a>',
            reverse('descargar_excel', args=[obj.id])
        )
    descargar_excel.short_description = "Reporte Excel"

    # 🔥 BOTONES GENERALES ARRIBA
    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['descargar_todos_pdf'] = reverse('descargar_todos_pdf')
        extra_context['descargar_todos_excel'] = reverse('descargar_todos_excel')
        return super().changelist_view(request, extra_context=extra_context)

class ReportesAdmin(admin.ModelAdmin):
    change_list_template = "admin/reportes.html"

admin.site.register(Voto, ReportesAdmin)

admin.site.register(Grado, GradoAdmin)
admin.site.register(Estudiante)
admin.site.register(Candidato)
admin.site.register(Mesa)