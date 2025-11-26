from django.db import models
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
        managed = False  # No crear migraciones - tabla existente
        
    def __str__(self):
        return self.nombre


class UsuarioSistema(models.Model):
    """Modelo que mapea exactamente a tu tabla usuarios existente"""
    TIPO_MENU_CHOICES = [
        ('horizontal', 'Horizontal'),
        ('vertical', 'Vertical'),
    ]
    
    id = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey(Rol, on_delete=models.PROTECT, db_column='idRol')
    nombre_usuario = models.CharField(max_length=50, unique=True, db_column='nombreUsuario')
    contrasena_hash = models.CharField(max_length=255, db_column='contrasenaHash')
    nombre_completo = models.CharField(max_length=150, db_column='nombreCompleto')
    email = models.EmailField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)
    tipo_menu = models.CharField(max_length=20, choices=TIPO_MENU_CHOICES, default='horizontal', db_column='tipoMenu', null=True, blank=True)
    
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
        managed = False  # No crear migraciones - tabla existente
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
        """Verificar contraseña"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.contrasena_hash)


# Otros modelos que necesites (sin cambios en la BD)
class PerfilUsuario(models.Model):
    """Perfil extendido de usuario - tabla separada"""
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
    """Configuración general de la empresa usando tabla empresas existente"""
    id = models.AutoField(primary_key=True)
    ruc = models.CharField(max_length=13, unique=True, help_text='RUC de la empresa emisora')
    razon_social = models.CharField(max_length=300)
    nombre_comercial = models.CharField(max_length=300, blank=True, null=True)
    direccion_matriz = models.CharField(max_length=300, default='', blank=True)
    telefono = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    contribuyente_especial = models.CharField(max_length=200, blank=True, null=True)
    obligado_contabilidad = models.BooleanField(default=False)
    logo = models.BinaryField(blank=True, null=True, help_text='Logo de la empresa en formato binario')
    certificado_p12_path = models.CharField(max_length=512, blank=True, null=True)
    certificado_password = models.CharField(max_length=255, blank=True, null=True)
    certificado_fecha_expiracion = models.DateField(blank=True, null=True)
    tipo_menu = models.CharField(
        max_length=20, 
        choices=[('horizontal', 'Horizontal'), ('vertical', 'Vertical')], 
        default='horizontal',
        help_text='Tipo de menú de navegación',
        blank=True,
        null=True
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(blank=True, null=True)
    actualizado_en = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'empresas'
        verbose_name = 'Configuración de Empresa'
        verbose_name_plural = 'Configuraciones de Empresa'
    
    def __str__(self):
        return self.nombre_comercial or self.razon_social
    
    @classmethod
    def obtener_configuracion(cls):
        """Obtener la configuración activa de la empresa"""
        from django.db import OperationalError
        try:
            return cls.objects.filter(activo=True).first()
        except OperationalError:
            # Modo offline - retornar None
            return None
    
    # Propiedades para compatibilidad con el código existente
    @property
    def nombre(self):
        return self.nombre_comercial or self.razon_social
    
    @property
    def direccion(self):
        return self.direccion_matriz