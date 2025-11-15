from django import forms
from .models import Cliente


class ClienteForm(forms.ModelForm):
    """Formulario para crear y editar clientes"""
    
    class Meta:
        model = Cliente
        fields = [
            'tipo_identificacion', 'cedula_ruc', 'nombres', 'apellidos', 
            'razon_social', 'direccion', 'telefono', 'celular', 'email',
            'fecha_nacimiento', 'tipo_cliente', 'estado'
        ]
        
        widgets = {
            'tipo_identificacion': forms.Select(
                attrs={'class': 'form-select'}
            ),
            'cedula_ruc': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese cédula o RUC',
                    'maxlength': '20'
                }
            ),
            'nombres': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nombres'
                }
            ),
            'apellidos': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Apellidos'
                }
            ),
            'razon_social': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Razón Social (para empresas)'
                }
            ),
            'direccion': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Dirección completa'
                }
            ),
            'telefono': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Teléfono fijo'
                }
            ),
            'celular': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Teléfono celular'
                }
            ),
            'email': forms.EmailInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'correo@ejemplo.com'
                }
            ),
            'fecha_nacimiento': forms.DateInput(
                attrs={
                    'class': 'form-control',
                    'type': 'date'
                }
            ),
            'tipo_cliente': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Tipo de cliente'
                }
            ),
            'estado': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            )
        }
        
        labels = {
            'tipo_identificacion': 'Tipo de Identificación',
            'cedula_ruc': 'Cédula/RUC',
            'nombres': 'Nombres',
            'apellidos': 'Apellidos',
            'razon_social': 'Razón Social',
            'direccion': 'Dirección',
            'telefono': 'Teléfono',
            'celular': 'Celular',
            'email': 'Email',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'tipo_cliente': 'Tipo de Cliente',
            'estado': 'Activo'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campos requeridos
        self.fields['tipo_identificacion'].required = True
        self.fields['cedula_ruc'].required = True
        
        # Validaciones adicionales
        self.fields['cedula_ruc'].help_text = 'Debe ser único en el sistema'

    def clean_cedula_ruc(self):
        cedula_ruc = self.cleaned_data.get('cedula_ruc')
        if cedula_ruc:
            # Verificar que no exista otro cliente con la misma cédula/RUC
            existing = Cliente.objects.filter(cedula_ruc=cedula_ruc, anulado=False)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError('Ya existe un cliente con esta cédula/RUC.')
        
        return cedula_ruc

    def clean(self):
        cleaned_data = super().clean()
        tipo_identificacion = cleaned_data.get('tipo_identificacion')
        nombres = cleaned_data.get('nombres')
        apellidos = cleaned_data.get('apellidos')
        razon_social = cleaned_data.get('razon_social')
        
        # Validar que tenga al menos nombres o razón social
        if not razon_social and not (nombres or apellidos):
            raise forms.ValidationError(
                'Debe ingresar al menos nombres y apellidos, o una razón social.'
            )
        
        return cleaned_data