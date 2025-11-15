from django import forms
from django.forms import inlineformset_factory
from .models import Cotizacion, DetalleCotizacion
from clientes.models import Cliente
from productos.models import Producto
from datetime import datetime, timedelta


class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ['cliente', 'referencia_cliente', 'fecha', 'fecha_vencimiento', 'validez_dias', 'descuento_global', 'observaciones', 'condiciones', 'estado', 'subtotal', 'impuesto', 'total']
        widgets = {
            'cliente': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'referencia_cliente': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número de orden, proyecto, etc.'
            }),
            'fecha': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'fecha_vencimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'validez_dias': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '365',
                'value': '15'
            }),
            'descuento_global': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100',
                'value': '0.00',
                'placeholder': '0.00'
            }),
            'observaciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Observaciones adicionales...'
            }),
            'condiciones': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Términos y condiciones de la cotización...'
            }),
            'estado': forms.Select(attrs={
                'class': 'form-select'
            }),
            'subtotal': forms.HiddenInput(),
            'impuesto': forms.HiddenInput(),
            'total': forms.HiddenInput(),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar fechas por defecto
        if not self.instance.pk:
            fecha_hoy = datetime.now().date()
            fecha_vencimiento = fecha_hoy + timedelta(days=15)
            self.fields['fecha'].initial = fecha_hoy
            self.fields['fecha_vencimiento'].initial = fecha_vencimiento
        
        # Configurar queryset de clientes
        self.fields['cliente'].queryset = Cliente.objects.filter(estado=True, anulado=False).order_by('nombres')
        
        # Valores por defecto para términos y condiciones
        if not self.fields['condiciones'].initial:
            self.fields['condiciones'].initial = """1. Esta cotización es válida por {validez_dias} días.
2. Los precios incluyen ISV (15%).
3. Tiempo de entrega: A convenir.
4. Forma de pago: A convenir.
5. Esta cotización no constituye una factura."""


class DetalleCotizacionForm(forms.ModelForm):
    class Meta:
        model = DetalleCotizacion
        fields = ['producto', 'cantidad', 'precio_unitario', 'descuento_linea']
        widgets = {
            'producto': forms.Select(attrs={
                'class': 'form-select producto-select',
                'required': True,
                'data-live-search': 'true'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control cantidad-input',
                'min': '1',
                'value': '1',
                'required': True
            }),
            'precio_unitario': forms.NumberInput(attrs={
                'class': 'form-control precio-input',
                'step': '0.01',
                'min': '0',
                'required': True
            }),
            'descuento_linea': forms.NumberInput(attrs={
                'class': 'form-control descuento-input',
                'step': '0.01',
                'min': '0',
                'value': '0.00'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar queryset de productos activos
        self.fields['producto'].queryset = Producto.objects.filter(activo=True).order_by('nombre')
        
        # Si hay un producto seleccionado, establecer su precio
        if self.instance.pk and self.instance.producto:
            self.fields['precio_unitario'].initial = self.instance.producto.precio_venta


# Formset para manejar múltiples detalles de cotización
DetalleCotizacionFormSet = inlineformset_factory(
    Cotizacion,
    DetalleCotizacion,
    form=DetalleCotizacionForm,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True
)


class BuscarCotizacionForm(forms.Form):
    ESTADO_CHOICES = [
        ('', 'Todos los estados'),
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
        ('vencida', 'Vencida'),
        ('convertida', 'Convertida a Venta'),
    ]
    
    busqueda = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Buscar por número, cliente...'
        })
    )
    
    estado = forms.ChoiceField(
        choices=ESTADO_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(estado=True, anulado=False).order_by('nombres'),
        required=False,
        empty_label='Todos los clientes',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    fecha_desde = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    fecha_hasta = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class ConvertirVentaForm(forms.Form):
    confirmar = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Confirmo que deseo convertir esta cotización en una venta'
    )
    
    observaciones_venta = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Observaciones para la venta (opcional)...'
        }),
        label='Observaciones para la venta'
    )