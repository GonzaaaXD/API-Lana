import schedule
import time
from datetime import datetime, date
import threading
from sqlalchemy.orm import Session
from DB.conexion import SessionLocal
from Services.email_service import (
    enviar_notificaciones_pagos_programados, 
    enviar_notificaciones_alertas_presupuestos, 
    enviar_resumen_semanal_presupuestos
)
from models.modelsDB import Usuario, PagoProgramado, Transaccion
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging compatible con Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('notifications.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class NotificationScheduler:
    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        
    def ejecutar_notificaciones_diarias(self):
        """Ejecuta el envío de notificaciones diarias"""
        try:
            logging.info("Iniciando envío de notificaciones diarias...")
            
            db: Session = SessionLocal()
            try:
                # Enviar notificaciones con diferentes días de anticipación
                resultado = enviar_notificaciones_pagos_programados(
                    db=db, 
                    dias_anticipacion=[7, 3, 1, 0]  # 7 días, 3 días, 1 día y hoy
                )
                
                logging.info(f"Notificaciones completadas: {resultado['enviados']} enviados, {resultado['errores']} errores")
                
            finally:
                db.close()
                
        except Exception as e:
            logging.error(f"Error en notificaciones diarias: {e}")
    
    def ejecutar_notificaciones_urgentes(self):
        """Ejecuta notificaciones para pagos que vencen HOY"""
        try:
            logging.info("Iniciando notificaciones urgentes (pagos de hoy)...")
            
            db: Session = SessionLocal()
            try:
                resultado = enviar_notificaciones_pagos_programados(
                    db=db, 
                    dias_anticipacion=[0]  # Solo pagos de hoy
                )
                
                if resultado['total'] > 0:
                    logging.warning(f"URGENTE: {resultado['total']} pagos vencen HOY")
                else:
                    logging.info("No hay pagos urgentes para hoy")
                    
            finally:
                db.close()
                
        except Exception as e:
            logging.error(f"Error en notificaciones urgentes: {e}")
    
    # Modificar la función ejecutar_verificacion_presupuestos
    def ejecutar_verificacion_presupuestos(self):
        """Ejecuta verificación y notificación de alertas de presupuestos"""
        try:
            logging.info("Iniciando verificación de presupuestos...")
            
            db: Session = SessionLocal()
            try:
                # Obtener todos los usuarios activos
                usuarios = db.query(Usuario).filter(Usuario.activo == True).all()
                
                total_alertas = 0
                notificaciones_enviadas = 0
                
                for usuario in usuarios:
                    try:
                        # Verificar alertas con notificaciones
                        resultado = verificar_alertas_con_notificacion(db, usuario.id)
                        
                        if resultado["tiene_alertas_criticas"]:
                            logging.warning(f"⚠️ Usuario {usuario.nombre} tiene alertas críticas")
                            total_alertas += len(resultado["alertas"])
                            notificaciones_enviadas += resultado["notificaciones_enviadas"]
                        
                    except Exception as e:
                        logging.error(f"Error procesando usuario {usuario.nombre}: {e}")
                        continue
                
                logging.info(f"Verificación completada: {total_alertas} alertas, {notificaciones_enviadas} notificaciones enviadas")
                return {
                    "total_usuarios": len(usuarios),
                    "total_alertas": total_alertas,
                    "notificaciones_enviadas": notificaciones_enviadas
                }
                        
            finally:
                db.close()
                
        except Exception as e:
            logging.error(f"Error en verificación de presupuestos: {e}")
            return {
                "error": str(e),
                "total_usuarios": 0,
                "total_alertas": 0,
                "notificaciones_enviadas": 0
            }

    def ejecutar_resumen_presupuestos_semanal(self):
        """Envía resumen semanal de presupuestos a todos los usuarios"""
        try:
            logging.info("Iniciando resumen semanal de presupuestos...")
            
            db: Session = SessionLocal()
            try:
                # Obtener todos los usuarios activos
                usuarios = db.query(Usuario).all()
                
                enviados = 0
                errores = 0
                
                for usuario in usuarios:
                    try:
                        exito = enviar_resumen_semanal_presupuestos(db, usuario.id)
                        if exito:
                            enviados += 1
                            logging.info(f"Resumen semanal enviado a: {usuario.nombre}")
                        else:
                            errores += 1
                            logging.error(f"Error enviando resumen a: {usuario.nombre}")
                    except Exception as e:
                        errores += 1
                        logging.error(f"Error procesando usuario {usuario.nombre}: {e}")
                
                logging.info(f"Resúmenes semanales completados: {enviados} enviados, {errores} errores")
                    
            finally:
                db.close()
                
        except Exception as e:
            logging.error(f"Error en resumen semanal de presupuestos: {e}")

    def ejecutar_resumen_semanal(self):
        """Envía un resumen semanal de pagos pendientes (funcionalidad futura)"""
        try:
            logging.info("Ejecutando resumen semanal de pagos...")
            # Aquí puedes implementar lógica adicional para resúmenes semanales
            # Por ejemplo: estadísticas de gastos, pagos completados, etc.
            
        except Exception as e:
            logging.error(f"Error en resumen semanal: {e}")
    
    def ejecutar_notificaciones_ahora(self):
        """Ejecuta pagos programados y crea transacciones automáticas."""
        db: Session = SessionLocal()
        try:
            hoy = date.today()
            pagos = db.query(PagoProgramado).filter(
                PagoProgramado.fecha <= hoy,
                PagoProgramado.estado == "pendiente"
            ).all()

            if not pagos:
                logger.info("No hay pagos programados pendientes para hoy.")
                return True

            for pago in pagos:
                # 1️⃣ Marcar pago como completado
                pago.estado = "pagado"

                # 2️⃣ Crear transacción automáticamente
                nueva_transaccion = Transaccion(
                    monto=pago.monto,
                    tipo="gasto",
                    fecha=hoy,
                    descripcion=f"Pago programado: {pago.nombre}",
                    usuario_id=pago.usuario_id,
                    categoria_id=pago.categoria_id
                )
                db.add(nueva_transaccion)

                logger.info(f"Pago '{pago.nombre}' ejecutado y registrado como transacción.")

            db.commit()
            return True

        except Exception as e:
            logger.error(f"Error ejecutando notificaciones: {e}")
            db.rollback()
            return False
        finally:
            db.close()

    def ejecutar_verificacion_presupuesto_usuario(self, usuario_id: int):
        """Ejecuta verificación de presupuesto para un usuario específico (útil para API)"""
        try:
            logging.info(f"Verificando presupuesto para usuario {usuario_id}...")
            
            db: Session = SessionLocal()
            try:
                resultado = enviar_notificaciones_alertas_presupuestos(db=db, usuario_id=usuario_id)
                
                if resultado['total'] > 0:
                    logging.info(f"Usuario {usuario_id} - Alertas: {resultado['enviados']} enviadas, {resultado['errores']} errores")
                    return resultado
                else:
                    logging.info(f"Usuario {usuario_id} - Sin alertas de presupuesto")
                    return {"enviados": 0, "errores": 0, "total": 0}
                    
            finally:
                db.close()
                
        except Exception as e:
            logging.error(f"Error verificando presupuesto usuario {usuario_id}: {e}")
            return {"enviados": 0, "errores": 1, "total": 0}
    
    def programar_tareas(self):
        """Programa todas las tareas de notificación"""
        
        # ✅ NOTIFICACIONES DE PAGOS (existentes)
        # Notificaciones diarias a las 9:00 AM
        schedule.every().day.at("09:00").do(self.ejecutar_notificaciones_diarias)
        
        # Notificaciones urgentes múltiples veces al día para pagos que vencen HOY
        schedule.every().day.at("08:00").do(self.ejecutar_notificaciones_urgentes)  # Mañana
        schedule.every().day.at("14:00").do(self.ejecutar_notificaciones_urgentes)  # Tarde  
        schedule.every().day.at("19:00").do(self.ejecutar_notificaciones_urgentes)  # Noche
        
        # ✅ NUEVAS NOTIFICACIONES DE PRESUPUESTOS
        # Verificación de presupuestos 2 veces al día
        schedule.every().day.at("12:00").do(self.ejecutar_verificacion_presupuestos)  # Mediodía
        schedule.every().day.at("20:00").do(self.ejecutar_verificacion_presupuestos)  # Noche
        
        # Resumen semanal de presupuestos (Domingos)
        schedule.every().sunday.at("18:00").do(self.ejecutar_resumen_presupuestos_semanal)
        
        # Resumen semanal de pagos (Lunes) - existente
        schedule.every().monday.at("10:00").do(self.ejecutar_resumen_semanal)
        
        logging.info("Tareas de notificación programadas:")
        logging.info("   📅 PAGOS:")
        logging.info("     - Notificaciones diarias: 9:00 AM")
        logging.info("     - Notificaciones urgentes: 8:00 AM, 2:00 PM, 7:00 PM")
        logging.info("     - Resumen semanal: Lunes 10:00 AM")
        logging.info("   💰 PRESUPUESTOS:")
        logging.info("     - Verificación de alertas: 12:00 PM, 8:00 PM")
        logging.info("     - Resumen semanal: Domingos 6:00 PM")
    
    def _run_scheduler(self):
        """Función interna que ejecuta el scheduler en el hilo"""
        logging.info("Scheduler de notificaciones iniciado")
        
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Revisar cada minuto
            
        logging.info("Scheduler de notificaciones detenido")
    
    def iniciar(self):
        """Inicia el scheduler en un hilo separado"""
        if not self.is_running:
            self.is_running = True
            self.programar_tareas()
            
            # Ejecutar en hilo separado para no bloquear la aplicación
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            
            logging.info("Scheduler de notificaciones iniciado exitosamente")
        else:
            logging.warning("El scheduler ya está ejecutándose")
    
    def detener(self):
        """Detiene el scheduler"""
        if self.is_running:
            self.is_running = False
            schedule.clear()  # Limpiar todas las tareas programadas
            
            if self.scheduler_thread:
                self.scheduler_thread.join()
                
            logging.info("Scheduler de notificaciones detenido")
        else:
            logging.warning("El scheduler no estaba ejecutándose")
    
    def obtener_estado(self):
        """Obtiene el estado actual del scheduler incluyendo estadísticas"""
        try:
            proxima_ejecucion = schedule.next_run() if schedule.jobs else None
            
            # Obtener información adicional de las tareas
            tareas_info = []
            for job in schedule.jobs:
                tareas_info.append({
                    "funcion": job.job_func.__name__ if hasattr(job.job_func, '__name__') else str(job.job_func),
                    "proxima_ejecucion": job.next_run,
                    "intervalo": str(job.interval)
                })
            
            return {
                "ejecutandose": self.is_running,
                "tareas_programadas": len(schedule.jobs),
                "proxima_ejecucion": proxima_ejecucion,
                "tareas_detalle": tareas_info,
                "tipos_notificacion": {
                    "pagos": True,
                    "presupuestos": True,
                    "resumenes_semanales": True
                }
            }
        except Exception as e:
            logging.error(f"Error obteniendo estado del scheduler: {e}")
            return {
                "ejecutandose": self.is_running,
                "tareas_programadas": 0,
                "error": str(e)
            }

# Instancia global del scheduler
notification_scheduler = NotificationScheduler()

def inicializar_scheduler():
    """Función para inicializar el scheduler desde main.py"""
    try:
        notification_scheduler.iniciar()
        return True
    except Exception as e:
        logging.error(f"Error inicializando scheduler: {e}")
        return False

def detener_scheduler():
    """Función para detener el scheduler"""
    notification_scheduler.detener()

def ejecutar_notificaciones_ahora():
    """Función pública para ejecutar notificaciones inmediatamente"""
    return notification_scheduler.ejecutar_notificaciones_ahora()

def verificar_presupuestos_ahora(usuario_id: int = None):
    """
    Función para verificar presupuestos inmediatamente desde la API
    Si usuario_id es None, verifica todos los usuarios
    """
    try:
        db: Session = SessionLocal()
        try:
            resultado = enviar_notificaciones_alertas_presupuestos(db=db, usuario_id=usuario_id)
            logging.info(f"Verificación manual de presupuestos ejecutada: {resultado}")
            return resultado
        finally:
            db.close()
    except Exception as e:
        logging.error(f"Error en verificación manual de presupuestos: {e}")
        return {"enviados": 0, "errores": 1, "total": 0}

def enviar_resumen_presupuesto_usuario(usuario_id: int):
    """Envía resumen de presupuesto a un usuario específico"""
    try:
        db: Session = SessionLocal()
        try:
            resultado = enviar_resumen_semanal_presupuestos(db, usuario_id)
            if resultado:
                logging.info(f"Resumen de presupuesto enviado al usuario {usuario_id}")
            else:
                logging.error(f"Error enviando resumen al usuario {usuario_id}")
            return resultado
        finally:
            db.close()
    except Exception as e:
        logging.error(f"Error enviando resumen a usuario {usuario_id}: {e}")
        return False

def test_notificaciones_presupuesto():
    """Función de prueba para verificar que las notificaciones de presupuesto funcionen"""
    try:
        print("🧪 Probando notificaciones de presupuesto...")
        resultado = verificar_presupuestos_ahora()
        print(f"✅ Resultado de prueba: {resultado}")
        return resultado
    except Exception as e:
        print(f"❌ Error en prueba de notificaciones: {e}")
        return False

def obtener_estado_scheduler():
    """Función pública para obtener el estado del scheduler"""
    return notification_scheduler.obtener_estado()

# Función para uso en desarrollo/testing
if __name__ == "__main__":
    print("Modo de prueba del Notification Scheduler")
    print("Iniciando scheduler...")
    
    # Iniciar scheduler
    notification_scheduler.iniciar()
    
    try:
        print("Scheduler ejecutándose. Presiona Ctrl+C para detener.")
        
        # Ejecutar notificaciones de prueba
        print("\n🧪 Ejecutando notificaciones de prueba...")
        
        # Probar pagos programados
        print("📅 Probando notificaciones de pagos...")
        ejecutar_notificaciones_ahora()
        
        # Probar presupuestos
        print("💰 Probando notificaciones de presupuestos...")
        test_notificaciones_presupuesto()
        
        print("\n✅ Pruebas completadas. El scheduler sigue ejecutándose...")
        
        # Mantener el programa ejecutándose
        while True:
            time.sleep(10)  # Revisar cada 10 segundos en modo de prueba
            
    except KeyboardInterrupt:
        print("\nDeteniendo scheduler...")
        notification_scheduler.detener()
        print("Scheduler detenido exitosamente")