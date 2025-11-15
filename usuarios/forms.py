from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.hashers import make_password
from .models import ConfiguracionEmpresa, UsuarioSistema, Rol


class PerfilUsuarioForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        label='Nombre',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su nombre'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        label='Apellido',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su apellido'
        })
    )
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'ejemplo@correo.com'
        })
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class ConfiguracionEmpresaForm(forms.ModelForm):
    # Campo para manejar el logo como archivo en lugar de binary
    logo_file = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        help_text='Seleccionar nuevo logo (JPG, PNG, GIF - máximo 2MB)'
    )
    
    class Meta:
        model = ConfiguracionEmpresa
        fields = [
            'ruc', 'razon_social', 'nombre_comercial', 'direccion_matriz',
            'telefono', 'email', 'contribuyente_especial', 'obligado_contabilidad',
            'tipo_menu',
            'certificado_p12_path', 'certificado_password', 'certificado_fecha_expiracion'
            # logo se maneja por separado como logo_file
        ]
        widgets = {
            'ruc': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '1234567890123',
                'maxlength': '13'
            }),
            'razon_social': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razón Social de la Empresa'
            }),
            'nombre_comercial': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre Comercial (opcional)'
            }),
            'direccion_matriz': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección completa de la empresa'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '2234-5678'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contacto@empresa.com'
            }),
            'contribuyente_especial': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de contribuyente especial (opcional)'
            }),
            'obligado_contabilidad': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'tipo_menu': forms.Select(attrs={
                'class': 'form-select'
            }),
            'certificado_p12_path': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ruta del certificado P12 (opcional)'
            }),
            'certificado_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Password del certificado (opcional)'
            }),
            'certificado_fecha_expiracion': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
        labels = {
            'ruc': 'RUC',
            'razon_social': 'Razón Social',
            'nombre_comercial': 'Nombre Comercial',
            'direccion_matriz': 'Dirección',
            'telefono': 'Teléfono',
            'email': 'Email',
            'contribuyente_especial': 'Contribuyente Especial',
            'obligado_contabilidad': 'Obligado a llevar contabilidad',
            'tipo_menu': 'Tipo de Menú',
            'certificado_p12_path': 'Ruta Certificado P12',
            'certificado_password': 'Password Certificado',
            'certificado_fecha_expiracion': 'Fecha Expiración Certificado'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Añadir clases Bootstrap a todos los campos
        for field in self.fields.values():
            if 'class' not in field.widget.attrs:
                field.widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Manejar el logo como binary field
        if self.cleaned_data.get('logo_file'):
            logo_file = self.cleaned_data['logo_file']
            instance.logo = logo_file.read()
        
        if commit:
            instance.save()
        return instance


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


# Formularios para gestión de usuarios del sistema

class UsuarioSistemaForm(forms.ModelForm):
    """Formulario para crear/editar usuarios del sistema"""
    
    contrasena = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese la contraseña'
        }),
        required=True,
        min_length=6,
        help_text="Mínimo 6 caracteres"
    )
    
    confirmar_contrasena = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirme la contraseña'
        }),
        required=True
    )
    
    class Meta:
        model = UsuarioSistema
        fields = [
            'nombre_usuario', 'nombre_completo', 'email', 
            'id_rol', 'activo', 'tipo_menu'
        ]
        widgets = {
            'nombre_usuario': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Usuario único para el sistema'
            }),
            'nombre_completo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del usuario'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'id_rol': forms.Select(attrs={
                'class': 'form-select'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'tipo_menu': forms.Select(attrs={
                'class': 'form-select'
            })
        }
        labels = {
            'nombre_usuario': 'Nombre de usuario',
            'nombre_completo': 'Nombre completo',
            'email': 'Correo electrónico',
            'id_rol': 'Rol',
            'activo': 'Usuario activo',
            'tipo_menu': 'Tipo de Menú'
        }
    
    def __init__(self, *args, **kwargs):
        self.is_edit = kwargs.pop('is_edit', False)
        super().__init__(*args, **kwargs)
        
        # Filtrar roles activos
        self.fields['id_rol'].queryset = Rol.objects.filter(anulado=False)
        
        # Si es edición, hacer contraseña opcional
        if self.is_edit:
            self.fields['contrasena'].required = False
            self.fields['confirmar_contrasena'].required = False
            self.fields['contrasena'].help_text = "Dejar en blanco para mantener la contraseña actual"
    
    def clean_confirmar_contrasena(self):
        contrasena = self.cleaned_data.get('contrasena')
        confirmar_contrasena = self.cleaned_data.get('confirmar_contrasena')
        
        if contrasena and contrasena != confirmar_contrasena:
            raise forms.ValidationError("Las contraseñas no coinciden")
        
        return confirmar_contrasena
    
    def clean_nombre_usuario(self):
        nombre_usuario = self.cleaned_data.get('nombre_usuario')
        
        if nombre_usuario:
            # Verificar unicidad
            qs = UsuarioSistema.objects.filter(nombre_usuario=nombre_usuario)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise forms.ValidationError("Este nombre de usuario ya existe")
        
        return nombre_usuario
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        if email:
            # Verificar unicidad
            qs = UsuarioSistema.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise forms.ValidationError("Este correo electrónico ya está registrado")
        
        return email
    
    def save(self, commit=True, usuario_actual=None):
        instance = super().save(commit=False)
        
        # Hash de contraseña si se proporcionó
        contrasena = self.cleaned_data.get('contrasena')
        if contrasena:
            instance.contrasena_hash = make_password(contrasena)
        
        # Campos de auditoría
        from django.utils import timezone
        if not instance.pk:  # Nuevo usuario
            instance.creado_date = timezone.now()
            if usuario_actual:
                instance.creado_por = usuario_actual.id
        else:  # Edición
            instance.editado_date = timezone.now()
            if usuario_actual:
                instance.editado_por = usuario_actual.id
        
        if commit:
            instance.save()
        
        return instance


class RolForm(forms.ModelForm):
    """Formulario para crear/editar roles"""
    
    class Meta:
        model = Rol
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del rol'
            }),
            'descripcion': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Descripción del rol',
                'rows': 3
            })
        }
        labels = {
            'nombre': 'Nombre del rol',
            'descripcion': 'Descripción'
        }
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        
        if nombre:
            # Verificar unicidad
            qs = Rol.objects.filter(nombre=nombre, anulado=False)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            
            if qs.exists():
                raise forms.ValidationError("Ya existe un rol con este nombre")
        
        return nombre
    
    def save(self, commit=True, usuario_actual=None):
        instance = super().save(commit=False)
        
        # Campos de auditoría
        from django.utils import timezone
        if not instance.pk:  # Nuevo rol
            instance.creado_date = timezone.now()
            if usuario_actual:
                instance.creado_por = usuario_actual.id
        else:  # Edición
            instance.editado_date = timezone.now()
            if usuario_actual:
                instance.editado_por = usuario_actual.id
        
        if commit:
            instance.save()
        
        return instance