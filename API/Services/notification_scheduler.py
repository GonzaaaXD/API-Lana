import schedule
import time
from datetime import datetime
import threading
from sqlalchemy.orm import Session
from DB.conexion import SessionLocal
from Services.email_service import enviar_notificaciones_pagos_programados
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
    
    def programar_tareas(self):
        """Programa todas las tareas de notificación"""
        
        # Notificaciones diarias a las 9:00 AM
        schedule.every().day.at("09:00").do(self.ejecutar_notificaciones_diarias)
        
        # Notificaciones urgentes múltiples veces al día para pagos que vencen HOY
        schedule.every().day.at("08:00").do(self.ejecutar_notificaciones_urgentes)  # Mañana
        schedule.every().day.at("14:00").do(self.ejecutar_notificaciones_urgentes)  # Tarde
        schedule.every().day.at("19:00").do(self.ejecutar_notificaciones_urgentes)  # Noche
        
        # Notificación semanal de resumen (opcional)
        schedule.every().monday.at("10:00").do(self.ejecutar_resumen_semanal)
        
        logging.info("Tareas de notificación programadas:")
        logging.info("   - Notificaciones diarias: 9:00 AM")
        logging.info("   - Notificaciones urgentes: 8:00 AM, 2:00 PM, 7:00 PM")
        logging.info("   - Resumen semanal: Lunes 10:00 AM")
    
    def ejecutar_resumen_semanal(self):
        """Envía un resumen semanal de pagos pendientes (funcionalidad futura)"""
        try:
            logging.info("Ejecutando resumen semanal...")
            # Aquí puedes implementar lógica adicional para resúmenes semanales
            # Por ejemplo: estadísticas de gastos, pagos completados, etc.
            
        except Exception as e:
            logging.error(f"Error en resumen semanal: {e}")
    
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
        """Obtiene el estado actual del scheduler"""
        return {
            "ejecutandose": self.is_running,
            "tareas_programadas": len(schedule.jobs),
            "proxima_ejecucion": schedule.next_run() if schedule.jobs else None
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
    """Ejecuta las notificaciones inmediatamente (útil para testing)"""
    try:
        logging.info("Ejecutando notificaciones manualmente...")
        notification_scheduler.ejecutar_notificaciones_diarias()
        return True
    except Exception as e:
        logging.error(f"Error ejecutando notificaciones manuales: {e}")
        return False

# Función para uso en desarrollo/testing
if __name__ == "__main__":
    print("Modo de prueba del Notification Scheduler")
    print("Iniciando scheduler...")
    
    # Iniciar scheduler
    notification_scheduler.iniciar()
    
    try:
        print("Scheduler ejecutándose. Presiona Ctrl+C para detener.")
        
        # También ejecutar notificaciones inmediatamente para prueba
        print("Ejecutando notificaciones de prueba...")
        ejecutar_notificaciones_ahora()
        
        # Mantener el programa ejecutándose
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nDeteniendo scheduler...")
        notification_scheduler.detener()
        print("Scheduler detenido exitosamente")