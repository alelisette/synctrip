from django import forms

from .models import Usuario


class UsuarioUpdateForm(forms.ModelForm):
    nueva_contraseña = forms.CharField(
        label="Nueva contraseña",
        required=False,
        widget=forms.PasswordInput,
    )

    class Meta:
        model = Usuario
        fields = ["username", "correo", "nombre", "apellidos", "fecha_nacimiento"]

    def save(self, commit=True):
        usuario = super().save(commit=False)
        nueva = self.cleaned_data.get("nueva_contraseña")
        if nueva:
            usuario.contraseña = nueva
        if commit:
            usuario.save()
        return usuario
