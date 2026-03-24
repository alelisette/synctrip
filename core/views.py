from functools import wraps

from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from .models import Viaje, Usuario

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from openai import OpenAI

from .models import Usuario, SolicitudAmistad
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.db import models
from django.db.models import Q

from .models import InvitacionViaje
from .models import SolicitudAmistad, InvitacionViaje

from .models import ChatMessage  
from .models import GrupoChat, MensajeGrupoChat
from .forms import UsuarioUpdateForm


client = OpenAI()  # usará OPENAI_API_KEY del entorno virtual


# ========= Helpers de sesión =========
from decimal import Decimal, ROUND_HALF_UP
from django.views.decorators.http import require_POST, require_GET
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect

from .models import Viaje, Usuario, Gasto, GastoSplit, ParticipanteGasto

from decimal import Decimal

def liquidar_balances(balances: dict):
    """
    balances: {usuario: Decimal}
    Retorna lista de transferencias:
      [{"deudor": u1, "acreedor": u2, "importe": Decimal}, ...]
    """
    acreedores = []
    deudores = []

    for u, bal in balances.items():
        if bal > 0:
            # Usuario que debe cobrar (le deben dinero)
            acreedores.append([u, bal])
        elif bal < 0:
            # Usuario que debe pagar (balance negativo)
            deudores.append([u, -bal])  # deuda positiva

    # Ordenar por importe descendente para emparejar grandes deudas primero
    acreedores.sort(key=lambda x: x[1], reverse=True)
    deudores.sort(key=lambda x: x[1], reverse=True)

    transferencias = []
    i = 0
    j = 0

    # Emparejar deudores con acreedores hasta saldar todos los importes
    while i < len(deudores) and j < len(acreedores):
        du, deuda = deudores[i]
        au, credito = acreedores[j]

        # Se transfiere el mínimo entre lo que debe y lo que debe cobrar
        x = deuda if deuda < credito else credito

        # Registrar la transferencia: du paga x a au
        transferencias.append({
            "deudor": du,
            "acreedor": au,
            "importe": x
        })

        # Actualizamos los saldos restantes
        deudores[i][1] = deuda - x
        acreedores[j][1] = credito - x

        # Si el deudor ya pagó todo, pasamos al siguiente
        if deudores[i][1] == 0:
            i += 1
        # Si el acreedor ya cobró todo, pasamos al siguiente
        if acreedores[j][1] == 0:
            j += 1

    return transferencias

def asegurar_participante_y_privado(request, viaje: Viaje, usuario: Usuario):
    if viaje.visibilidad != Viaje.Visibilidad.PRIVADO:
        messages.error(request, "Los gastos solo están disponibles en viajes privados.")
        return False

    if not viaje.participantes.filter(id=usuario.id).exists():
        messages.error(request, "No eres participante de este viaje.")
        return False

    return True


def get_usuario_actual(request):
    usuario_id = request.session.get('usuario_id')
    if not usuario_id:
        return None
    try:
        return Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        return None


