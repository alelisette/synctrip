# Create your models here.
from django.db import models


class Usuario(models.Model):
    username = models.CharField(max_length=30, unique=True)
    correo = models.EmailField(unique=True)
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)
    # Para un TFG sencillo puedes usar CharField, pero en un proyecto real usarías el sistema de usuarios de Django.
    contraseña = models.CharField(max_length=128)
    fecha_nacimiento = models.DateField()

    def __str__(self):
        return f"{self.username} ({self.correo})"



from django.db import models

class Viaje(models.Model):

    # Enum de estado del viaje
    class EstadoViaje(models.TextChoices):
        PROGRAMADO = "PROGRAMADO", "Programado"
        EN_CURSO = "EN_CURSO", "En curso"
        FINALIZADO = "FINALIZADO", "Finalizado"
        CANCELADO = "CANCELADO", "Cancelado"

    # Enum de visibilidad
    class Visibilidad(models.TextChoices):
        PRIVADO = "PRIVADO", "Privado"
        PUBLICO = "PUBLICO", "Público"

    ciudad_origen = models.CharField(max_length=100)
    pais_origen = models.CharField(max_length=100)

    ciudad_destino = models.CharField(max_length=100)
    pais_destino = models.CharField(max_length=100)

    fecha_ida = models.DateField()
    fecha_vuelta = models.DateField()

    direccion_encuentro = models.CharField(max_length=200)

    # Precio por persona (en lugar de precio)
    precio_persona = models.DecimalField(max_digits=8, decimal_places=2)

    # Estado del viaje (ENUM)
    estado_viaje = models.CharField(
        max_length=20,
        choices=EstadoViaje.choices,
        default=EstadoViaje.PROGRAMADO
    )

    # Visibilidad (ENUM)
    visibilidad = models.CharField(
        max_length=10,
        choices=Visibilidad.choices,
        default=Visibilidad.PUBLICO
    )

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
        return (
            f"{self.ciudad_origen} ({self.pais_origen}) → "
            f"{self.ciudad_destino} ({self.pais_destino}) "
            f"[{self.fecha_ida} - {self.fecha_vuelta}]"
        )


class Participa(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('usuario', 'viaje')  # un usuario no puede apuntarse dos veces al mismo viaje

    def __str__(self):
        return f"{self.usuario} participa en {self.viaje}"

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    viaje = models.ForeignKey("Viaje", on_delete=models.CASCADE, related_name="chat_messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.viaje_id} {self.role} {self.created_at}"

class SolicitudAmistad(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ACEPTADA = "ACEPTADA", "Aceptada"
        FINALIZADA = "FINALIZADA", "Finalizada"  # (puedes usarla como "eliminada/terminada")

    emisor = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="solicitudes_enviadas"
    )
    receptor = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name="solicitudes_recibidas"
    )

    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Evita duplicados: mismo emisor->receptor
            models.UniqueConstraint(fields=["emisor", "receptor"], name="unique_solicitud_emisor_receptor"),
            # Evita que alguien se envíe a sí mismo
            models.CheckConstraint(check=~models.Q(emisor=models.F("receptor")), name="no_autosolicitud"),
        ]

    def __str__(self):
        return f"{self.emisor.username} -> {self.receptor.username} ({self.estado})"


class InvitacionViaje(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        ACEPTADA = "ACEPTADA", "Aceptada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    viaje = models.ForeignKey(Viaje, on_delete=models.CASCADE, related_name="invitaciones")
    emisor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="invitaciones_enviadas")
    receptor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="invitaciones_recibidas")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["viaje", "receptor"], name="unique_invitacion_por_viaje_receptor"),
            models.CheckConstraint(check=~models.Q(emisor=models.F("receptor")), name="no_autoinvitacion"),
        ]

    def __str__(self):
        return f"Invitación {self.viaje_id}: {self.emisor.username} -> {self.receptor.username} ({self.estado})"

from django.db import models
from django.utils import timezone

class GrupoChat(models.Model):
    """
    Un chat opcional por viaje (0..1).
    Solo se crea si el creador del viaje lo decide.
    """
    viaje = models.OneToOneField(
        "Viaje",
        on_delete=models.CASCADE,
        related_name="grupo_chat"
    )
    creado_por = models.ForeignKey(
        "Usuario",
        on_delete=models.CASCADE,
        related_name="grupos_chat_creados"
    )
    nombre = models.CharField(max_length=100, default="Chat del viaje")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GrupoChat({self.viaje_id}) - {self.nombre}"


class MensajeGrupoChat(models.Model):
    """
    Mensajes del grupo del viaje.
    Solo pueden escribir usuarios participantes de ese viaje.
    """
    grupo = models.ForeignKey(
        "GrupoChat",
        on_delete=models.CASCADE,
        related_name="mensajes"
    )
    autor = models.ForeignKey(
        "Usuario",
        on_delete=models.CASCADE,
        related_name="mensajes_grupo"
    )
    contenido = models.TextField()
    fecha_envio = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha_envio"]

    def __str__(self):
        return f"{self.grupo.viaje_id} @{self.autor.username}: {self.contenido[:30]}"