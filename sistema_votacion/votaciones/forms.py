from django import forms
from .models import Estudiante, grado

class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = ['nombre', 'grado', 'mesa']

class EstudianteForm(forms.ModelForm):

    class Meta:
        model = Estudiante
        fields = ['nombre', 'grado', 'mesa']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['grado'].queryset = Grado.objects.order_by('numero')