def login_required_usuario(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not get_usuario_actual(request):
            return redirect('core:login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ========= HOME =========
def home(request):
    usuario_actual = get_usuario_actual(request)

    viajes = (
        Viaje.objects
        .filter(visibilidad=Viaje.Visibilidad.PUBLICO)
        .order_by('-fecha_ida')
    )

    return render(request, 'core/home.html', {
        'usuario_actual': usuario_actual,
        'viajes': viajes,
    })



# ========= VISTAS DE VIAJES =========

from django.db.models import Q
@login_required_usuario
def lista_viajes(request):
    usuario = get_usuario_actual(request)

    viajes = (
        Viaje.objects
        .filter(participantes=usuario)
        .distinct()
        .order_by("fecha_ida")
    )

    return render(request, "core/lista_viajes.html", {
        "viajes": viajes,
        "usuario_actual": usuario,
    })



def detalle_viaje(request, viaje_id):
    usuario_actual = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    participantes = viaje.participantes.all()
    es_creador = usuario_actual and (viaje.creador_id == usuario_actual.id)

    # 🔒 Bloqueo de viajes privados: solo creador o participantes
    if viaje.visibilidad == Viaje.Visibilidad.PRIVADO:
        if not usuario_actual:
            return redirect('core:login')
        if (not es_creador) and (usuario_actual not in participantes):
            return redirect('core:lista_viajes')  # o puedes devolver 403

    usuario_actual = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)
    participantes = viaje.participantes.all()
    es_creador = usuario_actual and (viaje.creador_id == usuario_actual.id)
    # ===== Chat de grupo del viaje (opcional) =====
    grupo_chat = GrupoChat.objects.filter(viaje=viaje).first()
    mensajes_grupo = []
    if grupo_chat:
        mensajes_grupo = (MensajeGrupoChat.objects
                          .filter(grupo=grupo_chat)
                          .select_related("autor")
                          .order_by("fecha_envio")[:100])  # últimos 100
        
    return render(request, 'core/detalle_viaje.html', {
        'viaje': viaje,
        'participantes': participantes,
        'usuario_actual': usuario_actual,
        'es_creador': es_creador,
        "grupo_chat": grupo_chat,
        "mensajes_grupo": mensajes_grupo,

    })

# ========= FORMULARIOS DE USUARIO =========

class UsuarioCreateForm(forms.ModelForm):
    contraseña = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput
    )
    fecha_nacimiento = forms.DateField(
        label='Fecha de nacimiento',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Usuario
        fields = ['correo', 'nombre', 'apellidos', 'contraseña', 'fecha_nacimiento']



class UsuarioCreateForm(forms.ModelForm):
    contraseña = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput
    )
    fecha_nacimiento = forms.DateField(
        label='Fecha de nacimiento',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Usuario
        fields = ['username', 'correo', 'nombre', 'apellidos', 'contraseña', 'fecha_nacimiento']

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Ese username ya está en uso.")
        return username


class LoginForm(forms.Form):
    identificador = forms.CharField(label="Correo o username")  # <-- campo único
    contraseña = forms.CharField(widget=forms.PasswordInput, label="Contraseña")



# ========= VISTAS DE USUARIO =========

def registro(request):
    usuario_actual = get_usuario_actual(request)
    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            request.session['usuario_id'] = usuario.id  # login automático
            return redirect('core:home')
    else:
        form = UsuarioCreateForm()

    return render(request, 'core/registro.html', {
        'form': form,
        'usuario_actual': usuario_actual,
    })


class UsuarioCreateForm(forms.ModelForm):
    contraseña = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput
    )
    fecha_nacimiento = forms.DateField(
        label='Fecha de nacimiento',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Usuario
        fields = ['username', 'correo', 'nombre', 'apellidos', 'contraseña', 'fecha_nacimiento']

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if Usuario.objects.filter(username=username).exists():
            raise forms.ValidationError("Ese username ya está en uso.")
        return username


def login_view(request):
    usuario_actual = get_usuario_actual(request)
    if usuario_actual:
        return redirect('core:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)

        # ✅ PRIMERO validar el form
        if form.is_valid():
            identificador = form.cleaned_data['identificador'].strip()
            contraseña = form.cleaned_data['contraseña']

            try:
                usuario = Usuario.objects.get(
                    (Q(correo=identificador) | Q(username=identificador)) &
                    Q(contraseña=contraseña)
                )
                request.session['usuario_id'] = usuario.id
                return redirect('core:home')
            except Usuario.DoesNotExist:
                form.add_error(None, "Credenciales incorrectas.")
    else:
        form = LoginForm()

    return render(request, 'core/login.html', {
        'form': form,
        'usuario_actual': usuario_actual,
    })




def logout_view(request):
    request.session.flush()
    return redirect('core:home')


@login_required_usuario
def solicitudes(request):
    usuario = get_usuario_actual(request)

    solicitudes_recibidas = SolicitudAmistad.objects.filter(
        receptor=usuario, estado="PENDIENTE"
    ).select_related("emisor").order_by("-id")

    solicitudes_enviadas = SolicitudAmistad.objects.filter(
        emisor=usuario
    ).select_related("receptor").order_by("-id")[:10]

    invitaciones_viaje = InvitacionViaje.objects.filter(
        receptor=usuario, estado="PENDIENTE"
    ).select_related("emisor", "viaje").order_by("-id")

    return render(request, "core/solicitudes.html", {
        "usuario_actual": usuario,
        "solicitudes_recibidas": solicitudes_recibidas,
        "solicitudes_enviadas": solicitudes_enviadas,
        "invitaciones_viaje": invitaciones_viaje,
    })


@login_required_usuario
def perfil(request):
    usuario = get_usuario_actual(request)

    if request.method == "POST":
        form = UsuarioUpdateForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            messages.success(request, "Cambios guardados ✅")
            return redirect("core:perfil")
        else:
            messages.error(request, "Revisa los campos marcados.")
    else:
        form = UsuarioUpdateForm(instance=usuario)

    return render(request, "core/perfil_editable.html", {
        "usuario_actual": usuario,
        "usuario": usuario,
        "form": form,
    })



@login_required_usuario
def editar_perfil(request):
    return redirect("core:perfil")


@login_required_usuario
def borrar_cuenta(request):
    usuario = get_usuario_actual(request)
    if request.method == 'POST':
        usuario.delete()
        request.session.flush()
        return redirect('core:home')
    return render(request, 'core/borrar_cuenta.html', {
        'usuario_actual': usuario,
    })

# ---------- FORMULARIO DE VIAJE ----------

class ViajeCreateForm(forms.ModelForm):
    fecha_ida = forms.DateField(
        label='Fecha de ida',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    fecha_vuelta = forms.DateField(
        label='Fecha de vuelta',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Viaje
        fields = [
            'ciudad_origen',
            'pais_origen',
            'ciudad_destino',
            'pais_destino',
            'fecha_ida',
            'fecha_vuelta',
            'direccion_encuentro',
            'precio_persona',
            'estado_viaje',
            'visibilidad',
        ]


@login_required_usuario
def crear_viaje(request):
    usuario = get_usuario_actual(request)

    if request.method == 'POST':
        form = ViajeCreateForm(request.POST)
        if form.is_valid():
            viaje = form.save(commit=False)
            viaje.creador = usuario   # el usuario actual es el creador
            viaje.save()

            # opcional: que el creador también sea participante del viaje
            viaje.participantes.add(usuario)

            return redirect('core:detalle_viaje', viaje_id=viaje.id)
    else:
        form = ViajeCreateForm()

    return render(request, 'core/crear_viaje.html', {
        'form': form,
        'usuario_actual': usuario,
    })

@login_required_usuario
def editar_viaje(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    # Solo el creador puede editar
    if viaje.creador_id != usuario.id:
        return redirect('core:detalle_viaje', viaje_id=viaje.id)

    if request.method == 'POST':
        form = ViajeCreateForm(request.POST, instance=viaje)
        if form.is_valid():
            form.save()
            return redirect('core:detalle_viaje', viaje_id=viaje.id)
    else:
        form = ViajeCreateForm(instance=viaje)

    return render(request, 'core/editar_viaje.html', {
        'form': form,
        'usuario_actual': usuario,
        'viaje': viaje,
    })


@login_required_usuario
def eliminar_viaje(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    # Solo el creador puede eliminar
    if viaje.creador_id != usuario.id:
        return redirect('core:detalle_viaje', viaje_id=viaje.id)

    if request.method == 'POST':
        viaje.delete()
        return redirect('core:lista_viajes')

    # Si es GET, mostramos pantalla de confirmación
    return render(request, 'core/eliminar_viaje.html', {
        'usuario_actual': usuario,
        'viaje': viaje,
    })

@login_required_usuario
def itinerario_viaje(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    # Solo el creador puede acceder al itinerario
    if viaje.creador_id != usuario.id:
        return redirect('core:detalle_viaje', viaje_id=viaje.id)

    itinerario_texto = None
    error_api = None

    if request.method == 'POST':
        prompt = (
            f"Genera un itinerario detallado en español para un viaje a "
            f"{viaje.ciudad_destino}, {viaje.pais_destino} "
            f"desde el {viaje.fecha_ida} hasta el {viaje.fecha_vuelta}. "
            f"Organiza el contenido por días y con viñetas."
        )
        try:
            resp = client.responses.create(
                model="gpt-4.1-mini",
                input=prompt,
            )
            itinerario_texto = resp.output[0].content[0].text
        except Exception as e:
            error_api = str(e)

    return render(request, 'core/itinerario_viaje.html', {
        'usuario_actual': usuario,
        'viaje': viaje,
        'itinerario_texto': itinerario_texto,
        'error_api': error_api,
    })

# Importa el módulo estándar para parsear/generar JSON
import json
# Importa modelos de tu app (tablas/entidades de BD de Django)
from .models import Viaje, Usuario, ChatMessage

# Número máximo de mensajes recientes que se enviarán como contexto al modelo
MAX_ULTIMOS_MENSAJES = 10     # 10 mensajes (5 user + 5 assistant)

@require_POST
@login_required_usuario
def chat_viaje_api(request, viaje_id):
    usuario = get_usuario_actual(request)
    # Busca el Viaje por id; si no existe, devuelve 404 automáticamente
    viaje = get_object_or_404(Viaje, id=viaje_id)

    if viaje.creador_id != usuario.id:
        return JsonResponse({"error": "No autorizado"}, status=403)

    # Intenta leer el body como JSON y extraer el texto del usuario
    try:
        # Decodifica bytes -> string UTF-8 y parsea a dict
        data = json.loads(request.body.decode("utf-8"))
        # Extrae "message"; si no existe o es None, usa "", y recorta espacios
        user_text = (data.get("message") or "").strip()
    except Exception:
        # Si el body no es JSON válido (o falla decode), responde 400 Bad Request
        return JsonResponse({"error": "JSON inválido"}, status=400)

    # Valida que el mensaje no esté vacío tras hacer strip()
    if not user_text:
        # Si está vacío, responde 400 Bad Request
        return JsonResponse({"error": "Mensaje vacío"}, status=400)

    # Guarda el mensaje del usuario en la BD asociado al viaje
    ChatMessage.objects.create(viaje=viaje, role="user", content=user_text)

    # Construye el prompt de sistema: identidad del bot + reglas + contexto del viaje
    system_prompt = f"""
    Eres SyncBot, el asistente del viaje en SyncTrip.
    Tu objetivo es ayudar a planificar y ajustar el itinerario del viaje.

    REGLAS DE RESPUESTA (OBLIGATORIAS):
    - Sé conciso: máximo 10 viñetas por respuesta.
    - Si el usuario pide un itinerario, devuélvelo estructurado por días.
    - Si falta información, haz SOLO 1 pregunta.
    - Evita datos demasiado exactos si no estás seguro.

    CONTEXTO DEL VIAJE:
    - Dirección de encuentro: {viaje.direccion_encuentro}
    - Precio por persona: {viaje.precio_persona} €
    - Origen: {viaje.ciudad_origen}, {viaje.pais_origen}
    - Destino: {viaje.ciudad_destino}, {viaje.pais_destino}
    - Fechas: {viaje.fecha_ida} a {viaje.fecha_vuelta}
    """.strip()  # strip() elimina saltos/espacios al inicio y al final

    # Recupera los últimos N mensajes del chat de ese viaje 
    history = list(
        # Filtra por viaje (solo mensajes de este chat)
        ChatMessage.objects.filter(viaje=viaje)
        # Ordena por fecha de creación descendente 
        .order_by("-created_at")[:MAX_ULTIMOS_MENSAJES]
    )
    # Debug: muestra la configuración de mensajes máximos
    print("MAX_ULTIMOS_MENSAJES =", MAX_ULTIMOS_MENSAJES)
    # Debug: cuántos mensajes se han recuperado realmente
    print("Mensajes recuperados =", len(history))
    # Debug: IDs de los mensajes recuperados (para verificar orden/selección)
    print("IDs recuperados =", [m.id for m in history])

    # Como se recuperaron en orden inverso (descendente), se invierte 
    history.reverse()
    # Inicia el “transcript” con el bloque SYSTEM (instrucciones + contexto)
    conversation = [f"SYSTEM: {system_prompt}"]
    # Recorre mensajes previos para construir el prompt con roles y contenido
    for m in history:
        role = "USER" if m.role == "user" else "ASSISTANT"
        # Añade el mensaje al transcript
        conversation.append(f"{role}: {m.content}")
    # Añade el marcador final para que el modelo continúe como el asistente
    conversation.append("ASSISTANT:")
    # Une todo en un string, separando bloques con líneas en blanco
    prompt = "\n\n".join(conversation)

    try:
        # Crea una respuesta con el modelo indicado
        resp = client.responses.create(
            # Modelo IA a usar
            model="gpt-4.1-mini",
            input=prompt,
            # Límite de tokens de salida (controla longitud)
            max_output_tokens=450,
            # Baja temperatura = más consistente
            temperature=0.1,
        )
        # extraer el texto de la respuesta
        assistant_text = resp.output[0].content[0].text.strip()
    except Exception as e:
        return JsonResponse({"error": f"Error OpenAI: {str(e)}"}, status=500)
    
    # Guarda la respuesta del asistente en BD asociada al mismo viaje
    ChatMessage.objects.create(viaje=viaje, role="assistant", content=assistant_text)
    # Devuelve la respuesta al frontend en JSON
    return JsonResponse({"reply": assistant_text})

@require_GET
@login_required_usuario
def chat_viaje_historial(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)
    if viaje.creador_id != usuario.id:
        return JsonResponse({"error": "No autorizado"}, status=403)
    # Recupera hasta 50 mensajes del viaje en orden cronológico 
    msgs = ChatMessage.objects.filter(viaje=viaje).order_by("created_at")[:50]
    # Serializa cada mensaje a un dict simple {role, content}
    data = [{"role": m.role, "content": m.content} for m in msgs]
    # Devuelve la lista como JSON
    return JsonResponse({"messages": data})

# ========= VISTAS DE AMISTAD =========

@require_POST
@login_required_usuario
def enviar_solicitud(request):
    usuario = get_usuario_actual(request)

    # OJO: el name del input en el HTML es "username_destino"
    username_destino = (request.POST.get("username_destino") or "").strip()

    if not username_destino:
        messages.error(request, "Debes escribir un username.")
        return redirect("core:perfil")

    try:
        receptor = Usuario.objects.get(username=username_destino)
    except Usuario.DoesNotExist:
        messages.error(request, "No existe ningún usuario con ese username.")
        return redirect("core:perfil")

    if receptor.id == usuario.id:
        messages.error(request, "No puedes enviarte una solicitud a ti mismo.")
        return redirect("core:perfil")

    obj, created = SolicitudAmistad.objects.get_or_create(
        emisor=usuario,
        receptor=receptor,
        defaults={"estado": SolicitudAmistad.Estado.PENDIENTE}
    )

    if not created:
        messages.info(request, f"Ya existe una solicitud hacia @{receptor.username} ({obj.get_estado_display()}).")
    else:
        messages.success(request, f"Solicitud enviada a @{receptor.username}.")

    return redirect("core:perfil")


@require_POST
@login_required_usuario
def aceptar_solicitud(request, solicitud_id):
    usuario = get_usuario_actual(request)
    sol = get_object_or_404(SolicitudAmistad, id=solicitud_id)

    # Solo el receptor puede aceptar
    if sol.receptor_id != usuario.id:
        return redirect("core:perfil")

    if sol.estado != SolicitudAmistad.Estado.PENDIENTE:
        return redirect("core:perfil")

    sol.estado = SolicitudAmistad.Estado.ACEPTADA
    sol.save()
    messages.success(request, f"Has aceptado a @{sol.emisor.username}.")
    return redirect("core:perfil")


@require_POST
@login_required_usuario
def finalizar_solicitud(request, solicitud_id):
    usuario = get_usuario_actual(request)
    sol = get_object_or_404(SolicitudAmistad, id=solicitud_id)

    # Solo emisor o receptor pueden finalizar/rechazar/cancelar
    if sol.emisor_id != usuario.id and sol.receptor_id != usuario.id:
        return redirect("core:perfil")

    sol.estado = SolicitudAmistad.Estado.FINALIZADA
    sol.save()
    messages.info(request, "Solicitud finalizada.")
    return redirect("core:perfil")

from django.views.decorators.http import require_POST

@require_POST
@login_required_usuario
def invitar_a_viaje(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    # Solo creador y solo si es privado
    if viaje.creador_id != usuario.id:
        return redirect("core:detalle_viaje", viaje_id=viaje.id)
    if viaje.visibilidad != Viaje.Visibilidad.PRIVADO:
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    username_destino = (request.POST.get("username_destino") or "").strip()

    if not username_destino:
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    try:
        receptor = Usuario.objects.get(username=username_destino)
    except Usuario.DoesNotExist:
        return render(request, "core/detalle_viaje.html", {
            "viaje": viaje,
            "participantes": viaje.participantes.all(),
            "usuario_actual": usuario,
            "es_creador": True,
            "invite_error": "No existe ningún usuario con ese username."
        })

    if receptor.id == usuario.id:
        return render(request, "core/detalle_viaje.html", {
            "viaje": viaje,
            "participantes": viaje.participantes.all(),
            "usuario_actual": usuario,
            "es_creador": True,
            "invite_error": "No puedes invitarte a ti misma."
        })

    # Si ya es participante
    if viaje.participantes.filter(id=receptor.id).exists():
        return render(request, "core/detalle_viaje.html", {
            "viaje": viaje,
            "participantes": viaje.participantes.all(),
            "usuario_actual": usuario,
            "es_creador": True,
            "invite_error": "Ese usuario ya está en el viaje."
        })

    # Crear invitación (si ya existe, no duplicar)
    invitacion, created = InvitacionViaje.objects.get_or_create(
        viaje=viaje,
        receptor=receptor,
        defaults={"emisor": usuario, "estado": InvitacionViaje.Estado.PENDIENTE}
    )

    if not created:
        return render(request, "core/detalle_viaje.html", {
            "viaje": viaje,
            "participantes": viaje.participantes.all(),
            "usuario_actual": usuario,
            "es_creador": True,
            "invite_error": f"Ya existe una invitación ({invitacion.estado})."
        })

    return render(request, "core/detalle_viaje.html", {
        "viaje": viaje,
        "participantes": viaje.participantes.all(),
        "usuario_actual": usuario,
        "es_creador": True,
        "invite_success": f"Invitación enviada a @{receptor.username}."
    })


@require_POST
@login_required_usuario
def aceptar_invitacion(request, inv_id):
    usuario = get_usuario_actual(request)
    invitacion = get_object_or_404(InvitacionViaje, id=inv_id)

    # Solo el receptor puede aceptar
    if invitacion.receptor_id != usuario.id:
        return redirect("core:perfil")

    if invitacion.estado != InvitacionViaje.Estado.PENDIENTE:
        return redirect("core:perfil")

    invitacion.viaje.participantes.add(usuario)
    invitacion.estado = InvitacionViaje.Estado.ACEPTADA
    invitacion.save()
    messages.success(request, "Invitación aceptada. Ya participas en el viaje.")
    return redirect("core:perfil")


@require_POST
@login_required_usuario
def rechazar_invitacion(request, inv_id):
    usuario = get_usuario_actual(request)
    invitacion = get_object_or_404(InvitacionViaje, id=inv_id)

    # Solo el receptor puede rechazar
    if invitacion.receptor_id != usuario.id:
        return redirect("core:perfil")

    if invitacion.estado != InvitacionViaje.Estado.PENDIENTE:
        return redirect("core:perfil")

    invitacion.estado = InvitacionViaje.Estado.RECHAZADA
    invitacion.save()
    messages.info(request, "Invitación rechazada.")
    return redirect("core:perfil")


from django.views.decorators.http import require_POST
from django.contrib import messages

@require_POST
@login_required_usuario
def crear_grupo_chat(request, viaje_id):
    """
    Solo el creador del viaje puede crear el grupo.
    El grupo es opcional (si no lo creas, no existe).
    """
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    if viaje.creador_id != usuario.id:
        return JsonResponse({"error": "No autorizado"}, status=403)

    # Si ya existe, no lo duplicamos
    if GrupoChat.objects.filter(viaje=viaje).exists():
        messages.info(request, "El grupo de chat ya existe.")
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    GrupoChat.objects.create(viaje=viaje, creado_por=usuario, nombre="Chat del viaje")
    messages.success(request, "Grupo de chat creado ✅")
    return redirect("core:detalle_viaje", viaje_id=viaje.id)


@require_POST
@login_required_usuario
def enviar_mensaje_grupo(request, viaje_id):
    """
    Solo participantes pueden enviar mensajes.
    El grupo debe existir.
    """
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    # Solo participantes
    es_participante = viaje.participantes.filter(id=usuario.id).exists()
    if not es_participante:
        return JsonResponse({"error": "No eres participante de este viaje"}, status=403)

    grupo = GrupoChat.objects.filter(viaje=viaje).first()
    if not grupo:
        messages.error(request, "Este viaje aún no tiene grupo de chat.")
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    contenido = (request.POST.get("contenido") or "").strip()
    if not contenido:
        messages.error(request, "Mensaje vacío.")
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    MensajeGrupoChat.objects.create(grupo=grupo, autor=usuario, contenido=contenido)
    return redirect("core:detalle_viaje", viaje_id=viaje.id)



@require_GET
@login_required_usuario
def grupo_chat_historial_api(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    if not viaje.participantes.filter(id=usuario.id).exists():
        return JsonResponse({"error": "No autorizado"}, status=403)

    grupo = GrupoChat.objects.filter(viaje=viaje).first()
    if not grupo:
        return JsonResponse({"messages": [], "has_group": False})

    msgs = (MensajeGrupoChat.objects
            .filter(grupo=grupo)
            .select_related("autor")
            .order_by("fecha_envio")[:100])

    data = [{
        "username": m.autor.username,
        "content": m.contenido,
        "fecha_envio": m.fecha_envio.isoformat(),
    } for m in msgs]

    return JsonResponse({"has_group": True, "messages": data})


@require_POST
@login_required_usuario
def enviar_mensaje_grupo_api(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    if not viaje.participantes.filter(id=usuario.id).exists():
        return JsonResponse({"error": "No autorizado"}, status=403)

    grupo = GrupoChat.objects.filter(viaje=viaje).first()
    if not grupo:
        return JsonResponse({"error": "No existe grupo"}, status=400)

    try:
        import json
        data = json.loads(request.body.decode("utf-8"))
        contenido = (data.get("contenido") or "").strip()
    except Exception:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    if not contenido:
        return JsonResponse({"error": "Mensaje vacío"}, status=400)

    m = MensajeGrupoChat.objects.create(grupo=grupo, autor=usuario, contenido=contenido)
    return JsonResponse({
        "ok": True,
        "message": {
            "username": m.autor.username,
            "content": m.contenido,
            "fecha_envio": m.fecha_envio.isoformat(),
        }
    })




# views.py
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

@require_POST
@login_required_usuario
def actualizar_itinerario_publico(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    # Solo creador
    if viaje.creador_id != usuario.id:
        messages.error(request, "No tienes permiso para editar el itinerario.")
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    texto = (request.POST.get("itinerario_publico") or "").strip()

    # límite opcional para evitar tochos infinitos
    if len(texto) > 8000:
        messages.error(request, "El itinerario es demasiado largo (máx. 8000 caracteres).")
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    viaje.itinerario_publico = texto
    viaje.save(update_fields=["itinerario_publico"])
    messages.success(request, "Itinerario actualizado ✅")
    return redirect("core:detalle_viaje", viaje_id=viaje.id)



@require_POST
def unirse_a_viaje(request, viaje_id):
    usuario = get_usuario_actual(request)

    # Si no hay sesión → login
    if not usuario:
        return redirect("core:login")

    viaje = get_object_or_404(Viaje, id=viaje_id)

    # Solo viajes públicos
    if viaje.visibilidad != Viaje.Visibilidad.PUBLICO:
        return redirect("core:home")

    # Evitar duplicados
    if not viaje.participantes.filter(id=usuario.id).exists():
        viaje.participantes.add(usuario)

    return redirect("core:detalle_viaje", viaje_id=viaje.id)



# views.py
from decimal import Decimal, ROUND_HALF_UP
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages

from .models import Viaje, Gasto, GastoSplit

@require_POST
@login_required_usuario
def crear_gasto(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    if not asegurar_participante_y_privado(request, viaje, usuario):
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    nombre = (request.POST.get("nombre") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    importe_str = (request.POST.get("importe_total") or "").strip().replace(",", ".")

    if not nombre or not importe_str:
        messages.error(request, "Rellena nombre e importe.")
        return redirect("core:gastos_viaje", viaje_id=viaje.id)

    try:
        importe_total = Decimal(importe_str).quantize(Decimal("0.01"))
        if importe_total <= 0:
            raise ValueError()
    except Exception:
        messages.error(request, "Importe inválido.")
        return redirect("core:gastos_viaje", viaje_id=viaje.id)

    participantes = list(viaje.participantes.all())
    n = len(participantes)

    if n < 2:
        messages.error(request, "Debe haber al menos 2 participantes para repartir gastos.")
        return redirect("core:gastos_viaje", viaje_id=viaje.id)

    gasto = Gasto.objects.create(
        viaje=viaje,
        pagador=usuario,
        nombre=nombre,
        descripcion=descripcion,
        importe_total=importe_total,
    )

    # Incluir participantes (siempre todos)
    ParticipanteGasto.objects.bulk_create([
        ParticipanteGasto(gasto=gasto, usuario=u) for u in participantes
    ])

    # Cuota por persona (base)
    share = (importe_total / Decimal(n)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Ajuste por redondeo: que la suma de splits sea EXACTAMENTE importe_total
    splits = [share for _ in range(n)]
    suma = sum(splits, Decimal("0.00"))
    ajuste = (importe_total - suma).quantize(Decimal("0.01"))

    # Aplicamos ajuste al pagador (puedes cambiarlo al último si prefieres)
    idx_pagador = next((i for i, u in enumerate(participantes) if u.id == usuario.id), 0)
    splits[idx_pagador] = (splits[idx_pagador] + ajuste).quantize(Decimal("0.01"))

    GastoSplit.objects.bulk_create([
        GastoSplit(gasto=gasto, usuario=u, importe=splits[i])
        for i, u in enumerate(participantes)
    ])

    messages.success(request, "Gasto creado y repartido ✅")
    return redirect("core:detalle_gasto", viaje_id=viaje.id, gasto_id=gasto.id)

@require_GET
@login_required_usuario
def gastos_viaje(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    if not asegurar_participante_y_privado(request, viaje, usuario):
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    gastos = (
        Gasto.objects
        .filter(viaje=viaje)
        .select_related("pagador")
        .order_by("-fecha_creacion")
    )

    # ===== Filtros =====
    username = (request.GET.get("username") or "").strip()
    precio_min = (request.GET.get("precio_min") or "").strip().replace(",", ".")
    precio_max = (request.GET.get("precio_max") or "").strip().replace(",", ".")

    if username:
        gastos = gastos.filter(pagador__username__icontains=username)

    try:
        if precio_min:
            gastos = gastos.filter(importe_total__gte=Decimal(precio_min))
    except Exception:
        messages.error(request, "El precio mínimo no es válido.")

    try:
        if precio_max:
            gastos = gastos.filter(importe_total__lte=Decimal(precio_max))
    except Exception:
        messages.error(request, "El precio máximo no es válido.")

    return render(request, "core/gastos_viaje.html", {
        "usuario_actual": usuario,
        "viaje": viaje,
        "gastos": gastos,
        "filtro_username": username,
        "filtro_precio_min": precio_min,
        "filtro_precio_max": precio_max,
    })


@require_GET
@login_required_usuario
def detalle_gasto(request, viaje_id, gasto_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    if not asegurar_participante_y_privado(request, viaje, usuario):
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    gasto = get_object_or_404(Gasto, id=gasto_id, viaje=viaje)

    splits = (GastoSplit.objects
              .filter(gasto=gasto)
              .select_related("usuario")
              .order_by("usuario__username"))

    # Para mostrar "Neto en este gasto":
    # neto = (pagó? total : 0) - cuota
    filas = []
    for s in splits:
        pago = gasto.importe_total if s.usuario_id == gasto.pagador_id else Decimal("0.00")
        neto = (pago - s.importe).quantize(Decimal("0.01"))
        filas.append({
            "usuario": s.usuario,
            "cuota": s.importe,
            "pago": pago,
            "neto": neto,
        })

    cuota_por_persona = (gasto.importe_total / Decimal(len(filas))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return render(request, "core/detalle_gasto.html", {
        "usuario_actual": usuario,
        "viaje": viaje,
        "gasto": gasto,
        "cuota_por_persona": cuota_por_persona,
        "filas": filas,
    })

@require_GET
@login_required_usuario
def balance_viaje(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    if not asegurar_participante_y_privado(request, viaje, usuario):
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    participantes = list(viaje.participantes.all())

    totales_pagado = {u.id: Decimal("0.00") for u in participantes}
    totales_debia = {u.id: Decimal("0.00") for u in participantes}

    # pagado
    for g in Gasto.objects.filter(viaje=viaje):
        totales_pagado[g.pagador_id] += g.importe_total

    # debia (splits)
    for s in GastoSplit.objects.filter(gasto__viaje=viaje):
        totales_debia[s.usuario_id] += s.importe

    balances = {}
    resumen = []

    for u in participantes:
        bal = (totales_pagado[u.id] - totales_debia[u.id]).quantize(Decimal("0.01"))
        balances[u] = bal
        resumen.append({
            "usuario": u,
            "pagado": totales_pagado[u.id],
            "debia": totales_debia[u.id],
            "balance": bal,
        })

    # Clasificación
    acreedores = [r for r in resumen if r["balance"] > 0]
    deudores = [r for r in resumen if r["balance"] < 0]

    # Liquidación sugerida
    transferencias = liquidar_balances(balances)

    return render(request, "core/balance_viaje.html", {
        "usuario_actual": usuario,
        "viaje": viaje,
        "resumen": resumen,
        "acreedores": acreedores,
        "deudores": deudores,
        "transferencias": transferencias,
    })



@require_POST
@login_required_usuario
def eliminar_gasto(request, viaje_id, gasto_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)
    gasto = get_object_or_404(Gasto, id=gasto_id, viaje=viaje)

    # Solo viajes privados
    if viaje.visibilidad != Viaje.Visibilidad.PRIVADO:
        messages.error(request, "Los gastos solo están disponibles en viajes privados.")
        return redirect("core:detalle_viaje", viaje_id=viaje.id)

    # Solo participantes
    if not viaje.participantes.filter(id=usuario.id).exists():
        messages.error(request, "No eres participante de este viaje.")
        return redirect("core:lista_viajes")

    # 🔴 SOLO el pagador puede eliminar
    if gasto.pagador_id != usuario.id:
        messages.error(request, "Solo el creador del gasto puede eliminarlo.")
        return redirect("core:detalle_gasto", viaje_id=viaje.id, gasto_id=gasto.id)

    gasto.delete()
    messages.success(request, "Gasto eliminado correctamente ✅")
    return redirect("core:gastos_viaje", viaje_id=viaje.id)
