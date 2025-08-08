from fastapi import FastAPI
from DB.conexion import engine
from models.modelsDB import Base
from routers import auth, transacciones, presupuestos, pagos, reportes, categorias
from fastapi.middleware.cors import CORSMiddleware

# Imports necesarios para el sistema de notificaciones
from contextlib import asynccontextmanager
from Services.notification_scheduler import inicializar_scheduler, detener_scheduler, ejecutar_notificaciones_ahora
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar logging compatible con Windows
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación"""
    
    # Startup
    logger.info("Iniciando LanaApp...")
    
    # Inicializar scheduler de notificaciones
    if inicializar_scheduler():
        logger.info("Sistema de notificaciones por correo iniciado")
    else:
        logger.error("Error iniciando sistema de notificaciones")
    
    yield
    
    # Shutdown
    logger.info("Cerrando aplicación...")
    detener_scheduler()
    logger.info("LanaApp cerrada correctamente")

app = FastAPI(
    title="API LanaApp",
    description="Sistema de Gestión Financiera",
    version="0.1.0",
    lifespan=lifespan  # Agregar el lifespan para gestionar notificaciones
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes
    allow_methods=["*"],  # Permite todos los métodos
    allow_headers=["*"],  # Permite todos los headers
)

# Incluir todos los routers
app.include_router(auth.router)
app.include_router(transacciones.router)
app.include_router(presupuestos.router)
app.include_router(pagos.router)
app.include_router(reportes.router)
app.include_router(categorias.router)

# Endpoints adicionales para gestión de notificaciones
@app.post("/admin/notificaciones/ejecutar")
async def ejecutar_notificaciones_manual():
    """Ejecuta las notificaciones manualmente (para admin/testing)"""
    try:
        if ejecutar_notificaciones_ahora():
            return {"mensaje": "Notificaciones de pagos ejecutadas exitosamente"}
        else:
            return {"error": "Error ejecutando notificaciones"}
    except Exception as e:
        logger.error(f"Error en endpoint de notificaciones: {e}")
        return {"error": str(e)}

@app.get("/admin/scheduler/estado")
async def obtener_estado_scheduler():
    """Obtiene el estado del scheduler de notificaciones"""
    from Services.notification_scheduler import notification_scheduler
    return notification_scheduler.obtener_estado()

@app.get("/")
def inicio():
    return {"mensaje": "API LanaApp - Sistema de Gestión Financiera"}