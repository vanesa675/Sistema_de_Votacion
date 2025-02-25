from django.db import models

class Grado(models.Model):
    nombre = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre

class Estudiante(models.Model):
    nombre = models.CharField(max_length=100)
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE)

    def __str__(self):
        return self.nombre

class Candidato(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Voto(models.Model):
    estudiante = models.OneToOneField(Estudiante, on_delete=models.CASCADE)
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE, null=True, blank=True)  # Puede ser voto en blanco
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.estudiante.nombre} - {self.candidato.nombre if self.candidato else 'Voto en Blanco'}"