from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("--- 🛠️  REPARANDO ESTRUCTURA DE BASE DE DATOS ---")

    # Lista de columnas que DEBEN existir
    columnas_nuevas = [
        """INSERT INTO cost_centers (code, name, description, status, budget, owner_id) VALUES
        ('CP22-041','READECUACIONES ELÉCTRICAS',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-001','INCREMENTO DE POTENCIA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-015','INCREMENTO DE POTENCIA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-043','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-045','INCREMENTO DE POTENCIA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-066','HYTERA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-067','RANCO BATCH1',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-073','FEN-LIMA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-074','READECUACIÓN DE ENERGÍA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-075','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-078','READECUACIÓN DE ENERGIA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-083','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-084','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP23-085','PROYECTO FEN',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-000','EPP Y HERRAMIENTAS',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-001','MATERIAL ELECTRICO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-004','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-005','HYTERA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-007','ADECUACIONES',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-008','COBERTURA APT 2024',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-009','ENERGÍA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-010','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-011','APT',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-012','AMPLIACIÓN DE POTENCIA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-013','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-014','HYETRA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-015','AMPLIACIÓN DE POTENCIA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-016','PROYECTO 5G',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-017','AMPLIACIÒN DE POTENCIA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-019','MANTENIMIENTO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-020','MANTENIMIENTO DE TORRE',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-022','REFARMING',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-023','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-026','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-027','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-028','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-029','RANCO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-030','REFARMING',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-032','REGULATORIO 3.5',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-036','PROYECTO FETRASA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-037','REACTIVOS REFARMING 2.3 2024',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-039','RANKO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-040','APT ENERGÌA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-041','RANKO FASE 2',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-042','ADECUACIÒN DE ENERGÌA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-043','SANTA CHIMBOTE',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-044','APT BATCH I REGIONES',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-045','MORRO SOLAR ATM',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-048','PROYECTO 5G',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-049','PROYECTO 5G',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-050','APT - BATCH 2 LIMA Y REGIONES',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-051','RANCO FASE 2',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-053','RANCO FASE 2',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-054','PROYECTO ANTAMINA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-055','SITES NO ASIGNADOS',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-057','RED TETRA - HYTERA',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-058','REFORZAMIENTO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-062','MANT. DE TORRE/INST. DE SOPOR.',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b'),
('CP24-064','PREVENTIVO',NULL,'Activo',1000,'auth0|6901006f37c4763e6941d83b')

"""
    ]

    for sql in columnas_nuevas:
        try:
            db.session.execute(text(sql))
            print(f"✅ Ejecutado: {sql}")
        except Exception as e:
            err_msg = str(e).lower()
            # Si el error es que la columna ya existe, es buena noticia, lo ignoramos
            if "duplicate column" in err_msg or "already exists" in err_msg:
                print(f"⚠️  Saltando (La columna ya existe): {sql.split('ADD COLUMN')[1]}")
            else:
                print(f"❌ Error real: {e}")

    try:
        db.session.commit()
        print("\n✨ ¡LISTO! Tu base de datos y tu código ahora están sincronizados.")
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar cambios: {e}")