from django.urls import path
from . import views

app_name = 'core'  # para usar namespaced URLs

urlpatterns = [
    path('', views.home, name='home'),

    # usuario / auth
    path('registro/', views.registro, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('perfil/', views.perfil, name='perfil'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('perfil/borrar/', views.borrar_cuenta, name='borrar_cuenta'),

    # viajes
    path('viajes/nuevo/', views.crear_viaje, name='crear_viaje'),
    path('viajes/<int:viaje_id>/editar/', views.editar_viaje, name='editar_viaje'),
    path('viajes/<int:viaje_id>/eliminar/', views.eliminar_viaje, name='eliminar_viaje'),
    path('viajes/', views.lista_viajes, name='lista_viajes'),
    path('viajes/<int:viaje_id>/', views.detalle_viaje, name='detalle_viaje'),
]


