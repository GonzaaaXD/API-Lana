from sqlalchemy.orm import Session
from models.modelsDB import PagoProgramado, Usuario, Categoria
from modelsPyDantic import PagoProgramadoCreate
from Services.email_service import enviar_correo_confirmacion_pago_creado
import logging

# Configurar logging
logger = logging.getLogger(__name__)

def crear_pago(db: Session, pago: PagoProgramadoCreate, usuario_id: int):
    """Crea un pago programado y envía correo de confirmación"""
    
    # Crear el pago en la base de datos
    db_pago = PagoProgramado(**pago.dict(), usuario_id=usuario_id)
    db.add(db_pago)
    db.commit()
    db.refresh(db_pago)
    
    try:
        # Obtener datos necesarios para el correo
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        categoria = None
        if hasattr(db_pago, 'categoria_id') and db_pago.categoria_id:
            categoria = db.query(Categoria).filter(Categoria.id == db_pago.categoria_id).first()
        
        # Enviar correo de confirmación
        if usuario:
            exito_correo = enviar_correo_confirmacion_pago_creado(usuario, db_pago, categoria)
            if exito_correo:
                logger.info(f"Correo de confirmación enviado para pago: {db_pago.nombre} - Usuario: {usuario.nombre}")
            else:
                logger.warning(f"Error enviando correo de confirmación para pago: {db_pago.nombre} - Usuario: {usuario.nombre}")
        else:
            logger.error(f"Usuario no encontrado para enviar confirmación de pago: {db_pago.nombre}")
            
    except Exception as e:
        # No fallar la creación del pago si hay error en el correo
        logger.error(f"Error enviando correo de confirmación para pago {db_pago.nombre}: {e}")
    
    return db_pago

def obtener_pagos(db: Session, usuario_id: int):
    return db.query(PagoProgramado).filter(PagoProgramado.usuario_id == usuario_id).all()

def obtener_pago(db: Session, pago_id: int):
    return db.query(PagoProgramado).filter(PagoProgramado.id == pago_id).first()

def actualizar_pago(db: Session, pago_id: int, pago: PagoProgramadoCreate):
    db_pago = obtener_pago(db, pago_id)
    if not db_pago:
        return None
    
    for key, value in pago.dict().items():
        setattr(db_pago, key, value)
    
    db.commit()
    db.refresh(db_pago)
    return db_pago

def eliminar_pago(db: Session, pago_id: int):
    db_pago = obtener_pago(db, pago_id)
    if not db_pago:
        return False
    
    db.delete(db_pago)
    db.commit()
    return True

def verificar_saldo(db: Session, usuario_id: int):
    # Implementar lógica de verificación de saldo
    return {"disponible": True}