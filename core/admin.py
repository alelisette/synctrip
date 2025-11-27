from django.contrib import admin
from .models import Usuario, Viaje, Participa

# Register your models here.
admin.site.register(Usuario)
admin.site.register(Viaje)
admin.site.register(Participa)