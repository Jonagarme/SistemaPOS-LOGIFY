# Temporalmente comentado para resolver conflictos de migración
# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from .models import Usuario, PerfilUsuario


# @admin.register(Usuario)
# class UsuarioAdmin(BaseUserAdmin):
#     # Los campos que se mostrarán en el formulario de edición del usuario
#     fieldsets = (
#         (None, {'fields': ('nombreUsuario', 'password')}),
#         ('Información personal', {'fields': ('nombre', 'apellidos', 'email')}),
#         ('Permisos', {'fields': ('activo', 'es_staff', 'es_superusuario')}),
#         ('Fechas importantes', {'fields': ('ultimoAcceso', 'fechaCreacion')}),
#     )
#     # Los campos que se mostrarán en el formulario de creación de usuario
#     add_fieldsets = (
#         (None, {
#             'classes': ('wide',),
#             'fields': ('nombreUsuario', 'email', 'nombre', 'apellidos', 'password1', 'password2'),
#         }),
#     )
#     list_display = ('nombreUsuario', 'email', 'nombre', 'apellidos', 'activo')
#     list_filter = ('activo', 'fechaCreacion')
#     search_fields = ('nombreUsuario', 'nombre', 'apellidos', 'email')
#     ordering = ('nombreUsuario',)
#     filter_horizontal = ()


# @admin.register(PerfilUsuario)
# class PerfilUsuarioAdmin(admin.ModelAdmin):
#     list_display = ['usuario', 'rol', 'telefono', 'activo', 'fecha_creacion']
#     list_filter = ['rol', 'activo', 'fecha_creacion']
#     search_fields = ['usuario__nombreUsuario', 'usuario__nombre', 'usuario__apellidos']
#     readonly_fields = ['fecha_creacion', 'fecha_modificacion']
