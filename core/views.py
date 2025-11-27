from functools import wraps

from django import forms
from django.shortcuts import render, get_object_or_404, redirect

from .models import Viaje, Usuario


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

