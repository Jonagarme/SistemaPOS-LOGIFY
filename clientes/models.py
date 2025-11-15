from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import User


class Cliente(models.Model):
    """Modelo adaptado para la estructura de clientes de LogiPharmBD"""
    
    TIPO_IDENTIFICACION_CHOICES = [
        ('CEDULA', 'Cédula'),
        ('RUC', 'RUC'),
        ('PASAPORTE', 'Pasaporte'),
    ]
    
    # Campos principales
    tipo_identificacion = models.CharField(max_length=10, choices=TIPO_IDENTIFICACION_CHOICES)
    cedula_ruc = models.CharField(max_length=20, unique=True)
    nombres = models.CharField(max_length=100, null=True, blank=True)
    apellidos = models.CharField(max_length=100, null=True, blank=True)
    razon_social = models.CharField(max_length=200, null=True, blank=True, db_column='razonSocial')
    
    # Información de contacto
    direccion = models.TextField(null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    celular = models.CharField(max_length=20, null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    
    # Información adicional
    fecha_nacimiento = models.DateField(null=True, blank=True)
    tipo_cliente = models.CharField(max_length=50, null=True, blank=True)
    
    # Control y auditoría
    estado = models.BooleanField(default=True)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, related_name='clientes_creados', db_column='creadoPor')
    creado_date = models.DateTimeField(db_column='creadoDate')
    editado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='clientes_editados', db_column='editadoPor')
    editado_date = models.DateTimeField(null=True, blank=True, db_column='editadoDate')
    anulado = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'clientes'
        managed = False
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombres', 'apellidos']
    
    def __str__(self):
        if self.razon_social:
            return f"{self.cedula_ruc} - {self.razon_social}"
        else:
            return f"{self.cedula_ruc} - {self.nombres} {self.apellidos}".strip()
    
    @property
    def nombre_completo(self):
        """Devuelve el nombre completo del cliente"""
        if self.razon_social:
            return self.razon_social
        else:
            return f"{self.nombres or ''} {self.apellidos or ''}".strip()
    
    @property
    def activo(self):
        """Alias para compatibilidad con el código existente"""
        return self.estado and not self.anulado
    
    @property
    def telefono_principal(self):
        """Devuelve el celular si existe, sino el teléfono"""
        return self.celular or self.telefono or ''
