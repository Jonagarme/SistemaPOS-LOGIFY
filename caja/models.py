from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal


class Caja(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    activa = models.BooleanField(default=True)
    # Nueva columna para asociar caja con ubicación/sucursal
    # Requiere agregar la columna en MySQL: ALTER TABLE cajas ADD COLUMN idUbicacion INT NULL;
    ubicacion = models.ForeignKey('inventario.Ubicacion', on_delete=models.PROTECT, 
                                   null=True, blank=True, db_column='idUbicacion',
                                   related_name='cajas')
    
    class Meta:
        db_table = 'cajas'
        managed = False
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class ArqueoCaja(models.Model):
    """Modelo para el detalle del arqueo físico de caja"""
    idCierreCaja = models.IntegerField(db_column='idCierreCaja')
    
    # Billetes
    billete_100 = models.IntegerField(default=0, db_column='billete_100')
    billete_50 = models.IntegerField(default=0, db_column='billete_50')
    billete_20 = models.IntegerField(default=0, db_column='billete_20')
    billete_10 = models.IntegerField(default=0, db_column='billete_10')
    billete_5 = models.IntegerField(default=0, db_column='billete_5')
    
    # Monedas
    moneda_1 = models.IntegerField(default=0, db_column='moneda_1')
    moneda_050 = models.IntegerField(default=0, db_column='moneda_050')
    moneda_025 = models.IntegerField(default=0, db_column='moneda_025')
    moneda_010 = models.IntegerField(default=0, db_column='moneda_010')
    moneda_005 = models.IntegerField(default=0, db_column='moneda_005')
    moneda_001 = models.IntegerField(default=0, db_column='moneda_001')
    
    # Totales
    total_billetes = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='total_billetes')
    total_monedas = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='total_monedas')
    total_general = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='total_general')
    
    # Notas
    notas_arqueo = models.TextField(null=True, blank=True, db_column='notas_arqueo')
    
    # Auditoría
    creadoPor = models.IntegerField(db_column='creadoPor')
    creadoDate = models.DateTimeField(auto_now_add=True, db_column='creadoDate')
    
    class Meta:
        db_table = 'arqueos_caja'
        managed = False
        verbose_name = "Arqueo de Caja"
        verbose_name_plural = "Arqueos de Caja"
    
    def __str__(self):
        return f"Arqueo - Cierre #{self.idCierreCaja} - ${self.total_general}"
    
    def calcular_totales(self):
        """Calcula los totales de billetes y monedas"""
        self.total_billetes = (
            Decimal(self.billete_100) * Decimal('100') +
            Decimal(self.billete_50) * Decimal('50') +
            Decimal(self.billete_20) * Decimal('20') +
            Decimal(self.billete_10) * Decimal('10') +
            Decimal(self.billete_5) * Decimal('5')
        )
        
        self.total_monedas = (
            Decimal(self.moneda_1) * Decimal('1') +
            Decimal(self.moneda_050) * Decimal('0.50') +
            Decimal(self.moneda_025) * Decimal('0.25') +
            Decimal(self.moneda_010) * Decimal('0.10') +
            Decimal(self.moneda_005) * Decimal('0.05') +
            Decimal(self.moneda_001) * Decimal('0.01')
        )
        
        self.total_general = self.total_billetes + self.total_monedas
        return self.total_general


