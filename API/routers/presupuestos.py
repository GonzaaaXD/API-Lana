from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import date, datetime
from calendar import monthrange
from DB.conexion import get_db
from models.modelsDB import Presupuesto as PresupuestoDB, Transaccion
from modelsPyDantic import Presupuesto, PresupuestoCreate
from Services.presupuestos_service import (
    crear_presupuesto,
    obtener_presupuestos,
    obtener_presupuesto,
    actualizar_presupuesto,
    eliminar_presupuesto,
    verificar_alertas,
    # Nuevos servicios recomendados
    verificar_alertas_con_notificacion,
    crear_presupuesto_con_verificacion,
    obtener_dashboard_presupuestos,
    programar_verificacion_automatica
)
from Services.auth_service import obtener_usuario

# ✅ IMPORTAR SERVICIOS DE NOTIFICACIONES (si los tienes implementados)
try:
    from Services.notification_scheduler import (
        verificar_presupuestos_ahora,
        enviar_resumen_presupuesto_usuario
    )
    NOTIFICACIONES_DISPONIBLES = True
except ImportError:
    NOTIFICACIONES_DISPONIBLES = False
    print("⚠️ Servicios de notificaciones no disponibles")

router = APIRouter(prefix="/presupuestos", tags=["Presupuestos"])

# ✅ ENDPOINTS EXISTENTES MANTENIDOS
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

