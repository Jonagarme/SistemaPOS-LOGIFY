from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date, datetime


class TipoCuenta(models.Model):
    """Tipos de cuentas contables según plan de cuentas"""
    TIPO_CHOICES = [
        ('activo', 'Activo'),
        ('pasivo', 'Pasivo'),
        ('patrimonio', 'Patrimonio'),
        ('ingreso', 'Ingreso'),
        ('gasto', 'Gasto'),
    ]
    
    codigo = models.CharField(max_length=10, unique=True, verbose_name='Código')
    nombre = models.CharField(max_length=100, verbose_name='Nombre')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    
    class Meta:
        verbose_name = 'Tipo de Cuenta'
        verbose_name_plural = 'Tipos de Cuentas'
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class CuentaContable(models.Model):
    """Plan de cuentas contables"""
    codigo = models.CharField(max_length=20, unique=True, verbose_name='Código de Cuenta')
    nombre = models.CharField(max_length=150, verbose_name='Nombre de la Cuenta')
    tipo_cuenta = models.ForeignKey(TipoCuenta, on_delete=models.PROTECT, verbose_name='Tipo de Cuenta')
    cuenta_padre = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, verbose_name='Cuenta Padre')
    nivel = models.IntegerField(default=1, verbose_name='Nivel')
    acepta_movimiento = models.BooleanField(default=True, verbose_name='Acepta Movimiento')
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Saldo Inicial')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Cuenta Contable'
        verbose_name_plural = 'Cuentas Contables'
        ordering = ['codigo']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    @property
    def saldo_actual(self):
        """Calcular saldo actual basado en movimientos"""
        from django.db.models import Sum
        
        debe = self.movimientos_debe.aggregate(total=Sum('monto'))['total'] or Decimal('0')
        haber = self.movimientos_haber.aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        if self.tipo_cuenta.tipo in ['activo', 'gasto']:
            return self.saldo_inicial + debe - haber
        else:  # pasivo, patrimonio, ingreso
            return self.saldo_inicial + haber - debe


class AsientoContable(models.Model):
    """Asientos contables del sistema"""
    TIPO_CHOICES = [
        ('manual', 'Manual'),
        ('automatico', 'Automático'),
        ('cierre', 'Cierre'),
        ('apertura', 'Apertura'),
    ]
    
    numero = models.CharField(max_length=20, unique=True, verbose_name='Número de Asiento')
    fecha = models.DateField(verbose_name='Fecha')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='manual', verbose_name='Tipo')
    concepto = models.CharField(max_length=255, verbose_name='Concepto')
    referencia = models.CharField(max_length=100, blank=True, verbose_name='Referencia')
    total_debe = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Total Debe')
    total_haber = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Total Haber')
    cuadrado = models.BooleanField(default=False, verbose_name='Cuadrado')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuario')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Asiento Contable'
        verbose_name_plural = 'Asientos Contables'
        ordering = ['-fecha', '-numero']
    
    def __str__(self):
        return f"Asiento {self.numero} - {self.fecha}"
    
    def save(self, *args, **kwargs):
        if not self.numero:
            self.numero = self.generar_numero()
        super().save(*args, **kwargs)
    
    def generar_numero(self):
        """Generar número de asiento automático"""
        ultimo = AsientoContable.objects.filter(
            fecha__year=self.fecha.year
        ).order_by('-numero').first()
        
        if ultimo:
            ultimo_num = int(ultimo.numero.split('-')[-1])
            nuevo_num = ultimo_num + 1
        else:
            nuevo_num = 1
        
        return f"ASI-{self.fecha.year}-{nuevo_num:06d}"


class MovimientoContable(models.Model):
    """Movimientos individuales de cada asiento"""
    asiento = models.ForeignKey(AsientoContable, on_delete=models.CASCADE, related_name='movimientos')
    cuenta = models.ForeignKey(CuentaContable, on_delete=models.PROTECT, verbose_name='Cuenta')
    debe = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Debe')
    haber = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Haber')
    concepto = models.CharField(max_length=255, verbose_name='Concepto')
    
    class Meta:
        verbose_name = 'Movimiento Contable'
        verbose_name_plural = 'Movimientos Contables'
    
    def __str__(self):
        return f"{self.cuenta.codigo} - {self.concepto}"