class CierreCaja(models.Model):
    """Modelo para la tabla cierres_caja que maneja tanto aperturas como cierres"""
    ESTADO_CHOICES = [
        ('ABIERTA', 'Abierta'),
        ('CERRADA', 'Cerrada'),
    ]
    
    # Mapear exactamente los nombres de columna de MySQL
    idCaja = models.IntegerField(db_column='idCaja')
    idUsuarioApertura = models.IntegerField(db_column='idUsuarioApertura')
    idUsuarioCierre = models.IntegerField(null=True, blank=True, db_column='idUsuarioCierre')
    fechaApertura = models.DateTimeField(db_column='fechaApertura')
    fechaCierre = models.DateTimeField(null=True, blank=True, db_column='fechaCierre')
    saldoInicial = models.DecimalField(max_digits=12, decimal_places=4, db_column='saldoInicial')
    totalIngresosSistema = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='totalIngresosSistema')
    totalEgresosSistema = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='totalEgresosSistema')
    saldoTeoricoSistema = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='saldoTeoricoSistema')
    totalContadoFisico = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='totalContadoFisico')
    diferencia = models.DecimalField(max_digits=12, decimal_places=4, default=0, db_column='diferencia')
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='ABIERTA', db_column='estado')
    creadoPor = models.IntegerField(db_column='creadoPor')
    creadoDate = models.DateTimeField(db_column='creadoDate')
    anulado = models.BooleanField(default=False, db_column='anulado')
    anuladoPor = models.IntegerField(null=True, blank=True, db_column='anuladoPor')
    anuladoDate = models.DateTimeField(null=True, blank=True, db_column='anuladoDate')
    
    class Meta:
        db_table = 'cierres_caja'
        managed = False
        verbose_name = "Apertura/Cierre de Caja"
        verbose_name_plural = "Aperturas/Cierres de Caja"
        ordering = ['-fechaApertura']
    
    @classmethod
    def obtener_caja_abierta(cls):
        """Obtiene cualquier caja abierta (sin importar el día)"""
        from django.db import connection, OperationalError
        from django.utils import timezone
        
        try:
            # Buscar cualquier caja abierta (sin filtro de fecha)
            caja_abierta = cls.objects.filter(
                estado='ABIERTA',
                anulado=False
            ).order_by('-fechaApertura').first()
            
            if caja_abierta:
                return {
                    'id': caja_abierta.id,
                    'idCaja': caja_abierta.idCaja,
                    'caja_nombre': f'Caja {caja_abierta.idCaja}',
                    'saldoInicial': caja_abierta.saldoInicial,
                    'idUsuarioApertura': caja_abierta.idUsuarioApertura,
                    'fechaApertura': caja_abierta.fechaApertura,
                    'estado': caja_abierta.estado
                }
            
            return None
            
        except OperationalError as e:
            # Re-lanzar OperationalError para que las vistas puedan detectar modo offline
            print(f"Error de conexión al obtener caja abierta: {e}")
            raise
        except Exception as e:
            print(f"Error al obtener caja abierta: {e}")
            return None
    
    def __str__(self):
        return f"Caja {self.idCaja} - {self.fechaApertura.strftime('%d/%m/%Y %H:%M')} - {self.estado}"
    
    @property
    def caja_nombre(self):
        """Obtiene el nombre de la caja desde la tabla cajas"""
        try:
            caja = Caja.objects.get(id=self.idCaja)
            return caja.nombre
        except Caja.DoesNotExist:
            return f"Caja {self.idCaja}"
    
    @property
    def esta_abierta(self):
        return self.estado == 'ABIERTA'


class AperturaCaja(models.Model):
    """Modelo para la tabla aperturascaja adicional (si la usas)"""
    AperturaID = models.AutoField(primary_key=True)
    FechaApertura = models.DateTimeField()
    MontoInicial = models.DecimalField(max_digits=18, decimal_places=2)
    UsuarioApertura = models.CharField(max_length=50)
    Caja = models.CharField(max_length=50)
    FechaCierre = models.DateTimeField(null=True, blank=True)
    MontoFinal = models.DecimalField(max_digits=18, decimal_places=2, null=True, blank=True)
    UsuarioCierre = models.CharField(max_length=50, null=True, blank=True)
    
    class Meta:
        db_table = 'aperturascaja'
        managed = False
        verbose_name = "Apertura de Caja (Legacy)"
        verbose_name_plural = "Aperturas de Caja (Legacy)"
        ordering = ['-FechaApertura']
    
    def __str__(self):
        return f"Apertura {self.AperturaID} - {self.Caja} - {self.FechaApertura.strftime('%d/%m/%Y %H:%M')}"
