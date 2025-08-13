from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from DB.conexion import get_db
from modelsPyDantic import PagoProgramado, PagoProgramadoCreate
from Services.pagos_service import pagos_service  # Solo esta importación
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
        pago_creado = pagos_service.crear_pago(db, pago, usuario_id)  # ✅ Usar pagos_service
        
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
    return pagos_service.obtener_pagos(db, usuario_id)  # ✅ Usar pagos_service

@router.get("/{pago_id}", response_model=PagoProgramado)
def obtener_pago_endpoint(pago_id: int, db: Session = Depends(get_db)):
    pago = pagos_service.obtener_pago(db, pago_id)  # ✅ Usar pagos_service
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return pago

@router.put("/{pago_id}", response_model=PagoProgramado)
def actualizar_pago_endpoint(
    pago_id: int,
    pago: PagoProgramadoCreate,
    db: Session = Depends(get_db)
):
    db_pago = pagos_service.actualizar_pago(db, pago_id, pago)  # ✅ Usar pagos_service
    if not db_pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return db_pago

@router.delete("/{pago_id}")
def eliminar_pago_endpoint(pago_id: int, db: Session = Depends(get_db)):
    if not pagos_service.eliminar_pago(db, pago_id):  # ✅ Usar pagos_service
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return {"mensaje": "Pago eliminado"}

@router.get("/verificar-saldo/")
def verificar_saldo_endpoint(usuario_id: int, db: Session = Depends(get_db)):
    return pagos_service.verificar_saldo(db, usuario_id)  # ✅ Usar pagos_service

@router.put("/{pago_id}/marcar-pagado")
def marcar_pago_pagado(
    pago_id: int, 
    db: Session = Depends(get_db)
):
    """
    Marca un pago como pagado y crea automáticamente una transacción
    """
    resultado = pagos_service.marcar_pago_como_pagado(db, pago_id)
    
    if not resultado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado"
        )
    
    return {
        "mensaje": resultado["mensaje"],
        "pago_id": pago_id,
        "transaccion_creada": resultado.get("transaccion", {}).id if resultado.get("transaccion") else None
    }
@router.get("/pendientes/{usuario_id}")
def obtener_pagos_pendientes(
    usuario_id: int, 
    db: Session = Depends(get_db)
):
    """
    Obtiene solo los pagos pendientes del usuario
    """
    pagos = pagos_service.obtener_pagos_pendientes(db, usuario_id)
    return pagos

@router.get("/pagados/{usuario_id}")
def obtener_pagos_pagados(
    usuario_id: int, 
    db: Session = Depends(get_db)
):
    """
    Obtiene solo los pagos ya pagados del usuario
    """
    pagos = pagos_service.obtener_pagos_pagados(db, usuario_id)
    return pagos

@router.post("/procesar-vencidos")
def procesar_pagos_vencidos(db: Session = Depends(get_db)):
    """
    Procesa automáticamente todos los pagos vencidos
    (Útil para ejecutar en un cron job)
    """
    resultado = pagos_service.procesar_pagos_vencidos(db)
    return resultado