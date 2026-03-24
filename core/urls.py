from django.urls import path
from . import views
from django.views.generic import RedirectView
from django.templatetags.static import static

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
    path('viajes/<int:viaje_id>/itinerario/', views.itinerario_viaje, name='itinerario_viaje'),  # <--- NUEVO
    path('viajes/', views.lista_viajes, name='lista_viajes'),
    path('viajes/<int:viaje_id>/', views.detalle_viaje, name='detalle_viaje'),
    path('viajes/<int:viaje_id>/chat/', views.chat_viaje_api, name='chat_viaje_api'),
    path("favicon.ico", RedirectView.as_view(url=static("favicon.ico"))),
    path('viajes/<int:viaje_id>/chat/historial/', views.chat_viaje_historial, name='chat_viaje_historial'),
    # amistad
    path("amistad/enviar/", views.enviar_solicitud, name="enviar_solicitud"),
    path("amistad/<int:solicitud_id>/aceptar/", views.aceptar_solicitud, name="aceptar_solicitud"),
    path("amistad/<int:solicitud_id>/finalizar/", views.finalizar_solicitud, name="finalizar_solicitud"),
    path("viajes/<int:viaje_id>/invitar/", views.invitar_a_viaje, name="invitar_a_viaje"),
    path("invitaciones/<int:inv_id>/aceptar/", views.aceptar_invitacion, name="aceptar_invitacion"),
    path("invitaciones/<int:inv_id>/rechazar/", views.rechazar_invitacion, name="rechazar_invitacion"),
    # chat de grupo (viaje)
    path("viajes/<int:viaje_id>/grupo/crear/", views.crear_grupo_chat, name="crear_grupo_chat"),
    path("viajes/<int:viaje_id>/grupo/enviar/", views.enviar_mensaje_grupo, name="enviar_mensaje_grupo"),
    path("viajes/<int:viaje_id>/grupo/historial/", views.grupo_chat_historial_api, name="grupo_chat_historial_api"),
    path("viajes/<int:viaje_id>/grupo/enviar-json/", views.enviar_mensaje_grupo_api, name="enviar_mensaje_grupo_api"),
# urls.py
    path(
        "viajes/<int:viaje_id>/itinerario/publico/",
        views.actualizar_itinerario_publico,
        name="actualizar_itinerario_publico",
    ),
    path("solicitudes/", views.solicitudes, name="solicitudes"),
    path(
        "viajes/<int:viaje_id>/unirme/",
        views.unirse_a_viaje,
        name="unirse_a_viaje"
    ),

    path("viajes/<int:viaje_id>/gastos/", views.gastos_viaje, name="gastos_viaje"),
    path("viajes/<int:viaje_id>/gastos/crear/", views.crear_gasto, name="crear_gasto"),
    path("viajes/<int:viaje_id>/gastos/<int:gasto_id>/", views.detalle_gasto, name="detalle_gasto"),
    path("viajes/<int:viaje_id>/balance/", views.balance_viaje, name="balance_viaje"),

    path(
    "viajes/<int:viaje_id>/gastos/<int:gasto_id>/eliminar/",
    views.eliminar_gasto,
    name="eliminar_gasto"
    ),

]




