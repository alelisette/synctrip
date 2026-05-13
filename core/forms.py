from django import forms

from .models import Usuario


class UsuarioUpdateForm(forms.ModelForm):
    contraseña_actual = forms.CharField(
        label="Contraseña actual",
        required=False,
        widget=forms.PasswordInput,
        help_text="Solo necesaria si quieres cambiar la contraseña.",
    )
    nueva_contraseña = forms.CharField(
        label="Nueva contraseña",
        required=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = Usuario
        fields = ["username", "correo", "nombre", "apellidos", "fecha_nacimiento"]

    def clean(self):
        cleaned_data = super().clean()
        nueva = cleaned_data.get("nueva_contraseña")
        actual = cleaned_data.get("contraseña_actual")
        if nueva:
            if not actual:
                self.add_error("contraseña_actual", "Introduce tu contraseña actual para poder cambiarla.")
            elif not self.instance.check_password(actual):
                self.add_error("contraseña_actual", "La contraseña actual no es correcta.")
        return cleaned_data

    def save(self, commit=True):
        usuario = super().save(commit=False)
        nueva = self.cleaned_data.get("nueva_contraseña")
        if nueva:
            usuario.set_password(nueva)
        if commit:
            usuario.save()
        return usuario
