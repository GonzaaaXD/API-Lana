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
    
# Modificar la función verificar_alertas_con_notificacion
def verificar_alertas_con_notificacion(db: Session, usuario_id: int, enviar_email: bool = True):
    """
    Verificar alertas de presupuestos y opcionalmente enviar notificaciones por correo
    """
    try:
        print(f"🚨 Verificando alertas con notificación para usuario {usuario_id}")
        
        # Obtener alertas usando la función existente
        alertas = verificar_alertas(db, usuario_id)
        
        if not alertas:
            print("✅ No hay alertas para este usuario")
            return {
                "alertas": [],
                "notificaciones_enviadas": 0,
                "tiene_alertas_criticas": False
            }
        
        # Filtrar alertas para envío por correo (ahora incluye informativas)
        alertas_para_notificar = [a for a in alertas if a['tipo'] in ['excedido', 'cerca_limite', 'informativo']]
        
        resultado_notificaciones = {
            "alertas": alertas,
            "notificaciones_enviadas": 0,
            "tiene_alertas_criticas": len([a for a in alertas if a['tipo'] in ['excedido', 'cerca_limite']]) > 0
        }
        
        # Enviar notificaciones por correo si es necesario
        if enviar_email and alertas_para_notificar:
            try:
                from Services.email_service import enviar_notificaciones_alertas_presupuestos
                
                # Obtener usuario para el correo
                usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
                if not usuario:
                    print("❌ Usuario no encontrado para enviar notificación")
                    return resultado_notificaciones
                
                resultado_email = enviar_notificaciones_alertas_presupuestos(
                    db=db,
                    usuario_id=usuario_id,
                    alertas=alertas_para_notificar  # Pasar las alertas específicas
                )
                
                resultado_notificaciones["notificaciones_enviadas"] = resultado_email.get("enviados", 0)
                
                print(f"📧 Notificaciones enviadas: {resultado_notificaciones['notificaciones_enviadas']}")
                
            except Exception as e:
                print(f"❌ Error enviando notificaciones por correo: {e}")
                import traceback
                traceback.print_exc()
        
        return resultado_notificaciones
        
    except Exception as e:
        print(f"❌ Error en verificar_alertas_con_notificacion: {str(e)}")
        return {
            "alertas": [],
            "notificaciones_enviadas": 0,
            "tiene_alertas_criticas": False,
            "error": str(e)
        }
    
def crear_presupuesto_con_verificacion(db: Session, presupuesto: PresupuestoCreate, usuario_id: int, verificar_alertas_existentes: bool = True):
    """
    Crear presupuesto y opcionalmente verificar alertas de presupuestos existentes
    """
    try:
        print(f"🔄 Creando presupuesto con verificación para usuario {usuario_id}")
        
        # Crear el presupuesto usando la función existente
        nuevo_presupuesto = crear_presupuesto(db, presupuesto, usuario_id)
        
        resultado = {
            "presupuesto": nuevo_presupuesto,
            "alertas_verificadas": False,
            "alertas_encontradas": []
        }
        
        # Verificar alertas de todos los presupuestos del usuario si se solicita
        if verificar_alertas_existentes:
            try:
                alertas_resultado = verificar_alertas_con_notificacion(db, usuario_id, enviar_email=False)
                resultado["alertas_verificadas"] = True
                resultado["alertas_encontradas"] = alertas_resultado.get("alertas", [])
                
                # Log informativo
                if alertas_resultado["tiene_alertas_criticas"]:
                    print(f"⚠️ Usuario {usuario_id} tiene {len(alertas_resultado['alertas'])} alertas después de crear presupuesto")
                
            except Exception as e:
                print(f"❌ Error verificando alertas después de crear presupuesto: {e}")
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error en crear_presupuesto_con_verificacion: {str(e)}")
        raise

