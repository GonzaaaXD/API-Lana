from sqlalchemy.orm import Session
from models.modelsDB import PagoProgramado, Transaccion, Usuario, Categoria
from modelsPyDantic import PagoProgramadoCreate, TransaccionCreate
from datetime import datetime
from Services.email_service import enviar_correo_confirmacion_pago_creado
import logging

logger = logging.getLogger(__name__)

class PagosService:
    
    def crear_pago(self, db: Session, pago: PagoProgramadoCreate, usuario_id: int):
        # Crear el pago en la base de datos
        db_pago = PagoProgramado(**pago.dict(), usuario_id=usuario_id)
        db.add(db_pago)
        db.commit()
        db.refresh(db_pago)
        
        # 🔥 ENVIAR CORREO DE CONFIRMACIÓN AUTOMÁTICO
        try:
            # Obtener datos del usuario y categoría para el correo
            usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
            categoria = None
            if db_pago.categoria_id:
                categoria = db.query(Categoria).filter(Categoria.id == db_pago.categoria_id).first()
            
            if usuario and usuario.correo:
                # Enviar correo de confirmación
                correo_enviado = enviar_correo_confirmacion_pago_creado(usuario, db_pago, categoria)
                
                if correo_enviado:
                    logger.info(f"Correo de confirmación enviado a {usuario.correo} para pago '{db_pago.nombre}'")
                else:
                    logger.warning(f"Error enviando correo de confirmación a {usuario.correo} para pago '{db_pago.nombre}'")
            else:
                logger.warning(f"No se pudo enviar correo: usuario no encontrado o sin correo (ID: {usuario_id})")
                
        except Exception as e:
            logger.error(f"Error enviando correo de confirmación para pago '{db_pago.nombre}': {e}")
            # No fallar la creación del pago si el correo falla
        
        return db_pago

    def obtener_pagos(self, db: Session, usuario_id: int):
        return db.query(PagoProgramado).filter(PagoProgramado.usuario_id == usuario_id).all()

    def obtener_pago(self, db: Session, pago_id: int):
        return db.query(PagoProgramado).filter(PagoProgramado.id == pago_id).first()

    def actualizar_pago(self, db: Session, pago_id: int, pago: PagoProgramadoCreate):
        db_pago = self.obtener_pago(db, pago_id)
        if not db_pago:
            return None
        
        # Guardar el estado anterior para verificar cambios
        estado_anterior = db_pago.estado
        
        # Actualizar los campos del pago
        for key, value in pago.dict().items():
            setattr(db_pago, key, value)
        
        # Si el estado cambió de "pendiente" a "pagado", crear transacción
        if estado_anterior == "pendiente" and db_pago.estado == "pagado":
            self.crear_transaccion_desde_pago(db, db_pago)
        
        db.commit()
        db.refresh(db_pago)
        return db_pago

    def marcar_pago_como_pagado(self, db: Session, pago_id: int):
        """
        Función específica para marcar un pago como pagado y crear la transacción automáticamente
        """
        db_pago = self.obtener_pago(db, pago_id)
        if not db_pago:
            return None
        
        if db_pago.estado == "pagado":
            return {"mensaje": "El pago ya estaba marcado como pagado", "pago": db_pago}
        
        # Marcar como pagado
        db_pago.estado = "pagado"
        
        # Crear transacción automáticamente
        transaccion_creada = self.crear_transaccion_desde_pago(db, db_pago)
        
        db.commit()
        db.refresh(db_pago)
        
        return {
            "mensaje": "Pago marcado como pagado y transacción creada",
            "pago": db_pago,
            "transaccion": transaccion_creada
        }

    def crear_transaccion_desde_pago(self, db: Session, pago: PagoProgramado):
        """
        Crea una transacción automáticamente cuando un pago se marca como pagado
        """
        try:
            # Crear la transacción basada en el pago
            nueva_transaccion = Transaccion(
                monto=pago.monto,
                tipo="egreso",  # Los pagos siempre son egresos
                fecha=datetime.now().date(),  # Fecha actual cuando se ejecuta el pago
                descripcion=f"Pago: {pago.nombre}",  # Incluir referencia al pago original
                categoria_id=pago.categoria_id,
                usuario_id=pago.usuario_id
            )
            
            db.add(nueva_transaccion)
            db.flush()  # Para obtener el ID sin hacer commit
            
            return nueva_transaccion
            
        except Exception as e:
            print(f"Error al crear transacción desde pago: {e}")
            db.rollback()
            raise e

    def eliminar_pago(self, db: Session, pago_id: int):
        db_pago = self.obtener_pago(db, pago_id)
        if not db_pago:
            return False
        
        db.delete(db_pago)
        db.commit()
        return True

    def verificar_saldo(self, db: Session, usuario_id: int):
        # Implementar lógica de verificación de saldo
        return {"disponible": True}

    def procesar_pagos_vencidos(self, db: Session):
        """
        Función para procesar automáticamente pagos que ya vencieron
        Útil para ejecutar en un cron job o tarea programada
        """
        try:
            fecha_actual = datetime.now().date()
            
            # Buscar pagos pendientes que ya vencieron
            pagos_vencidos = db.query(PagoProgramado).filter(
                PagoProgramado.estado == "pendiente",
                PagoProgramado.fecha <= fecha_actual
            ).all()
            
            pagos_procesados = []
            
            for pago in pagos_vencidos:
                # Marcar como pagado y crear transacción
                pago.estado = "pagado"
                transaccion = self.crear_transaccion_desde_pago(db, pago)
                
                pagos_procesados.append({
                    "pago_id": pago.id,
                    "nombre": pago.nombre,
                    "monto": pago.monto,
                    "transaccion_id": transaccion.id
                })
            
            db.commit()
            
            return {
                "procesados": len(pagos_procesados),
                "detalles": pagos_procesados
            }
            
        except Exception as e:
            db.rollback()
            print(f"Error al procesar pagos vencidos: {e}")
            return {"error": str(e)}

    def obtener_pagos_pendientes(self, db: Session, usuario_id: int):
        """
        Obtiene solo los pagos pendientes del usuario
        """
        return db.query(PagoProgramado).filter(
            PagoProgramado.usuario_id == usuario_id,
            PagoProgramado.estado == "pendiente"
        ).all()

    def obtener_pagos_pagados(self, db: Session, usuario_id: int):
        """
        Obtiene solo los pagos ya pagados del usuario
        """
        return db.query(PagoProgramado).filter(
            PagoProgramado.usuario_id == usuario_id,
            PagoProgramado.estado == "pagado"
        ).all()

# Crear una instancia del servicio para exportar
pagos_service = PagosService()