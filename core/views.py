from functools import wraps

from django import forms
from django.shortcuts import render, get_object_or_404, redirect
from .models import Viaje, Usuario
from openai import OpenAI

from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from openai import OpenAI

from .models import ChatMessage  

client = OpenAI()  # usará OPENAI_API_KEY del entorno virtual


# ========= Helpers de sesión =========

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
    viajes = Viaje.objects.all().order_by('-fecha_ida')[:5]
    return render(request, 'core/home.html', {
        'usuario_actual': usuario_actual,
        'viajes': viajes,
    })


# ========= VISTAS DE VIAJES =========

def lista_viajes(request):
    usuario_actual = get_usuario_actual(request)
    viajes = Viaje.objects.all().order_by('fecha_ida')
    return render(request, 'core/lista_viajes.html', {
        'viajes': viajes,
        'usuario_actual': usuario_actual,
    })


def detalle_viaje(request, viaje_id):
    usuario_actual = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)
    participantes = viaje.participantes.all()
    es_creador = usuario_actual and (viaje.creador_id == usuario_actual.id)

    return render(request, 'core/detalle_viaje.html', {
        'viaje': viaje,
        'participantes': participantes,
        'usuario_actual': usuario_actual,
        'es_creador': es_creador,
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


class UsuarioUpdateForm(forms.ModelForm):
    fecha_nacimiento = forms.DateField(
        label='Fecha de nacimiento',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    nueva_contraseña = forms.CharField(
        label='Nueva contraseña',
        widget=forms.PasswordInput,
        required=False,
        help_text='Déjalo en blanco para mantener la contraseña actual.'
    )

    class Meta:
        model = Usuario
        fields = ['correo', 'nombre', 'apellidos', 'fecha_nacimiento']

    def clean_correo(self):
        correo = self.cleaned_data['correo']
        qs = Usuario.objects.filter(correo=correo).exclude(id=self.instance.id)
        if qs.exists():
            raise forms.ValidationError("Ya existe un usuario con este correo electrónico.")
        return correo


class LoginForm(forms.Form):
    correo = forms.EmailField(label='Correo electrónico')
    contraseña = forms.CharField(widget=forms.PasswordInput, label='Contraseña')


# ========= VISTAS DE USUARIO =========

def registro(request):
    usuario_actual = get_usuario_actual(request)
    if request.method == 'POST':
        form = UsuarioCreateForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            # login automático
            request.session['usuario_id'] = usuario.id
            return redirect('core:home')
    else:
        form = UsuarioCreateForm()

    return render(request, 'core/registro.html', {
        'form': form,
        'usuario_actual': usuario_actual,
    })


def login_view(request):
    usuario_actual = get_usuario_actual(request)
    if usuario_actual:
        return redirect('core:home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['correo']
            contraseña = form.cleaned_data['contraseña']
            try:
                usuario = Usuario.objects.get(correo=correo, contraseña=contraseña)
                request.session['usuario_id'] = usuario.id
                return redirect('core:home')
            except Usuario.DoesNotExist:
                form.add_error(None, "Correo o contraseña incorrectos.")
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
def perfil(request):
    usuario = get_usuario_actual(request)
    return render(request, 'core/perfil.html', {
        'usuario_actual': usuario,
        'usuario': usuario,
    })


@login_required_usuario
def editar_perfil(request):
    usuario = get_usuario_actual(request)
    if request.method == 'POST':
        form = UsuarioUpdateForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save()
            nueva_contraseña = form.cleaned_data.get('nueva_contraseña')
            if nueva_contraseña:
                usuario.contraseña = nueva_contraseña
                usuario.save()
            return redirect('core:perfil')
    else:
        form = UsuarioUpdateForm(instance=usuario)

    return render(request, 'core/editar_perfil.html', {
        'form': form,
        'usuario_actual': usuario,
    })


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
            'ciudad_destino',
            'pais_destino',
            'fecha_ida',
            'fecha_vuelta',
            'punto_encuentro',
            'precio',
            'estado',
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

import json
from .models import Viaje, Usuario, ChatMessage

MAX_ULTIMOS_MENSAJES = 10     # 10 mensajes (5 user + 5 assistant)

@require_POST
@login_required_usuario
def chat_viaje_api(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    if viaje.creador_id != usuario.id:
        return JsonResponse({"error": "No autorizado"}, status=403)

    try:
        data = json.loads(request.body.decode("utf-8"))
        user_text = (data.get("message") or "").strip()
    except Exception:
        return JsonResponse({"error": "JSON inválido"}, status=400)

    if not user_text:
        return JsonResponse({"error": "Mensaje vacío"}, status=400)

    ChatMessage.objects.create(viaje=viaje, role="user", content=user_text)

    system_prompt = f"""
    Eres SyncBot, el asistente del viaje en SyncTrip.
    Tu objetivo es ayudar a planificar y ajustar el itinerario del viaje.

    REGLAS DE RESPUESTA (OBLIGATORIAS):
    - Sé conciso: máximo 10 viñetas por respuesta.
    - Si el usuario pide un itinerario, devuélvelo estructurado por días.
    - Si falta información, haz SOLO 1 pregunta.
    - Evita datos demasiado exactos si no estás seguro.

    CONTEXTO DEL VIAJE:
    - Destino: {viaje.ciudad_destino}, {viaje.pais_destino}
    - Fechas: {viaje.fecha_ida} a {viaje.fecha_vuelta}
    - Punto de encuentro: {viaje.punto_encuentro}
    - Precio: {viaje.precio} €
    """.strip()

    history = list(
        ChatMessage.objects.filter(viaje=viaje)
        .order_by("-created_at")[:MAX_ULTIMOS_MENSAJES] #10 mensajes para el contexto
    )
    print("MAX_ULTIMOS_MENSAJES =", MAX_ULTIMOS_MENSAJES)
    print("Mensajes recuperados =", len(history))
    print("IDs recuperados =", [m.id for m in history])

    history.reverse()

    conversation = [f"SYSTEM: {system_prompt}"]
    for m in history:
        role = "USER" if m.role == "user" else "ASSISTANT"
        conversation.append(f"{role}: {m.content}")
    conversation.append("ASSISTANT:")
    prompt = "\n\n".join(conversation)

    try:
        resp = client.responses.create(
            model="gpt-4.1-mini",
            input=prompt,
            max_output_tokens=450,
            temperature=0.1,
        )
        #extraer el texto de la respuesta
        assistant_text = resp.output[0].content[0].text.strip()
    except Exception as e:
        return JsonResponse({"error": f"Error OpenAI: {str(e)}"}, status=500)

    ChatMessage.objects.create(viaje=viaje, role="assistant", content=assistant_text)
    return JsonResponse({
        "reply": assistant_text,
        "usage": resp.usage if hasattr(resp, "usage") else None
    })

@require_GET
@login_required_usuario
def chat_viaje_historial(request, viaje_id):
    usuario = get_usuario_actual(request)
    viaje = get_object_or_404(Viaje, id=viaje_id)

    if viaje.creador_id != usuario.id:
        return JsonResponse({"error": "No autorizado"}, status=403)

    msgs = ChatMessage.objects.filter(viaje=viaje).order_by("created_at")[:50] #interfaz 50 mensajes
    data = [{"role": m.role, "content": m.content} for m in msgs]
    return JsonResponse({"messages": data})