def obtener_dashboard_presupuestos(db: Session, usuario_id: int):
    """
    Obtener dashboard completo de presupuestos con alertas y estadísticas
    """
    try:
        print(f"📊 Generando dashboard de presupuestos para usuario {usuario_id}")
        
        hoy = date.today()
        
        # Obtener presupuestos del mes actual
        presupuestos_actuales = db.query(PresupuestoDB).filter(
            PresupuestoDB.usuario_id == usuario_id,
            PresupuestoDB.mes == hoy.month,
            PresupuestoDB.año == hoy.year
        ).all()
        
        # Obtener alertas
        alertas = verificar_alertas(db, usuario_id)
        
        # Calcular estadísticas generales
        total_presupuestado = sum(float(p.monto) for p in presupuestos_actuales)
        
        # Calcular total gastado en todas las categorías con presupuesto
        total_gastado = 0
        for presupuesto in presupuestos_actuales:
            primer_dia = date(presupuesto.año, presupuesto.mes, 1)
            ultimo_dia_mes = monthrange(presupuesto.año, presupuesto.mes)[1]
            ultimo_dia = date(presupuesto.año, presupuesto.mes, ultimo_dia_mes)
            
            gasto_categoria = db.query(func.sum(Transaccion.monto)).filter(
                and_(
                    Transaccion.usuario_id == usuario_id,
                    Transaccion.categoria_id == presupuesto.categoria_id,
                    Transaccion.tipo == "egreso",
                    Transaccion.fecha >= primer_dia,
                    Transaccion.fecha <= ultimo_dia
                )
            ).scalar() or 0
            
            total_gastado += float(gasto_categoria)
        
        # Preparar datos de presupuestos con detalles
        presupuestos_detalle = []
        for presupuesto in presupuestos_actuales:
            categoria = db.query(Categoria).filter(Categoria.id == presupuesto.categoria_id).first()
            
            # Buscar alerta correspondiente
            alerta_presupuesto = None
            for alerta in alertas:
                if alerta.get('presupuesto_id') == presupuesto.id:
                    alerta_presupuesto = alerta
                    break
            
            presupuestos_detalle.append({
                "id": presupuesto.id,
                "categoria_id": presupuesto.categoria_id,
                "categoria_nombre": categoria.nombre if categoria else f"Categoría {presupuesto.categoria_id}",
                "monto": float(presupuesto.monto),
                "mes": presupuesto.mes,
                "año": presupuesto.año,
                "gasto_actual": alerta_presupuesto.get('gasto_actual', 0) if alerta_presupuesto else 0,
                "porcentaje_usado": alerta_presupuesto.get('porcentaje', 0) if alerta_presupuesto else 0,
                "estado": alerta_presupuesto.get('tipo', 'normal') if alerta_presupuesto else 'normal',
                "tiene_alerta": alerta_presupuesto is not None
            })
        
        # Estadísticas de alertas
        alertas_por_tipo = {
            "excedido": len([a for a in alertas if a['tipo'] == 'excedido']),
            "cerca_limite": len([a for a in alertas if a['tipo'] == 'cerca_limite']),
            "informativo": len([a for a in alertas if a['tipo'] == 'informativo']),
            "normal": len(presupuestos_actuales) - len(alertas)
        }
        
        dashboard = {
            "resumen": {
                "total_presupuestado": total_presupuestado,
                "total_gastado": total_gastado,
                "porcentaje_general": (total_gastado / total_presupuestado * 100) if total_presupuestado > 0 else 0,
                "disponible": total_presupuestado - total_gastado,
                "mes_actual": hoy.month,
                "año_actual": hoy.year
            },
            "presupuestos": presupuestos_detalle,
            "alertas": alertas,
            "estadisticas_alertas": alertas_por_tipo,
            "tiene_alertas_criticas": any(a['tipo'] in ['excedido', 'cerca_limite'] for a in alertas)
        }
        
        print(f"✅ Dashboard generado: {len(presupuestos_detalle)} presupuestos, {len(alertas)} alertas")
        return dashboard
        
    except Exception as e:
        print(f"❌ Error generando dashboard de presupuestos: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def programar_verificacion_automatica(db: Session, usuario_id: int):
    """
    Programa verificación automática de presupuestos para un usuario específico
    (Esta función se puede llamar desde tu API cuando un usuario actualiza una transacción)
    """
    try:
        print(f"⏰ Programando verificación automática para usuario {usuario_id}")
        
        # Verificar inmediatamente
        resultado = verificar_alertas_con_notificacion(db, usuario_id, enviar_email=True)
        
        # Aquí podrías agregar lógica adicional como:
        # - Registrar en logs específicos
        # - Enviar a sistema de colas si usas uno
        # - Actualizar métricas de usuario
        
        return {
            "verificacion_ejecutada": True,
            "alertas_encontradas": len(resultado.get("alertas", [])),
            "notificaciones_enviadas": resultado.get("notificaciones_enviadas", 0),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error en verificación automática: {str(e)}")
        return {
            "verificacion_ejecutada": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# ✅ FUNCIÓN PARA USAR EN TUS ENDPOINTS DE API
def manejar_transaccion_con_verificacion_presupuesto(db: Session, transaccion_data, usuario_id: int):
    """
    Función auxiliar para usar cuando creates/actualices transacciones desde tu API
    """
    try:
        # Aquí agregarías tu lógica existente para crear/actualizar transacciones
        # ... tu código de transacciones ...
        
        # Después de la transacción, verificar si afecta algún presupuesto
        if hasattr(transaccion_data, 'tipo') and transaccion_data.tipo == "egreso":
            print(f"💸 Transacción de egreso detectada, verificando presupuestos...")
            
            # Verificar alertas y enviar notificaciones si es necesario
            resultado_verificacion = verificar_alertas_con_notificacion(
                db, 
                usuario_id, 
                enviar_email=True
            )
            
            return {
                "transaccion_procesada": True,
                "verificacion_presupuesto": resultado_verificacion,
                "recomendacion": "Revisa tus presupuestos" if resultado_verificacion["tiene_alertas_criticas"] else "Presupuestos bajo control"
            }
        
        return {
            "transaccion_procesada": True,
            "verificacion_presupuesto": {"alertas": [], "notificaciones_enviadas": 0},
            "recomendacion": "Transacción registrada exitosamente"
        }
        
    except Exception as e:
        print(f"❌ Error manejando transacción con verificación: {str(e)}")
        raise