# 🆕 NUEVO: Crear presupuesto con verificación automática de alertas
@router.post("/crear-con-verificacion")
async def crear_presupuesto_con_verificacion_endpoint(
    presupuesto: PresupuestoCreate,
    background_tasks: BackgroundTasks,
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """Crear presupuesto y verificar alertas existentes automáticamente"""
    try:
        # Verificar que el usuario existe
        usuario = obtener_usuario(db, usuario_id)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Crear presupuesto con verificación (si tienes esta función)
        if 'crear_presupuesto_con_verificacion' in globals():
            resultado = crear_presupuesto_con_verificacion(
                db=db, 
                presupuesto=presupuesto, 
                usuario_id=usuario_id,
                verificar_alertas_existentes=True
            )
        else:
            # Fallback: crear presupuesto normal y verificar alertas después
            nuevo_presupuesto = crear_presupuesto(db, presupuesto, usuario_id)
            alertas_encontradas = verificar_alertas(db, usuario_id) or []
            resultado = {
                "presupuesto": nuevo_presupuesto,
                "alertas_encontradas": alertas_encontradas
            }
        
        # Enviar notificación de confirmación en segundo plano
        if resultado.get("presupuesto"):
            background_tasks.add_task(
                enviar_confirmacion_presupuesto_creado,
                db, resultado["presupuesto"], usuario_id
            )
        
        return {
            "message": "Presupuesto creado exitosamente",
            "presupuesto": resultado["presupuesto"],
            "alertas_encontradas": len(resultado.get("alertas_encontradas", [])),
            "tiene_alertas_criticas": any(
                a.get("tipo") in ["excedido", "cerca_limite"] 
                for a in resultado.get("alertas_encontradas", [])
                if isinstance(a, dict)
            )
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=list[Presupuesto])
def listar_presupuestos(usuario_id: int, db: Session = Depends(get_db)):
    return obtener_presupuestos(db, usuario_id)

@router.get("/{presupuesto_id}", response_model=Presupuesto)
def obtener_presupuesto_endpoint(presupuesto_id: int, db: Session = Depends(get_db)):
    presupuesto = obtener_presupuesto(db, presupuesto_id)
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return presupuesto

# ✅ RUTA PRINCIPAL QUE YA TIENES - MANTENIDA
@router.get("/usuario/{usuario_id}")
def obtener_presupuestos_con_gastos(usuario_id: int, db: Session = Depends(get_db)):
    """
    ✅ OBTENER PRESUPUESTOS CON GASTOS ACTUALES CALCULADOS CORRECTAMENTE
    """
    try:
        hoy = date.today()
        print(f"🔍 Calculando gastos para usuario {usuario_id} - Fecha actual: {hoy}")
        
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
            
            primer_dia = date(p.año, p.mes, 1)
            ultimo_dia_mes = monthrange(p.año, p.mes)[1]
            ultimo_dia = date(p.año, p.mes, ultimo_dia_mes)
            
            print(f"📅 Rango de fechas: {primer_dia} a {ultimo_dia}")
            
            gasto_total = db.query(func.sum(Transaccion.monto)).filter(
                and_(
                    Transaccion.usuario_id == usuario_id,
                    Transaccion.categoria_id == p.categoria_id,
                    Transaccion.tipo == "egreso",
                    Transaccion.fecha >= primer_dia,
                    Transaccion.fecha <= ultimo_dia
                )
            ).scalar() or 0
            
            print(f"💸 Gasto total calculado: ${gasto_total}")
            
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

# Modificar la ruta para verificar alertas
@router.get("/alertas/{usuario_id}")
async def obtener_alertas_presupuesto_mejorado(
    usuario_id: int,
    enviar_notificaciones: bool = True,  # Cambiado a True por defecto
    db: Session = Depends(get_db)
):
    """Obtener alertas de presupuesto y opcionalmente enviar notificaciones"""
    try:
        logging.info(f"Verificando alertas para usuario {usuario_id}")
        
        # Verificar que el usuario existe
        usuario = obtener_usuario(db, usuario_id)
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Usar la función mejorada que incluye notificaciones
        resultado = verificar_alertas_con_notificacion(
            db=db,
            usuario_id=usuario_id,
            enviar_email=enviar_notificaciones
        )
        
        return {
            "usuario_id": usuario_id,
            "nombre_usuario": usuario.nombre,
            "total_alertas": len(resultado["alertas"]),
            "alertas_criticas": len([
                a for a in resultado["alertas"] 
                if a.get("tipo") in ["excedido", "cerca_limite"]
            ]),
            "alertas_informativas": len([
                a for a in resultado["alertas"] 
                if a.get("tipo") == "informativo"
            ]),
            "notificaciones_enviadas": resultado.get("notificaciones_enviadas", 0),
            "tiene_alertas_criticas": resultado["tiene_alertas_criticas"],
            "alertas": resultado["alertas"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error obteniendo alertas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo alertas: {str(e)}")

# 🆕 NUEVO: Dashboard completo de presupuestos
@router.get("/dashboard/{usuario_id}")
async def obtener_dashboard_usuario(
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """Obtener dashboard completo con presupuestos, alertas y estadísticas"""
    try:
        # Si tienes la función de dashboard, usarla
        if 'obtener_dashboard_presupuestos' in globals():
            dashboard = obtener_dashboard_presupuestos(db, usuario_id)
        else:
            # Crear dashboard básico usando tus funciones existentes
            presupuestos_con_gastos = obtener_presupuestos_con_gastos(usuario_id, db)
            alertas = verificar_alertas(db, usuario_id) or []
            
            dashboard = {
                "presupuestos": presupuestos_con_gastos,
                "alertas": alertas,
                "tiene_alertas_criticas": any(
                    p.get("excedido", False) for p in presupuestos_con_gastos
                ),
                "resumen": {
                    "total_presupuestos": len(presupuestos_con_gastos),
                    "presupuestos_excedidos": len([
                        p for p in presupuestos_con_gastos if p.get("excedido", False)
                    ]),
                    "gasto_total": sum(p.get("gasto_actual", 0) for p in presupuestos_con_gastos),
                    "presupuesto_total": sum(p.get("monto_presupuesto", 0) for p in presupuestos_con_gastos)
                }
            }
            
            # Calcular porcentaje general
            if dashboard["resumen"]["presupuesto_total"] > 0:
                dashboard["resumen"]["porcentaje_general"] = (
                    dashboard["resumen"]["gasto_total"] / 
                    dashboard["resumen"]["presupuesto_total"] * 100
                )
            else:
                dashboard["resumen"]["porcentaje_general"] = 0
        
        return {
            "usuario_id": usuario_id,
            "dashboard": dashboard,
            "timestamp": datetime.now().isoformat(),
            "recomendaciones": generar_recomendaciones(dashboard)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🆕 NUEVO: Forzar verificación inmediata (útil para testing)
@router.post("/verificar-ahora")
async def verificar_presupuestos_inmediato(
    usuario_id: int = None,
    db: Session = Depends(get_db)
):
    """Forzar verificación inmediata de presupuestos"""
    try:
        if NOTIFICACIONES_DISPONIBLES and 'verificar_presupuestos_ahora' in globals():
            resultado = verificar_presupuestos_ahora(usuario_id)
        else:
            # Fallback: verificar alertas manualmente
            if usuario_id:
                alertas = verificar_alertas(db, usuario_id)
                resultado = {
                    "usuario_id": usuario_id,
                    "alertas_encontradas": len(alertas) if alertas else 0
                }
            else:
                resultado = {"mensaje": "Verificación manual no implementada para todos los usuarios"}
        
        return {
            "message": "Verificación ejecutada",
            "scope": "todos los usuarios" if usuario_id is None else f"usuario {usuario_id}",
            "resultado": resultado
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🆕 NUEVO: Enviar resumen manual
@router.post("/enviar-resumen/{usuario_id}")
async def enviar_resumen_manual(
    usuario_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Enviar resumen de presupuestos manualmente"""
    try:
        if NOTIFICACIONES_DISPONIBLES:
            background_tasks.add_task(
                enviar_resumen_presupuesto_usuario,
                usuario_id
            )
            mensaje = f"Resumen programado para envío al usuario {usuario_id}"
        else:
            # Fallback: generar resumen básico
            background_tasks.add_task(
                generar_resumen_basico,
                db, usuario_id
            )
            mensaje = f"Resumen básico generado para usuario {usuario_id}"
        
        return {
            "message": mensaje,
            "usuario_id": usuario_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 🆕 NUEVO: Integración con transacciones
@router.post("/verificar-tras-transaccion")
async def verificar_tras_crear_transaccion(
    usuario_id: int,
    categoria_id: int,
    tipo_transaccion: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Verificar presupuestos después de crear una transacción"""
    try:
        # Solo verificar si es un egreso
        if tipo_transaccion.lower() == "egreso":
            # Programar verificación en segundo plano
            if 'programar_verificacion_automatica' in globals():
                background_tasks.add_task(
                    programar_verificacion_automatica,
                    db, usuario_id
                )
            else:
                # Fallback: verificar alertas inmediatamente
                background_tasks.add_task(
                    verificar_alertas_tras_transaccion,
                    db, usuario_id, categoria_id
                )
            
            return {
                "message": "Verificación de presupuestos programada",
                "usuario_id": usuario_id,
                "categoria_afectada": categoria_id
            }
        else:
            return {
                "message": "No se requiere verificación para ingresos",
                "usuario_id": usuario_id
            }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ✅ RUTAS EXISTENTES MANTENIDAS
@router.get("/usuario/{usuario_id}/{año}/{mes}")
def obtener_presupuestos_mes_especifico(
    usuario_id: int, 
    año: int, 
    mes: int, 
    db: Session = Depends(get_db)
):
    """Obtener presupuestos con gastos para un mes/año específico"""
    try:
        print(f"🔍 Calculando gastos para usuario {usuario_id} - {mes}/{año}")
        
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
            primer_dia = date(año, mes, 1)
            ultimo_dia_mes = monthrange(año, mes)[1]
            ultimo_dia = date(año, mes, ultimo_dia_mes)
            
            gasto_total = db.query(func.sum(Transaccion.monto)).filter(
                and_(
                    Transaccion.usuario_id == usuario_id,
                    Transaccion.categoria_id == p.categoria_id,
                    Transaccion.tipo == "egreso",
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

# ✅ RUTA DE ALERTAS EXISTENTE MANTENIDA
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
        return []

# 🔍 FUNCIÓN DE DEBUG MANTENIDA
@router.get("/debug/{usuario_id}")
def debug_presupuestos_gastos(usuario_id: int, db: Session = Depends(get_db)):
    """🔍 FUNCIÓN DE DEBUG PARA ENCONTRAR PROBLEMAS"""
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
            primer_dia = date(p.año, p.mes, 1)
            ultimo_dia_mes = monthrange(p.año, p.mes)[1]
            ultimo_dia = date(p.año, p.mes, ultimo_dia_mes)
            
            print(f"\n🔍 Calculando para presupuesto {p.id}:")
            print(f"   📅 Rango: {primer_dia} a {ultimo_dia}")
            print(f"   🏷️ Categoría: {p.categoria_id}")
            
            transacciones_coincidentes = db.query(Transaccion).filter(
                and_(
                    Transaccion.usuario_id == usuario_id,
                    Transaccion.categoria_id == p.categoria_id,
                    Transaccion.tipo == "egreso",
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

# 🆕 NUEVO: Estado del sistema de notificaciones
@router.get("/notificaciones/estado")
async def obtener_estado_notificaciones():
    """Obtener estado del sistema de notificaciones"""
    try:
        if NOTIFICACIONES_DISPONIBLES:
            try:
                from Services.notification_scheduler import notification_scheduler
                estado = notification_scheduler.obtener_estado()
            except:
                estado = {"disponible": True, "detalles": "Servicio básico"}
        else:
            estado = {"disponible": False, "razon": "Servicios no implementados"}
        
        return {
            "sistema_notificaciones": estado,
            "tipos_disponibles": [
                "pagos_programados",
                "alertas_presupuesto", 
                "resumenes_semanales"
            ] if NOTIFICACIONES_DISPONIBLES else [],
            "notificaciones_implementadas": NOTIFICACIONES_DISPONIBLES,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ✅ FUNCIONES AUXILIARES

def generar_recomendaciones(dashboard: dict) -> list:
    """Genera recomendaciones basadas en el estado de los presupuestos"""
    recomendaciones = []
    
    if dashboard.get("tiene_alertas_criticas"):
        recomendaciones.append("🚨 Tienes presupuestos excedidos o cerca del límite")
        recomendaciones.append("📊 Revisa tus gastos recientes y ajusta tus hábitos")
    
    resumen = dashboard.get("resumen", {})
    if resumen.get("porcentaje_general", 0) > 80:
        recomendaciones.append("⚠️ Has usado más del 80% de tus presupuestos totales")
        recomendaciones.append("💡 Considera reducir gastos no esenciales")
    
    if resumen.get("presupuestos_excedidos", 0) > 0:
        recomendaciones.append("🔄 Evalúa ajustar los presupuestos excedidos para el próximo mes")
    
    if len(recomendaciones) == 0:
        recomendaciones.append("✅ ¡Excelente control financiero!")
        recomendaciones.append("📈 Mantén estos buenos hábitos de gasto")
    
    return recomendaciones

async def enviar_confirmacion_presupuesto_creado(db: Session, presupuesto, usuario_id: int):
    """Función auxiliar para enviar confirmación en segundo plano"""
    try:
        # Aquí podrías integrar con tu servicio de email existente
        print(f"📧 Confirmación de presupuesto enviada al usuario {usuario_id}")
        print(f"   💰 Presupuesto: ${presupuesto.monto} para categoría {presupuesto.categoria_id}")
        
        # Si tienes servicio de email, descomenta y adapta:
        # from Services.email_service import enviar_correo_confirmacion_presupuesto
        # usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        # if usuario:
        #     enviar_correo_confirmacion_presupuesto(usuario.correo, presupuesto)
            
    except Exception as e:
        print(f"❌ Error enviando confirmación de presupuesto: {e}")

async def generar_resumen_basico(db: Session, usuario_id: int):
    """Generar resumen básico de presupuestos (fallback cuando no hay servicio de notificaciones)"""
    try:
        print(f"📊 Generando resumen básico para usuario {usuario_id}")
        
        # Obtener datos del usuario
        presupuestos_con_gastos = obtener_presupuestos_con_gastos(usuario_id, db)
        alertas = verificar_alertas(db, usuario_id) or []
        
        resumen = {
            "usuario_id": usuario_id,
            "fecha": datetime.now().isoformat(),
            "total_presupuestos": len(presupuestos_con_gastos),
            "presupuestos_excedidos": len([p for p in presupuestos_con_gastos if p.get("excedido", False)]),
            "total_gastado": sum(p.get("gasto_actual", 0) for p in presupuestos_con_gastos),
            "total_presupuestado": sum(p.get("monto_presupuesto", 0) for p in presupuestos_con_gastos),
            "alertas_activas": len(alertas)
        }
        
        print(f"📧 Resumen generado: {resumen}")
        
        # Aquí podrías enviar por email, guardar en log, etc.
        # Por ahora solo lo loggeamos
        
    except Exception as e:
        print(f"❌ Error generando resumen básico: {e}")

async def verificar_alertas_tras_transaccion(db: Session, usuario_id: int, categoria_id: int):
    """Verificar alertas específicas después de crear una transacción"""
    try:
        print(f"🔍 Verificando alertas tras transacción - Usuario: {usuario_id}, Categoría: {categoria_id}")
        
        # Obtener presupuestos de la categoría afectada para el mes actual
        hoy = date.today()
        presupuestos_afectados = db.query(PresupuestoDB).filter(
            PresupuestoDB.usuario_id == usuario_id,
            PresupuestoDB.categoria_id == categoria_id,
            PresupuestoDB.mes == hoy.month,
            PresupuestoDB.año == hoy.year
        ).all()
        
        alertas_generadas = []
        
        for presupuesto in presupuestos_afectados:
            # Calcular gasto actual
            primer_dia = date(presupuesto.año, presupuesto.mes, 1)
            ultimo_dia_mes = monthrange(presupuesto.año, presupuesto.mes)[1]
            ultimo_dia = date(presupuesto.año, presupuesto.mes, ultimo_dia_mes)
            
            gasto_actual = db.query(func.sum(Transaccion.monto)).filter(
                and_(
                    Transaccion.usuario_id == usuario_id,
                    Transaccion.categoria_id == categoria_id,
                    Transaccion.tipo == "egreso",
                    Transaccion.fecha >= primer_dia,
                    Transaccion.fecha <= ultimo_dia
                )
            ).scalar() or 0
            
            porcentaje_usado = (float(gasto_actual) / float(presupuesto.monto) * 100) if presupuesto.monto > 0 else 0
            
            # Generar alertas según el porcentaje
            if porcentaje_usado >= 100:
                alertas_generadas.append({
                    "tipo": "excedido",
                    "presupuesto_id": presupuesto.id,
                    "categoria_id": categoria_id,
                    "porcentaje": porcentaje_usado,
                    "mensaje": f"🚨 Presupuesto excedido en {porcentaje_usado:.1f}%"
                })
            elif porcentaje_usado >= 80:
                alertas_generadas.append({
                    "tipo": "cerca_limite",
                    "presupuesto_id": presupuesto.id,
                    "categoria_id": categoria_id,
                    "porcentaje": porcentaje_usado,
                    "mensaje": f"⚠️ Cerca del límite: {porcentaje_usado:.1f}% usado"
                })
            elif porcentaje_usado >= 50:
                alertas_generadas.append({
                    "tipo": "medio_camino",
                    "presupuesto_id": presupuesto.id,
                    "categoria_id": categoria_id,
                    "porcentaje": porcentaje_usado,
                    "mensaje": f"📊 {porcentaje_usado:.1f}% del presupuesto usado"
                })
        
        print(f"🚨 Alertas generadas: {len(alertas_generadas)}")
        
        # Aquí podrías enviar notificaciones push, email, etc.
        for alerta in alertas_generadas:
            print(f"   {alerta['mensaje']}")
        
        return alertas_generadas
        
    except Exception as e:
        print(f"❌ Error verificando alertas tras transacción: {e}")
        return []