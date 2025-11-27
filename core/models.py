# Create your models here.
from django.db import models


class Usuario(models.Model):
    correo = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)
    # Para un TFG sencillo puedes usar CharField, pero en un proyecto real usarías el sistema de usuarios de Django.
    contraseña = models.CharField(max_length=128)
    fecha_nacimiento = models.DateField()

    def __str__(self):
        return f"{self.nombre} {self.apellidos} <{self.correo}>"


class Viaje(models.Model):
    ESTADO_CHOICES = [
        ('EN_CURSO', 'En curso'),
        ('FINALIZADO', 'Finalizado'),
        ('CANCELADO', 'Cancelado'),
        # añade los estados que te hagan falta
    ]

    ciudad_destino = models.CharField(max_length=100)
    pais_destino = models.CharField(max_length=100)
    fecha_ida = models.DateField()
    fecha_vuelta = models.DateField()
    punto_encuentro = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE')

    # id_usuario → fk al usuario que crea el viaje
    creador = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='viajes_creados'
    )

    # relación N:M con Usuario a través de la tabla intermedia Participa
    participantes = models.ManyToManyField(
        Usuario,
        through='Participa',
        related_name='viajes_en_los_que_participa'
    )

    def __str__(self):
        return f"{self.ciudad_destino} ({self.pais_destino}) [{self.fecha_ida} - {self.fecha_vuelta}]"


class Participa(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('usuario', 'viaje')  # un usuario no puede apuntarse dos veces al mismo viaje

    def __str__(self):
        return f"{self.usuario} participa en {self.viaje}"
