# Services/presupuestos_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func, and_  # ✅ AGREGAR ESTE IMPORT
from datetime import date, datetime
from calendar import monthrange
from models.modelsDB import Presupuesto as PresupuestoDB, Transaccion, Categoria
from modelsPyDantic import PresupuestoCreate

def crear_presupuesto(db: Session, presupuesto: PresupuestoCreate, usuario_id: int):
    """Crear un nuevo presupuesto"""
    try:
        print(f"🔄 Creando presupuesto para usuario {usuario_id}: {presupuesto.dict()}")
        
        # Verificar si ya existe un presupuesto para la misma categoría/mes/año
        presupuesto_existente = db.query(PresupuestoDB).filter(
            PresupuestoDB.usuario_id == usuario_id,
            PresupuestoDB.categoria_id == presupuesto.categoria_id,
            PresupuestoDB.mes == presupuesto.mes,
            PresupuestoDB.año == presupuesto.año
        ).first()
        
        if presupuesto_existente:
            raise ValueError(f"Ya existe un presupuesto para esta categoría en {presupuesto.mes}/{presupuesto.año}")
        
        db_presupuesto = PresupuestoDB(
            usuario_id=usuario_id,
            categoria_id=presupuesto.categoria_id,
            monto=presupuesto.monto,
            mes=presupuesto.mes,
            año=presupuesto.año
        )
        
        db.add(db_presupuesto)
        db.commit()
        db.refresh(db_presupuesto)
        
        print(f"✅ Presupuesto creado con ID: {db_presupuesto.id}")
        return db_presupuesto
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creando presupuesto: {str(e)}")
        raise

def obtener_presupuestos(db: Session, usuario_id: int):
    """Obtener todos los presupuestos de un usuario"""
    return db.query(PresupuestoDB).filter(PresupuestoDB.usuario_id == usuario_id).all()

def obtener_presupuesto(db: Session, presupuesto_id: int):
    """Obtener un presupuesto específico"""
    return db.query(PresupuestoDB).filter(PresupuestoDB.id == presupuesto_id).first()

def actualizar_presupuesto(db: Session, presupuesto_id: int, presupuesto: PresupuestoCreate):
    """Actualizar un presupuesto existente"""
    try:
        db_presupuesto = db.query(PresupuestoDB).filter(PresupuestoDB.id == presupuesto_id).first()
        
        if not db_presupuesto:
            return None
        
        # Actualizar campos
        db_presupuesto.categoria_id = presupuesto.categoria_id
        db_presupuesto.monto = presupuesto.monto
        db_presupuesto.mes = presupuesto.mes
        db_presupuesto.año = presupuesto.año
        
        db.commit()
        db.refresh(db_presupuesto)
        
        print(f"✅ Presupuesto {presupuesto_id} actualizado")
        return db_presupuesto
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error actualizando presupuesto: {str(e)}")
        raise

def eliminar_presupuesto(db: Session, presupuesto_id: int):
    """Eliminar un presupuesto"""
    try:
        db_presupuesto = db.query(PresupuestoDB).filter(PresupuestoDB.id == presupuesto_id).first()
        
        if not db_presupuesto:
            return False
        
        db.delete(db_presupuesto)
        db.commit()
        
        print(f"✅ Presupuesto {presupuesto_id} eliminado")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error eliminando presupuesto: {str(e)}")
        raise

