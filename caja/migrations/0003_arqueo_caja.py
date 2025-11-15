# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('caja', '0002_caja_ubicacion'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS arqueos_caja (
                id BIGINT PRIMARY KEY AUTO_INCREMENT,
                idCierreCaja BIGINT NOT NULL,
                -- Billetes
                billete_100 INT DEFAULT 0,
                billete_50 INT DEFAULT 0,
                billete_20 INT DEFAULT 0,
                billete_10 INT DEFAULT 0,
                billete_5 INT DEFAULT 0,
                -- Monedas
                moneda_1 INT DEFAULT 0,
                moneda_050 INT DEFAULT 0,
                moneda_025 INT DEFAULT 0,
                moneda_010 INT DEFAULT 0,
                moneda_005 INT DEFAULT 0,
                moneda_001 INT DEFAULT 0,
                -- Totales calculados
                total_billetes DECIMAL(12, 4) DEFAULT 0,
                total_monedas DECIMAL(12, 4) DEFAULT 0,
                total_general DECIMAL(12, 4) DEFAULT 0,
                -- Notas adicionales
                notas_arqueo TEXT,
                -- Auditoría
                creadoPor INT,
                creadoDate DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_idCierreCaja (idCierreCaja)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """,
            reverse_sql="DROP TABLE IF EXISTS arqueos_caja;"
        ),
    ]