class CuentaPorCobrar(models.Model):
    """Gestión de cuentas por cobrar"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('parcial', 'Pago Parcial'),
        ('pagada', 'Pagada'),
        ('vencida', 'Vencida'),
        ('incobrable', 'Incobrable'),
    ]
    
    numero = models.CharField(max_length=20, unique=True, verbose_name='Número')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, verbose_name='Cliente')
    factura_relacionada = models.ForeignKey('ventas.Venta', on_delete=models.PROTECT, null=True, blank=True)
    fecha_emision = models.DateField(verbose_name='Fecha de Emisión')
    fecha_vencimiento = models.DateField(verbose_name='Fecha de Vencimiento')
    monto_original = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto Original')
    monto_pendiente = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto Pendiente')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name='Estado')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    usuario_creacion = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Creado por')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Cuenta por Cobrar'
        verbose_name_plural = 'Cuentas por Cobrar'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"CxC {self.numero} - {self.cliente.nombres}"
    
    @property
    def dias_vencimiento(self):
        """Días desde vencimiento (negativo si no ha vencido)"""
        return (date.today() - self.fecha_vencimiento).days
    
    @property
    def monto_pagado(self):
        """Monto total pagado"""
        return self.monto_original - self.monto_pendiente


class PagoCuentaPorCobrar(models.Model):
    """Pagos realizados a cuentas por cobrar"""
    cuenta_cobrar = models.ForeignKey(CuentaPorCobrar, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateField(verbose_name='Fecha de Pago')
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    forma_pago = models.CharField(max_length=50, verbose_name='Forma de Pago')
    referencia = models.CharField(max_length=100, blank=True, verbose_name='Referencia')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuario')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Pago de Cuenta por Cobrar'
        verbose_name_plural = 'Pagos de Cuentas por Cobrar'
        ordering = ['-fecha_pago']


class CuentaPorPagar(models.Model):
    """Gestión de cuentas por pagar"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('parcial', 'Pago Parcial'),
        ('pagada', 'Pagada'),
        ('vencida', 'Vencida'),
    ]
    
    numero = models.CharField(max_length=20, unique=True, verbose_name='Número')
    proveedor = models.ForeignKey('proveedores.Proveedor', on_delete=models.PROTECT, verbose_name='Proveedor')
    factura_proveedor = models.CharField(max_length=50, verbose_name='Factura Proveedor')
    fecha_emision = models.DateField(verbose_name='Fecha de Emisión')
    fecha_vencimiento = models.DateField(verbose_name='Fecha de Vencimiento')
    monto_original = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto Original')
    monto_pendiente = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Monto Pendiente')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name='Estado')
    categoria_gasto = models.CharField(max_length=100, verbose_name='Categoría de Gasto')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    usuario_creacion = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Creado por')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Cuenta por Pagar'
        verbose_name_plural = 'Cuentas por Pagar'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"CxP {self.numero} - {self.proveedor.nombres}"


class PagoCuentaPorPagar(models.Model):
    """Pagos realizados a cuentas por pagar"""
    cuenta_pagar = models.ForeignKey(CuentaPorPagar, on_delete=models.CASCADE, related_name='pagos')
    fecha_pago = models.DateField(verbose_name='Fecha de Pago')
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    forma_pago = models.CharField(max_length=50, verbose_name='Forma de Pago')
    referencia = models.CharField(max_length=100, blank=True, verbose_name='Referencia')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuario')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Pago de Cuenta por Pagar'
        verbose_name_plural = 'Pagos de Cuentas por Pagar'
        ordering = ['-fecha_pago']


class CuentaBancaria(models.Model):
    """Cuentas bancarias de la empresa"""
    TIPO_CHOICES = [
        ('ahorro', 'Ahorro'),
        ('corriente', 'Corriente'),
        ('inversion', 'Inversión'),
    ]
    
    nombre = models.CharField(max_length=100, verbose_name='Nombre de la Cuenta')
    banco = models.CharField(max_length=100, verbose_name='Banco')
    numero_cuenta = models.CharField(max_length=50, unique=True, verbose_name='Número de Cuenta')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    saldo_inicial = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Saldo Inicial')
    fecha_apertura = models.DateField(verbose_name='Fecha de Apertura')
    activa = models.BooleanField(default=True, verbose_name='Activa')
    cuenta_contable = models.ForeignKey(CuentaContable, on_delete=models.PROTECT, verbose_name='Cuenta Contable')
    
    class Meta:
        verbose_name = 'Cuenta Bancaria'
        verbose_name_plural = 'Cuentas Bancarias'
        ordering = ['banco', 'nombre']
    
    def __str__(self):
        return f"{self.banco} - {self.nombre}"
    
    @property
    def saldo_actual(self):
        """Calcular saldo actual basado en movimientos"""
        from django.db.models import Sum
        
        ingresos = self.movimientos.filter(tipo='ingreso').aggregate(total=Sum('monto'))['total'] or Decimal('0')
        egresos = self.movimientos.filter(tipo='egreso').aggregate(total=Sum('monto'))['total'] or Decimal('0')
        
        return self.saldo_inicial + ingresos - egresos


