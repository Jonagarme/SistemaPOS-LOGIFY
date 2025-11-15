from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


class Rol(models.Model):
    """Modelo para la tabla roles existente"""
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    creado_por = models.PositiveIntegerField(null=True, blank=True, db_column='creadoPor')
    creado_date = models.DateTimeField(db_column='creadoDate')
    editado_por = models.PositiveIntegerField(null=True, blank=True, db_column='editadoPor')
    editado_date = models.DateTimeField(null=True, blank=True, db_column='editadoDate')
    anulado = models.BooleanField(default=False)
    anulado_por = models.PositiveIntegerField(null=True, blank=True, db_column='anuladoPor')
    anulado_date = models.DateTimeField(null=True, blank=True, db_column='anuladoDate')
    
    class Meta:
        db_table = 'roles'
        managed = False  # No tocar la tabla existente
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        
    def __str__(self):
        return self.nombre


class UsuarioSistema(models.Model):
    """Modelo que mapea directamente a tu tabla usuarios existente"""
    id = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Rol, on_delete=models.PROTECT, db_column='idRol')
    nombre_usuario = models.CharField(max_length=50, unique=True, db_column='nombreUsuario')
    contrasena_hash = models.CharField(max_length=255, db_column='contrasenaHash')
    nombre_completo = models.CharField(max_length=150, db_column='nombreCompleto')
    email = models.EmailField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)
    
    # Campos de auditoría exactos de tu tabla
    creado_por = models.PositiveIntegerField(null=True, blank=True, db_column='creadoPor')
    creado_date = models.DateTimeField(db_column='creadoDate')
    editado_por = models.PositiveIntegerField(null=True, blank=True, db_column='editadoPor')
    editado_date = models.DateTimeField(null=True, blank=True, db_column='editadoDate')
    anulado = models.BooleanField(default=False)
    anulado_por = models.PositiveIntegerField(null=True, blank=True, db_column='anuladoPor')
    anulado_date = models.DateTimeField(null=True, blank=True, db_column='anuladoDate')
    
    class Meta:
        db_table = 'usuarios'
        managed = False  # No tocar la tabla existente
        verbose_name = 'Usuario del Sistema'
        verbose_name_plural = 'Usuarios del Sistema'
        ordering = ['nombre_completo']
    
    def __str__(self):
        return f"{self.nombre_completo} ({self.nombre_usuario})"
    
    @property
    def estado_display(self):
        if self.anulado:
            return "Anulado"
        elif self.activo:
            return "Activo"
        else:
            return "Inactivo"
    
    @property
    def rol_nombre(self):
        return self.id_rol.nombre if self.id_rol else "Sin rol"

    @property
    def esta_activo(self):
        return self.activo and not self.anulado

    @property
    def puede_iniciar_sesion(self):
        return self.activo and not self.anulado
    
    def check_password(self, raw_password):
        """Verificar contraseña - implementar según tu sistema de hash"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.contrasena_hash)


# Modelos adicionales que puedas tener
class PerfilUsuario(models.Model):
    """Perfil extendido de usuario"""
    usuario = models.OneToOneField('auth.User', on_delete=models.CASCADE)
    rol = models.CharField(max_length=50, choices=[
        ('admin', 'Administrador'),
        ('vendedor', 'Vendedor'),
        ('cajero', 'Cajero'),
        ('gerente', 'Gerente'),
    ], default='vendedor')
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    foto = models.ImageField(upload_to='perfiles/', blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
    
    def __str__(self):
        return self.usuario.get_full_name() or self.usuario.username


class ConfiguracionEmpresa(models.Model):
    """Configuración general de la empresa"""
    nombre = models.CharField(max_length=200)
    ruc = models.CharField(max_length=20, unique=True)
    direccion = models.TextField()
    telefono = models.CharField(max_length=20)
    email = models.EmailField()
    logo = models.ImageField(upload_to='empresa/', blank=True, null=True)
    moneda = models.CharField(max_length=10, default='USD')
    simbolo_moneda = models.CharField(max_length=5, default='$')
    igv = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    serie_factura = models.CharField(max_length=10, default='F001')
    serie_boleta = models.CharField(max_length=10, default='B001')
    correlativo_factura = models.PositiveIntegerField(default=1)
    correlativo_boleta = models.PositiveIntegerField(default=1)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración de Empresa'
        verbose_name_plural = 'Configuraciones de Empresa'
    
    def __str__(self):
        return self.nombre