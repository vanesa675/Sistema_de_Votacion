from django.db import models

class Grado(models.Model):
    nombre = models.CharField(max_length=10, unique=True)  # Ejemplo: "1°A", "2°B", "10°"

    def __str__(self):
        return self.nombre
    
class Mesa(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"{self.nombre}"

class Candidato(models.Model):
    nombre = models.CharField(max_length=100)
    tarjeton = models.IntegerField(unique=True)
    imagen = models.ImageField(upload_to='candidatos/')  # Guarda la imagen en /media/candidatos/

    def __str__(self):
        return f"{self.nombre} - Tarjetón #{self.tarjeton}"


class Estudiante(models.Model):
    nombre = models.CharField(max_length=100)
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE, null=True, blank=True)  # ✅ Permite valores nulos
    mesa = models.ForeignKey("Mesa", on_delete=models.CASCADE, default=1)  # 🔹 Asignar un valor por defecto

    def __str__(self):
        return f"{self.grado.nombre} - {self.mesa} - {self.nombre} - Candidato {self.tarjeton}"



class Voto(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE)
    candidato = models.ForeignKey(Candidato, on_delete=models.CASCADE, null=True, blank=True)  # ✅ Permite valores nulos
    grado = models.ForeignKey(Grado, on_delete=models.CASCADE, default=1)  # ✅ Usar un grado por defecto
    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE, default=1)  # ✅ Usar un grado por defecto
    def __str__(self):
        return f"{self.estudiante} votó por {self.candidato} en la mesa {self.mesa}"
    



    