# ✅ FUNCIÓN DE ALERTAS CORREGIDA
def verificar_alertas(db: Session, usuario_id: int):
    """
    Verificar alertas de presupuestos excedidos o cerca del límite
    """
    try:
        print(f"🚨 Verificando alertas para usuario {usuario_id}")
        
        hoy = date.today()
        alertas = []
        
        # Obtener presupuestos del mes actual
        presupuestos = db.query(PresupuestoDB).filter(
            PresupuestoDB.usuario_id == usuario_id,
            PresupuestoDB.mes == hoy.month,
            PresupuestoDB.año == hoy.year
        ).all()
        
        print(f"📊 Verificando {len(presupuestos)} presupuestos")
        
        for presupuesto in presupuestos:
            # Calcular fechas del mes
            primer_dia = date(presupuesto.año, presupuesto.mes, 1)
            ultimo_dia_mes = monthrange(presupuesto.año, presupuesto.mes)[1]
            ultimo_dia = date(presupuesto.año, presupuesto.mes, ultimo_dia_mes)
            
            # ✅ CALCULAR GASTOS USANDO func CORRECTAMENTE
            gasto_total = db.query(func.sum(Transaccion.monto)).filter(
                and_(
                    Transaccion.usuario_id == usuario_id,
                    Transaccion.categoria_id == presupuesto.categoria_id,
                    Transaccion.tipo == "egreso",  # ✅ USAR "egreso"
                    Transaccion.fecha >= primer_dia,
                    Transaccion.fecha <= ultimo_dia
                )
            ).scalar() or 0
            
            # Obtener nombre de categoría
            categoria = db.query(Categoria).filter(Categoria.id == presupuesto.categoria_id).first()
            nombre_categoria = categoria.nombre if categoria else f"Categoría {presupuesto.categoria_id}"
            
            # Calcular porcentajes
            porcentaje_usado = (float(gasto_total) / float(presupuesto.monto) * 100) if presupuesto.monto > 0 else 0
            
            print(f"💰 {nombre_categoria}: ${gasto_total} / ${presupuesto.monto} ({porcentaje_usado:.1f}%)")
            
            # ✅ GENERAR ALERTAS SEGÚN PORCENTAJE
            if porcentaje_usado >= 100:
                # Presupuesto excedido
                exceso = float(gasto_total) - float(presupuesto.monto)
                alertas.append({
                    "tipo": "excedido",
                    "presupuesto_id": presupuesto.id,
                    "categoria": nombre_categoria,
                    "mensaje": f"⚠️ Presupuesto de {nombre_categoria} excedido por ${exceso:.2f}",
                    "porcentaje": porcentaje_usado,
                    "monto_presupuesto": float(presupuesto.monto),
                    "gasto_actual": float(gasto_total)
                })
            elif porcentaje_usado >= 80:
                # Cerca del límite (80% o más)
                restante = float(presupuesto.monto) - float(gasto_total)
                alertas.append({
                    "tipo": "cerca_limite",
                    "presupuesto_id": presupuesto.id,
                    "categoria": nombre_categoria,
                    "mensaje": f"🔶 {nombre_categoria}: {porcentaje_usado:.1f}% usado. Quedan ${restante:.2f}",
                    "porcentaje": porcentaje_usado,
                    "monto_presupuesto": float(presupuesto.monto),
                    "gasto_actual": float(gasto_total)
                })
            elif porcentaje_usado >= 50:
                # Información - 50% usado
                restante = float(presupuesto.monto) - float(gasto_total)
                alertas.append({
                    "tipo": "informativo",
                    "presupuesto_id": presupuesto.id,
                    "categoria": nombre_categoria,
                    "mensaje": f"ℹ️ {nombre_categoria}: {porcentaje_usado:.1f}% usado. Quedan ${restante:.2f}",
                    "porcentaje": porcentaje_usado,
                    "monto_presupuesto": float(presupuesto.monto),
                    "gasto_actual": float(gasto_total)
                })
        
        print(f"🚨 Alertas generadas: {len(alertas)}")
        for alerta in alertas:
            print(f"   - {alerta['tipo']}: {alerta['mensaje']}")
        
        return alertas
        
    except Exception as e:
        print(f"❌ Error en verificar_alertas: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

# ✅ NUEVA FUNCIÓN: Obtener resumen detallado de un presupuesto
def obtener_resumen_presupuesto(db: Session, presupuesto_id: int):
    """
    Obtener resumen detallado de un presupuesto con todas las transacciones
    """
    try:
        presupuesto = db.query(PresupuestoDB).filter(PresupuestoDB.id == presupuesto_id).first()
        
        if not presupuesto:
            return None
        
        # Calcular fechas
        primer_dia = date(presupuesto.año, presupuesto.mes, 1)
        ultimo_dia_mes = monthrange(presupuesto.año, presupuesto.mes)[1]
        ultimo_dia = date(presupuesto.año, presupuesto.mes, ultimo_dia_mes)
        
        # Obtener todas las transacciones de la categoría en el período
        transacciones = db.query(Transaccion).filter(
            and_(
                Transaccion.usuario_id == presupuesto.usuario_id,
                Transaccion.categoria_id == presupuesto.categoria_id,
                Transaccion.tipo == "egreso",  # ✅ USAR "egreso"
                Transaccion.fecha >= primer_dia,
                Transaccion.fecha <= ultimo_dia
            )
        ).order_by(Transaccion.fecha.desc()).all()
        
        # Calcular total gastado
        gasto_total = sum(float(t.monto) for t in transacciones)
        
        # Obtener categoría
        categoria = db.query(Categoria).filter(Categoria.id == presupuesto.categoria_id).first()
        
        return {
            "presupuesto": {
                "id": presupuesto.id,
                "categoria_id": presupuesto.categoria_id,
                "categoria_nombre": categoria.nombre if categoria else f"Categoría {presupuesto.categoria_id}",
                "monto": float(presupuesto.monto),
                "mes": presupuesto.mes,
                "año": presupuesto.año
            },
            "gastos": {
                "total": gasto_total,
                "restante": float(presupuesto.monto) - gasto_total,
                "porcentaje_usado": (gasto_total / float(presupuesto.monto) * 100) if presupuesto.monto > 0 else 0,
                "excedido": gasto_total > float(presupuesto.monto)
            },
            "transacciones": [
                {
                    "id": t.id,
                    "descripcion": t.descripcion,
                    "monto": float(t.monto),
                    "fecha": t.fecha.isoformat(),
                    "tipo": t.tipo
                } for t in transacciones
            ],
            "periodo": {
                "inicio": primer_dia.isoformat(),
                "fin": ultimo_dia.isoformat()
            }
        }
        
    except Exception as e:
        print(f"❌ Error obteniendo resumen: {str(e)}")
        raise