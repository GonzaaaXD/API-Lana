from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, and_  # ✅ AGREGAR and_
from datetime import date
from calendar import monthrange  # ✅ AGREGAR ESTE IMPORT
from DB.conexion import get_db
from models.modelsDB import Presupuesto as PresupuestoDB, Transaccion
from modelsPyDantic import Presupuesto, PresupuestoCreate
from Services.presupuestos_service import (
    crear_presupuesto,
    obtener_presupuestos,
    obtener_presupuesto,
    actualizar_presupuesto,
    eliminar_presupuesto,
    verificar_alertas
)
from Services.auth_service import obtener_usuario

router = APIRouter(prefix="/presupuestos", tags=["Presupuestos"])

@router.post("/", response_model=Presupuesto)
def crear_presupuesto_endpoint(
    presupuesto: PresupuestoCreate,
    usuario_id: int,
    db: Session = Depends(get_db)
):
    usuario = obtener_usuario(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    return crear_presupuesto(db, presupuesto, usuario_id)

@router.get("/", response_model=list[Presupuesto])
def listar_presupuestos(usuario_id: int, db: Session = Depends(get_db)):
    return obtener_presupuestos(db, usuario_id)

@router.get("/{presupuesto_id}", response_model=Presupuesto)
def obtener_presupuesto_endpoint(presupuesto_id: int, db: Session = Depends(get_db)):
    presupuesto = obtener_presupuesto(db, presupuesto_id)
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return presupuesto

# ✅ RUTA PRINCIPAL QUE FALTABA - LA QUE LLAMA TU APP
@router.get("/usuario/{usuario_id}")
def obtener_presupuestos_con_gastos(usuario_id: int, db: Session = Depends(get_db)):
    """
    ✅ OBTENER PRESUPUESTOS CON GASTOS ACTUALES CALCULADOS CORRECTAMENTE
    """
    try:
        hoy = date.today()
        print(f"🔍 Calculando gastos para usuario {usuario_id} - Fecha actual: {hoy}")
        
        # Obtener todos los presupuestos del usuario para el mes/año actual
        presupuestos = db.query(PresupuestoDB).filter(
            PresupuestoDB.usuario_id == usuario_id,
            PresupuestoDB.mes == hoy.month,
            PresupuestoDB.año == hoy.year
        ).all()
        
        print(f"📊 Presupuestos encontrados: {len(presupuestos)}")
        
        if not presupuestos:
            print("⚠️ No se encontraron presupuestos para el mes actual")
            return []
        
        resultado = []
        
        for p in presupuestos:
            print(f"💰 Calculando gastos para presupuesto {p.id} - Categoría {p.categoria_id}")
            
            # ✅ CALCULAR FECHAS CORRECTAS DEL MES
            primer_dia = date(p.año, p.mes, 1)
            ultimo_dia_mes = monthrange(p.año, p.mes)[1]  # Obtener último día del mes
            ultimo_dia = date(p.año, p.mes, ultimo_dia_mes)
            
            print(f"📅 Rango de fechas: {primer_dia} a {ultimo_dia}")
            
            # ✅ CONSULTA CORREGIDA - USAR "egreso" EN LUGAR DE "gasto"
            gasto_total = db.query(func.sum(Transaccion.monto)).filter(
                and_(
                    Transaccion.usuario_id == usuario_id,
                    Transaccion.categoria_id == p.categoria_id,
                    Transaccion.tipo == "egreso",  # ✅ CAMBIAR A "egreso"
                    Transaccion.fecha >= primer_dia,
                    Transaccion.fecha <= ultimo_dia
                )
            ).scalar() or 0
            
            print(f"💸 Gasto total calculado: ${gasto_total}")
            
            # ✅ CALCULAR RESTANTE
            restante = float(p.monto) - float(gasto_total)
            
            resultado_item = {
                "presupuesto_id": p.id,
                "categoria_id": p.categoria_id,
                "monto_presupuesto": float(p.monto),
                "gasto_actual": float(gasto_total),
                "restante": restante,
                "mes": p.mes,
                "año": p.año,
                "porcentaje_usado": (float(gasto_total) / float(p.monto) * 100) if p.monto > 0 else 0,
                "excedido": restante < 0
            }
            
            print(f"✅ Resultado para presupuesto {p.id}: {resultado_item}")
            resultado.append(resultado_item)
        
        print(f"🎯 Total resultados: {len(resultado)}")
        return resultado
        
    except Exception as e:
        print(f"❌ Error en obtener_presupuestos_con_gastos: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error calculando gastos: {str(e)}")

# 🔍 FUNCIÓN DE DEBUG TEMPORAL
@router.get("/debug/{usuario_id}")
def debug_presupuestos_gastos(usuario_id: int, db: Session = Depends(get_db)):
    """
    🔍 FUNCIÓN DE DEBUG PARA ENCONTRAR EL PROBLEMA
    """
    try:
        hoy = date.today()
        print(f"🔍 DEBUG - Usuario: {usuario_id}, Fecha actual: {hoy}")
        
        # 1. Verificar presupuestos
        presupuestos = db.query(PresupuestoDB).filter(
            PresupuestoDB.usuario_id == usuario_id
        ).all()
        
        print(f"📊 Total presupuestos del usuario: {len(presupuestos)}")
        presupuestos_info = []
        
        for p in presupuestos:
            print(f"💰 Presupuesto {p.id}: Categoría {p.categoria_id}, ${p.monto}, {p.mes}/{p.año}")
            presupuestos_info.append({
                "id": p.id,
                "categoria_id": p.categoria_id,
                "monto": float(p.monto),
                "mes": p.mes,
                "año": p.año
            })
        
        # 2. Verificar TODAS las transacciones del usuario
        todas_transacciones = db.query(Transaccion).filter(
            Transaccion.usuario_id == usuario_id
        ).all()
        
        print(f"💸 Total transacciones del usuario: {len(todas_transacciones)}")
        transacciones_info = []
        
        for t in todas_transacciones:
            print(f"💳 Transacción {t.id}: Categoría {t.categoria_id}, ${t.monto}, {t.tipo}, {t.fecha}")
            transacciones_info.append({
                "id": t.id,
                "categoria_id": t.categoria_id,
                "monto": float(t.monto),
                "tipo": t.tipo,
                "fecha": t.fecha.isoformat(),
                "descripcion": t.descripcion,
                "mes": t.fecha.month,
                "año": t.fecha.year
            })
        
        # 3. Verificar transacciones de cada presupuesto
        detalles_calculo = []
        
        for p in presupuestos:
            # Calcular fechas del mes del presupuesto
            primer_dia = date(p.año, p.mes, 1)
            ultimo_dia_mes = monthrange(p.año, p.mes)[1]
            ultimo_dia = date(p.año, p.mes, ultimo_dia_mes)
            
            print(f"\n🔍 Calculando para presupuesto {p.id}:")
            print(f"   📅 Rango: {primer_dia} a {ultimo_dia}")
            print(f"   🏷️ Categoría: {p.categoria_id}")
            
            # Buscar transacciones que coincidan
            transacciones_coincidentes = db.query(Transaccion).filter(
                and_(
                    Transaccion.usuario_id == usuario_id,
                    Transaccion.categoria_id == p.categoria_id,
                    Transaccion.tipo == "egreso",  # ✅ USAR "egreso"
                    Transaccion.fecha >= primer_dia,
                    Transaccion.fecha <= ultimo_dia
                )
            ).all()
            
            print(f"   💳 Transacciones coincidentes: {len(transacciones_coincidentes)}")
            
            gasto_total = 0
            transacciones_detalle = []
            
            for t in transacciones_coincidentes:
                print(f"      - ID {t.id}: ${t.monto} en {t.fecha}")
                gasto_total += float(t.monto)
                transacciones_detalle.append({
                    "id": t.id,
                    "monto": float(t.monto),
                    "fecha": t.fecha.isoformat(),
                    "descripcion": t.descripcion
                })
            
            print(f"   💰 Total gastado: ${gasto_total}")
            
            detalles_calculo.append({
                "presupuesto_id": p.id,
                "categoria_id": p.categoria_id,
                "monto_presupuesto": float(p.monto),
                "mes": p.mes,
                "año": p.año,
                "periodo": {
                    "inicio": primer_dia.isoformat(),
                    "fin": ultimo_dia.isoformat()
                },
                "gasto_calculado": gasto_total,
                "transacciones_encontradas": len(transacciones_coincidentes),
                "transacciones_detalle": transacciones_detalle
            })
        
        return {
            "fecha_actual": hoy.isoformat(),
            "usuario_id": usuario_id,
            "presupuestos": presupuestos_info,
            "todas_transacciones": transacciones_info,
            "calculos_detallados": detalles_calculo,
            "posibles_problemas": [
                "¿La transacción tiene categoria_id diferente al presupuesto?",
                "¿La transacción es tipo 'gasto' o 'egreso'?",
                "¿La fecha de la transacción está en el mes/año del presupuesto?",
                "¿Los nombres de las columnas en la BD coinciden?",
                "¿La transacción se guardó correctamente?"
            ]
        }
        
    except Exception as e:
        print(f"❌ Error en debug: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error en debug: {str(e)}")

@router.put("/{presupuesto_id}", response_model=Presupuesto)
def actualizar_presupuesto_endpoint(
    presupuesto_id: int,
    presupuesto: PresupuestoCreate,
    db: Session = Depends(get_db)
):
    db_presupuesto = actualizar_presupuesto(db, presupuesto_id, presupuesto)
    if not db_presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return db_presupuesto

@router.delete("/{presupuesto_id}")
def eliminar_presupuesto_endpoint(presupuesto_id: int, db: Session = Depends(get_db)):
    if not eliminar_presupuesto(db, presupuesto_id):
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return {"mensaje": "Presupuesto eliminado"}

# ✅ RUTA DE ALERTAS CORREGIDA
@router.get("/alertas/")
def obtener_alertas(usuario_id: int, db: Session = Depends(get_db)):
    try:
        print(f"🚨 Obteniendo alertas para usuario {usuario_id}")
        alertas = verificar_alertas(db, usuario_id)
        print(f"✅ Alertas obtenidas: {len(alertas) if alertas else 0}")
        return alertas or []
    except Exception as e:
        print(f"❌ Error obteniendo alertas: {str(e)}")
        import traceback
        traceback.print_exc()
        # No fallar por alertas, devolver lista vacía
        return []

# ✅ NUEVA RUTA: Obtener presupuestos de cualquier mes/año
@router.get("/usuario/{usuario_id}/{año}/{mes}")
def obtener_presupuestos_mes_especifico(
    usuario_id: int, 
    año: int, 
    mes: int, 
    db: Session = Depends(get_db)
):
    """
    Obtener presupuestos con gastos para un mes/año específico
    """
    try:
        print(f"🔍 Calculando gastos para usuario {usuario_id} - {mes}/{año}")
        
        # Validar mes y año
        if mes < 1 or mes > 12:
            raise HTTPException(status_code=400, detail="Mes inválido")
        if año < 2020 or año > 2030:
            raise HTTPException(status_code=400, detail="Año inválido")
        
        presupuestos = db.query(PresupuestoDB).filter(
            PresupuestoDB.usuario_id == usuario_id,
            PresupuestoDB.mes == mes,
            PresupuestoDB.año == año
        ).all()
        
        if not presupuestos:
            return []
        
        resultado = []
        
        for p in presupuestos:
            # Calcular fechas del mes específico
            primer_dia = date(año, mes, 1)
            ultimo_dia_mes = monthrange(año, mes)[1]
            ultimo_dia = date(año, mes, ultimo_dia_mes)
            
            # Calcular gastos del mes específico
            gasto_total = db.query(func.sum(Transaccion.monto)).filter(
                and_(
                    Transaccion.usuario_id == usuario_id,
                    Transaccion.categoria_id == p.categoria_id,
                    Transaccion.tipo == "egreso",  # ✅ CAMBIAR A "egreso"
                    Transaccion.fecha >= primer_dia,
                    Transaccion.fecha <= ultimo_dia
                )
            ).scalar() or 0
            
            restante = float(p.monto) - float(gasto_total)
            
            resultado.append({
                "presupuesto_id": p.id,
                "categoria_id": p.categoria_id,
                "monto_presupuesto": float(p.monto),
                "gasto_actual": float(gasto_total),
                "restante": restante,
                "mes": mes,
                "año": año,
                "porcentaje_usado": (float(gasto_total) / float(p.monto) * 100) if p.monto > 0 else 0,
                "excedido": restante < 0
            })
        
        return resultado
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error calculando gastos: {str(e)}")