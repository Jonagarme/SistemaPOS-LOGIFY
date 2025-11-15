from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.validators import RegexValidator
from decimal import Decimal
from django.utils import timezone


class Rol(models.Model):
    """Modelo para la tabla roles"""
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    permisos = models.TextField(null=True, blank=True)  # JSON con permisos
    
    # Campos de auditoría
    creado_date = models.DateTimeField(default=timezone.now, db_column='creadoDate')
    editado_date = models.DateTimeField(null=True, blank=True, db_column='editadoDate')
    
    class Meta:
        db_table = 'roles'
        managed = True
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        
    def __str__(self):
        return self.nombre


class CustomUserManager(BaseUserManager):
    """Manager personalizado para el modelo Usuario"""
    
    def create_user(self, nombre_usuario, email, password=None, **extra_fields):
        if not email:
            raise ValueError('El usuario debe tener un email')
        if not nombre_usuario:
            raise ValueError('El usuario debe tener un nombre de usuario')
            
        email = self.normalize_email(email)
        user = self.model(
            nombre_usuario=nombre_usuario,
            email=email,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, nombre_usuario, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')
            
        return self.create_user(nombre_usuario, email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Modelo personalizado que mapea a la tabla usuarios existente"""
    
    id = models.AutoField(primary_key=True)
    id_rol = models.ForeignKey('Rol', on_delete=models.PROTECT, db_column='idRol')
    nombre_usuario = models.CharField(max_length=50, unique=True, db_column='nombreUsuario')
    contrasena_hash = models.CharField(max_length=255, db_column='contrasenaHash')
    nombre_completo = models.CharField(max_length=150, db_column='nombreCompleto')
    email = models.EmailField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)
    
    # Campos de auditoría
    creado_por = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='usuarios_creados', db_column='creadoPor')
    creado_date = models.DateTimeField(db_column='creadoDate', default=timezone.now)
    editado_por = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='usuarios_editados', db_column='editadoPor')
    editado_date = models.DateTimeField(null=True, blank=True, db_column='editadoDate')
    anulado = models.BooleanField(default=False)
    anulado_por = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='usuarios_anulados', db_column='anuladoPor')
    anulado_date = models.DateTimeField(null=True, blank=True, db_column='anuladoDate')
    
    # Campos requeridos por Django
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    
    # Resolver conflictos de related_name con User de Django
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='usuario_set',
        related_query_name='usuario',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='usuario_set',
        related_query_name='usuario',
    )
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'nombre_usuario'
    REQUIRED_FIELDS = ['email', 'nombre_completo']
    
    class Meta:
        db_table = 'usuarios'
        managed = True  # Cambiado para permitir migraciones
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
    
    def __str__(self):
        return f"{self.nombre_usuario} - {self.nombre_completo}"
    
    @property
    def password(self):
        return self.contrasena_hash
    
    @password.setter
    def password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.contrasena_hash = make_password(raw_password)
    
    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.contrasena_hash = make_password(raw_password)
    
    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.contrasena_hash)
    
    def get_full_name(self):
        return self.nombre_completo
    
    def get_short_name(self):
        return self.nombre_usuario
    
    @property
    def rol_nombre(self):
        return self.id_rol.nombre if self.id_rol else 'Sin rol'


# Mantener el modelo existente para compatibilidad
class PerfilUsuario(models.Model):
    ROLES = (
        ('admin', 'Administrador'),
        ('cajero', 'Cajero'),
        ('vendedor', 'Vendedor'),
        ('supervisor', 'Supervisor'),
    )
    
    usuario = models.OneToOneField('Usuario', on_delete=models.CASCADE)
    rol = models.CharField(max_length=20, choices=ROLES, default='cajero')
    telefono = models.CharField(
        max_length=15, 
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$', message="Número de teléfono debe tener entre 9 y 15 dígitos.")],
        blank=True
    )
    direccion = models.TextField(blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuarios"
    
    def __str__(self):
        return f"{self.usuario.get_full_name()} - {self.get_rol_display()}"

    @property
    def nombre_completo(self):
        return self.usuario.get_full_name() or self.usuario.username


class ConfiguracionEmpresa(models.Model):
    # Información general de la empresa
    nombre = models.CharField(
        max_length=200,
        verbose_name="Nombre de la empresa",
        help_text="Nombre completo de la empresa"
    )
    rtn = models.CharField(
        max_length=20,
        verbose_name="RTN",
        help_text="Registro Tributario Nacional",
        blank=True
    )
    telefono = models.CharField(
        max_length=20,
        verbose_name="Teléfono",
        blank=True
    )
    email = models.EmailField(
        verbose_name="Correo electrónico",
        blank=True
    )
    direccion = models.TextField(
        verbose_name="Dirección",
        blank=True
    )
    sitio_web = models.URLField(
        verbose_name="Sitio web",
        blank=True
    )
    
    # Logo de la empresa (comentado temporalmente hasta resolver Pillow)
    # logo = models.ImageField(
    #     upload_to='empresa/',
    #     verbose_name="Logo",
    #     blank=True,
    #     null=True,
    #     help_text="Logo de la empresa (JPG, PNG, GIF)"
    # )
    
    # Configuración de facturación
    cai = models.CharField(
        max_length=50,
        verbose_name="CAI",
        help_text="Código de Autorización de Impresión",
        blank=True
    )
    rango_inicial = models.CharField(
        max_length=20,
        verbose_name="Rango inicial",
        help_text="Número inicial del rango de facturación",
        blank=True
    )
    rango_final = models.CharField(
        max_length=20,
        verbose_name="Rango final",
        help_text="Número final del rango de facturación",
        blank=True
    )
    fecha_limite_emision = models.DateField(
        verbose_name="Fecha límite de emisión",
        null=True,
        blank=True,
        help_text="Fecha límite para emisión de facturas"
    )
    
    # Configuración del sistema
    moneda = models.CharField(
        max_length=50,
        verbose_name="Moneda",
        default="Dólares",
        help_text="Nombre de la moneda utilizada"
    )
    simbolo_moneda = models.CharField(
        max_length=5,
        verbose_name="Símbolo de moneda",
        default="$",
        help_text="Símbolo utilizado para la moneda"
    )
    impuesto_defecto = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Impuesto por defecto",
        default=Decimal('15.00'),
        help_text="Porcentaje de impuesto por defecto"
    )
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración de Empresa"
        verbose_name_plural = "Configuraciones de Empresa"
    
    def __str__(self):
        return self.nombre
    
    @classmethod
    def obtener_configuracion(cls):
        """Obtiene la configuración de la empresa o crea una por defecto"""
        config, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'nombre': 'Mi Empresa',
                'moneda': 'Dólares',
                'simbolo_moneda': '$',
                'impuesto_defecto': Decimal('15.00')
            }
        )
        return config


# Modelos para gestión de usuarios con tablas MySQL existentes

class Rol(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.CharField(max_length=255, null=True, blank=True)
    creado_por = models.PositiveIntegerField(null=True, blank=True, db_column='creadoPor')
    creado_date = models.DateTimeField(auto_now_add=True, db_column='creadoDate')
    editado_por = models.PositiveIntegerField(null=True, blank=True, db_column='editadoPor')
    editado_date = models.DateTimeField(auto_now=True, db_column='editadoDate')
    anulado = models.BooleanField(default=False)
    anulado_por = models.PositiveIntegerField(null=True, blank=True, db_column='anuladoPor')
    anulado_date = models.DateTimeField(null=True, blank=True, db_column='anuladoDate')
    
    class Meta:
        db_table = 'roles'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
    
    def __str__(self):
        return self.nombre


class Permiso(models.Model):
    id = models.AutoField(primary_key=True)
    nombre_menu = models.CharField(max_length=100, db_column='nombreMenu')
    clave_menu = models.CharField(max_length=100, unique=True, db_column='claveMenu')
    id_padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, db_column='idPadre')
    
    class Meta:
        db_table = 'permisos'
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'
    
    def __str__(self):
        return self.nombre_menu


# Modelo UsuarioSistema removido - ahora usamos Usuario personalizado para autenticación
