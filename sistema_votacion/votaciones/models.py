from django.db import models

class Grado(models.Model):
    nombre = models.CharField(max_length=10, unique=True)  # Ejemplo: "1°A", "2°B", "10°"

    def __str__(self):
        return self.nombre
    
class Mesa(models.Model):
    nombre = models.IntegerField(unique=True)

    def __str__(self):
        return f"Mesa {self.nombre}"

class Candidato(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.ImageField(upload_to="candidatos/", default="candidatos/perfil.png")  # ✅ Imagen por defecto

    def __str__(self):
        return self.nombre

class Estudiante(models.Model):
    nombre = models.CharField(max_length=100)
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE, null=True, blank=True)  # ✅ Permite valores nulos
    mesa = models.ForeignKey("Mesa", on_delete=models.CASCADE, default=1)  # 🔹 Asignar un valor por defecto

    def __str__(self):
        return f"{self.nombre} - {self.grado.nombre} - Candidato {self.candidato}"



class Voto(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE, null=True, blank=True)  # ✅ Permite valores nulos
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE, default=1)  # ✅ Usar un grado por defecto
    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE, default=1)  # ✅ Usar un grado por defecto
    def __str__(self):
        return f"{self.estudiante} votó por {self.candidato} en la mesa {self.mesa}"
    



    

