from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from DB.conexion import get_db
from modelsPyDantic import PagoProgramado, PagoProgramadoCreate
from Services.pagos_service import (
    crear_pago,
    obtener_pagos,
    obtener_pago,
    actualizar_pago,
    eliminar_pago,
    verificar_saldo
)
from Services.auth_service import obtener_usuario
import logging

# Configurar logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pagos", tags=["Pagos"])

@router.post("/", response_model=PagoProgramado)
def crear_pago_endpoint(
    pago: PagoProgramadoCreate,
    usuario_id: int,
    db: Session = Depends(get_db)
):
    """Crea un pago programado y envía correo de confirmación automáticamente"""
    
    # Verificar que el usuario existe
    usuario = obtener_usuario(db, usuario_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    try:
        # Crear el pago (incluye envío automático de correo de confirmación)
        pago_creado = crear_pago(db, pago, usuario_id)
        
        logger.info(f"Pago programado creado exitosamente: {pago_creado.nombre} para usuario {usuario.nombre}")
        
        return pago_creado
        
    except Exception as e:
        logger.error(f"Error creando pago programado para usuario {usuario_id}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error interno al crear el pago programado: {str(e)}"
        )

@router.get("/", response_model=list[PagoProgramado])
def listar_pagos(usuario_id: int, db: Session = Depends(get_db)):
    return obtener_pagos(db, usuario_id)

@router.get("/{pago_id}", response_model=PagoProgramado)
def obtener_pago_endpoint(pago_id: int, db: Session = Depends(get_db)):
    pago = obtener_pago(db, pago_id)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago

@router.put("/{pago_id}", response_model=PagoProgramado)
def actualizar_pago_endpoint(
    pago_id: int,
    pago: PagoProgramadoCreate,
    db: Session = Depends(get_db)
):
    db_pago = actualizar_pago(db, pago_id, pago)
    if not db_pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return db_pago

@router.delete("/{pago_id}")
def eliminar_pago_endpoint(pago_id: int, db: Session = Depends(get_db)):
    if not eliminar_pago(db, pago_id):
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return {"mensaje": "Pago eliminado"}

@router.get("/verificar-saldo/")
def verificar_saldo_endpoint(usuario_id: int, db: Session = Depends(get_db)):
    return verificar_saldo(db, usuario_id)