class MovimientoBancario(models.Model):
    """Movimientos de cuentas bancarias"""
    TIPO_CHOICES = [
        ('ingreso', 'Ingreso'),
        ('egreso', 'Egreso'),
    ]
    
    cuenta_bancaria = models.ForeignKey(CuentaBancaria, on_delete=models.CASCADE, related_name='movimientos')
    fecha = models.DateField(verbose_name='Fecha')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name='Tipo')
    monto = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    concepto = models.CharField(max_length=255, verbose_name='Concepto')
    referencia = models.CharField(max_length=100, blank=True, verbose_name='Referencia')
    conciliado = models.BooleanField(default=False, verbose_name='Conciliado')
    asiento_contable = models.ForeignKey(AsientoContable, on_delete=models.SET_NULL, null=True, blank=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuario')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Movimiento Bancario'
        verbose_name_plural = 'Movimientos Bancarios'
        ordering = ['-fecha', '-fecha_creacion']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.concepto} - ${self.monto}"


class CategoriaGasto(models.Model):
    """Categorías para clasificar gastos"""
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    cuenta_contable = models.ForeignKey(CuentaContable, on_delete=models.PROTECT, verbose_name='Cuenta Contable')
    presupuesto_mensual = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name='Presupuesto Mensual')
    activa = models.BooleanField(default=True, verbose_name='Activa')
    
    class Meta:
        verbose_name = 'Categoría de Gasto'
        verbose_name_plural = 'Categorías de Gastos'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Gasto(models.Model):
    """Control de gastos de la empresa"""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente Aprobación'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
        ('pagado', 'Pagado'),
    ]
    
    numero = models.CharField(max_length=20, unique=True, verbose_name='Número')
    fecha = models.DateField(verbose_name='Fecha')
    categoria = models.ForeignKey(CategoriaGasto, on_delete=models.PROTECT, verbose_name='Categoría')
    proveedor = models.ForeignKey('proveedores.Proveedor', on_delete=models.PROTECT, null=True, blank=True, verbose_name='Proveedor')
    concepto = models.CharField(max_length=255, verbose_name='Concepto')
    monto = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente', verbose_name='Estado')
    factura_numero = models.CharField(max_length=50, blank=True, verbose_name='Número de Factura')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    cuenta_pagar = models.ForeignKey(CuentaPorPagar, on_delete=models.SET_NULL, null=True, blank=True)
    usuario_solicita = models.ForeignKey(User, on_delete=models.PROTECT, related_name='gastos_solicitados')
    usuario_aprueba = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name='gastos_aprobados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Gasto {self.numero} - {self.concepto}"


class FlujoCaja(models.Model):
    """Proyección de flujo de caja"""
    fecha = models.DateField(verbose_name='Fecha')
    concepto = models.CharField(max_length=255, verbose_name='Concepto')
    ingreso_proyectado = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Ingreso Proyectado')
    egreso_proyectado = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Egreso Proyectado')
    ingreso_real = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Ingreso Real')
    egreso_real = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name='Egreso Real')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name='Usuario')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Flujo de Caja'
        verbose_name_plural = 'Flujos de Caja'
        ordering = ['fecha']
        unique_together = ['fecha', 'concepto']
    
    def __str__(self):
        return f"Flujo {self.fecha} - {self.concepto}"
    
    @property
    def flujo_proyectado(self):
        return self.ingreso_proyectado - self.egreso_proyectado
    
    @property
    def flujo_real(self):
        return self.ingreso_real - self.egreso_real
    
    @property
    def variacion(self):
        return self.flujo_real - self.flujo_proyectado
