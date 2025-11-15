from django import forms
from .models import Proveedor


class ProveedorForm(forms.ModelForm):
    """Formulario para crear y editar proveedores"""
    
    class Meta:
        model = Proveedor
        fields = [
            'ruc', 'razon_social', 'nombre_comercial', 
            'direccion', 'telefono', 'email', 'estado'
        ]
        
        widgets = {
            'ruc': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Ingrese RUC',
                    'maxlength': '13'
                }
            ),
            'razon_social': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Razón Social'
                }
            ),
            'nombre_comercial': forms.TextInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'Nombre Comercial (opcional)'
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
                    'placeholder': 'Teléfono'
                }
            ),
            'email': forms.EmailInput(
                attrs={
                    'class': 'form-control',
                    'placeholder': 'correo@ejemplo.com'
                }
            ),
            'estado': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            )
        }
        
        labels = {
            'ruc': 'RUC',
            'razon_social': 'Razón Social',
            'nombre_comercial': 'Nombre Comercial',
            'direccion': 'Dirección',
            'telefono': 'Teléfono',
            'email': 'Email',
            'estado': 'Activo'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Campos requeridos
        self.fields['ruc'].required = True
        self.fields['razon_social'].required = True
        
        # Validaciones adicionales
        self.fields['ruc'].help_text = 'Debe ser único en el sistema'

    def clean_ruc(self):
        ruc = self.cleaned_data.get('ruc')
        if ruc:
            # Verificar que no exista otro proveedor con el mismo RUC
            existing = Proveedor.objects.filter(ruc=ruc, anulado=False)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise forms.ValidationError('Ya existe un proveedor con este RUC.')
        
        return ruc

    def clean(self):
        cleaned_data = super().clean()
        razon_social = cleaned_data.get('razon_social')
        
        # Validar que tenga razón social
        if not razon_social:
            raise forms.ValidationError('La razón social es obligatoria.')
        
        return cleaned_data