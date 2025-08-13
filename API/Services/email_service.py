import smtplib
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models.modelsDB import Usuario, PagoProgramado, Categoria
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

def enviar_correo(destinatario: str, asunto: str, contenido: str):
    """Función original mejorada con mejor manejo de errores"""
    remitente = os.getenv("EMAIL_SENDER")
    contraseña = os.getenv("EMAIL_PASSWORD")

    if not remitente or not contraseña:
        raise ValueError("Variables de entorno EMAIL_SENDER y EMAIL_PASSWORD no configuradas")

    mensaje = EmailMessage()
    mensaje["Subject"] = asunto
    mensaje["From"] = remitente
    mensaje["To"] = destinatario
    mensaje.set_content(contenido)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(remitente, contraseña)
            smtp.send_message(mensaje)
            print(f"Correo enviado correctamente a {destinatario}")
            return True
    except Exception as e:
        print(f"Error al enviar correo a {destinatario}: {e}")
        return False

def enviar_correo_html(destinatario: str, asunto: str, contenido_html: str, contenido_texto: str = ""):
    """Envía correos con formato HTML más atractivo"""
    remitente = os.getenv("EMAIL_SENDER")
    contraseña = os.getenv("EMAIL_PASSWORD")

    if not remitente or not contraseña:
        raise ValueError("Variables de entorno EMAIL_SENDER y EMAIL_PASSWORD no configuradas")

    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = asunto
    mensaje["From"] = remitente
    mensaje["To"] = destinatario

    # Crear versión texto plano y HTML
    if contenido_texto:
        parte_texto = MIMEText(contenido_texto, "plain")
        mensaje.attach(parte_texto)
    
    parte_html = MIMEText(contenido_html, "html")
    mensaje.attach(parte_html)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(remitente, contraseña)
            smtp.send_message(mensaje)
            print(f"Correo HTML enviado correctamente a {destinatario}")
            return True
    except Exception as e:
        print(f"Error al enviar correo HTML a {destinatario}: {e}")
        return False

# ======================== FUNCIONES DE PAGOS PROGRAMADOS ========================

def generar_plantilla_recordatorio_pago(usuario: Usuario, pago: PagoProgramado, categoria: Categoria, dias_restantes: int) -> Dict[str, str]:
    """Genera plantillas de correo para recordatorios de pago"""
    
    fecha_formatted = pago.fecha.strftime("%d/%m/%Y")
    monto_formatted = f"${pago.monto:,.2f}"
    
    if dias_restantes == 0:
        urgencia = "HOY"
        mensaje_urgencia = "¡Tu pago vence HOY!"
        color_urgencia = "#dc3545"  # Rojo
    elif dias_restantes == 1:
        urgencia = "MAÑANA"
        mensaje_urgencia = "¡Tu pago vence mañana!"
        color_urgencia = "#fd7e14"  # Naranja
    elif dias_restantes <= 3:
        urgencia = "PRÓXIMAMENTE"
        mensaje_urgencia = f"Tu pago vence en {dias_restantes} días"
        color_urgencia = "#ffc107"  # Amarillo
    else:
        urgencia = "RECORDATORIO"
        mensaje_urgencia = f"Tu pago vence en {dias_restantes} días"
        color_urgencia = "#17a2b8"  # Azul info

    # Plantilla HTML (código completo mantenido igual que en el original)
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Recordatorio de Pago</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #e9ecef;">
                <h1 style="color: #343a40; margin: 0;">Control de Gastos</h1>
                <p style="color: #6c757d; margin: 5px 0 0 0;">Recordatorio de Pago Programado</p>
            </div>

            <!-- Alert Badge -->
            <div style="text-align: center; margin: 20px 0;">
                <span style="background-color: {color_urgencia}; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 14px;">
                    {urgencia}
                </span>
            </div>

            <!-- Main Content -->
            <div style="padding: 20px 0;">
                <h2 style="color: {color_urgencia}; text-align: center; margin-bottom: 30px;">
                    {mensaje_urgencia}
                </h2>

                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #495057; margin-top: 0;">Detalles del Pago:</h3>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;"><strong>Concepto:</strong></td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6; text-align: right;">{pago.nombre}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;"><strong>Monto:</strong></td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6; text-align: right; color: #dc3545; font-weight: bold;">{monto_formatted}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;"><strong>Fecha de vencimiento:</strong></td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6; text-align: right;">{fecha_formatted}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0;"><strong>Categoría:</strong></td>
                            <td style="padding: 10px 0; text-align: right;">{categoria.nombre if categoria else "Sin categoría"}</td>
                        </tr>
                    </table>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <p style="color: #6c757d; font-size: 16px;">
                        Hola <strong>{usuario.nombre}</strong>, no olvides realizar este pago a tiempo para mantener tus finanzas al día.
                    </p>
                </div>

            </div>

            <!-- Footer -->
            <div style="border-top: 2px solid #e9ecef; padding-top: 20px; text-align: center; color: #6c757d; font-size: 14px;">
                <p>Este es un recordatorio automático de tu aplicación de Control de Gastos.</p>
                <p>© 2025 Control de Gastos. Mantén tus finanzas organizadas.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plantilla de texto plano
    texto_template = f"""
Control de Gastos - Recordatorio de Pago

{mensaje_urgencia}

Hola {usuario.nombre},

Te recordamos que tienes un pago programado próximo a vencer:

Detalles del Pago:
- Concepto: {pago.nombre}
- Monto: {monto_formatted}
- Fecha de vencimiento: {fecha_formatted}
- Categoría: {categoria.nombre if categoria else "Sin categoría"}

No olvides realizar este pago a tiempo para mantener tus finanzas al día.

¡Gracias por usar Control de Gastos!
"""

    return {
        "html": html_template,
        "texto": texto_template,
        "asunto": f"Recordatorio: {pago.nombre} - Vence {fecha_formatted}"
    }

def obtener_pagos_proximos_a_vencer(db: Session, dias_anticipacion: List[int] = [7, 3, 1, 0]) -> List[Dict[str, Any]]:
    """Obtiene los pagos que están próximos a vencer según los días de anticipación"""
    pagos_a_notificar = []
    hoy = date.today()
    
    for dias in dias_anticipacion:
        fecha_objetivo = hoy + timedelta(days=dias)
        
        pagos = db.query(PagoProgramado).join(Usuario).join(Categoria, isouter=True).filter(
            PagoProgramado.fecha == fecha_objetivo,
            PagoProgramado.estado == "pendiente"
        ).all()
        
        for pago in pagos:
            pagos_a_notificar.append({
                "pago": pago,
                "usuario": pago.usuario,
                "categoria": pago.categoria,
                "dias_restantes": dias
            })
    
    return pagos_a_notificar

def enviar_notificaciones_pagos_programados(db: Session, dias_anticipacion: List[int] = [7, 3, 1, 0]) -> Dict[str, int]:
    """Envía notificaciones para todos los pagos próximos a vencer"""
    pagos_a_notificar = obtener_pagos_proximos_a_vencer(db, dias_anticipacion)
    
    resultado = {
        "enviados": 0,
        "errores": 0,
        "total": len(pagos_a_notificar)
    }
    
    for item in pagos_a_notificar:
        try:
            plantilla = generar_plantilla_recordatorio_pago(
                item["usuario"], 
                item["pago"], 
                item["categoria"], 
                item["dias_restantes"]
            )
            
            exito = enviar_correo_html(
                destinatario=item["usuario"].correo,
                asunto=plantilla["asunto"],
                contenido_html=plantilla["html"],
                contenido_texto=plantilla["texto"]
            )
            
            if exito:
                resultado["enviados"] += 1
                print(f"Notificación enviada: {item['pago'].nombre} - {item['usuario'].nombre}")
            else:
                resultado["errores"] += 1
                print(f"Error enviando: {item['pago'].nombre} - {item['usuario'].nombre}")
                
        except Exception as e:
            resultado["errores"] += 1
            print(f"Error procesando pago {item['pago'].nombre}: {e}")
    
    print(f"\nResumen: {resultado['enviados']} enviados, {resultado['errores']} errores de {resultado['total']} total")
    return resultado

# ======================== FUNCIONES DE PRESUPUESTOS ========================

# Modificar la función enviar_notificaciones_alertas_presupuestos
def enviar_notificaciones_alertas_presupuestos(db: Session, usuario_id: int, alertas: list = None) -> Dict[str, int]:
    """
    ✅ FUNCIÓN PRINCIPAL CORREGIDA - Envía notificaciones para alertas de presupuestos
    Si no se pasan alertas, verifica todas las del usuario.
    """
    resultado = {
        "enviados": 0,
        "errores": 0,
        "total": 0
    }
    
    try:
        # Obtener usuario
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            print(f"❌ Usuario {usuario_id} no encontrado")
            return resultado
        
        # Si no se pasan alertas, obtenerlas
        if alertas is None:
            from Services.presupuestos_service import verificar_alertas
            alertas = verificar_alertas(db, usuario_id)
        
        if not alertas:
            print(f"✅ Usuario {usuario_id} - Sin alertas para notificar")
            return resultado
        
        # Filtrar solo alertas que queremos notificar (excedido, cerca_limite, informativo)
        alertas_a_notificar = [a for a in alertas if a.get('tipo') in ['excedido', 'cerca_limite', 'informativo']]
        resultado["total"] = len(alertas_a_notificar)
        
        if not alertas_a_notificar:
            print(f"✅ Usuario {usuario_id} - Sin alertas críticas para notificar")
            return resultado
        
        # Agrupar alertas por tipo para un solo email
        alertas_excedidas = [a for a in alertas_a_notificar if a.get('tipo') == 'excedido']
        alertas_limite = [a for a in alertas_a_notificar if a.get('tipo') == 'cerca_limite']
        alertas_informativas = [a for a in alertas_a_notificar if a.get('tipo') == 'informativo']
        
        # Enviar un solo email con todas las alertas del usuario
        exito = enviar_correo_alerta_presupuesto_consolidado(
            usuario=usuario,
            alertas_excedidas=alertas_excedidas,
            alertas_limite=alertas_limite,
            alertas_informativas=alertas_informativas,
            db=db
        )
        
        if exito:
            resultado["enviados"] = len(alertas_a_notificar)
            print(f"✅ Alertas enviadas a {usuario.nombre}: {len(alertas_a_notificar)} alertas")
        else:
            resultado["errores"] = len(alertas_a_notificar)
            print(f"❌ Error enviando alertas a {usuario.nombre}")
            
        return resultado
        
    except Exception as e:
        print(f"❌ Error general enviando alertas de presupuesto: {e}")
        resultado["errores"] = resultado["total"]
        return resultado

# Modificar la función generar_html_alerta_presupuesto
def generar_html_alerta_presupuesto(usuario: Usuario, alertas_excedidas: list, 
                                 alertas_limite: list, alertas_informativas: list,
                                 fecha_actual: str, db: Session) -> str:
    """Genera el contenido HTML para el email de alertas de presupuesto"""
    
    total_alertas = len(alertas_excedidas) + len(alertas_limite) + len(alertas_informativas)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Alertas de Presupuesto</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 0; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 600;">💰 Control de Gastos</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">Alertas de Presupuesto</p>
            </div>
            
            <!-- Stats -->
            <div style="padding: 20px; text-align: center; background: #f8f9fa;">
                <div style="display: inline-block; margin: 0 20px;">
                    <div style="font-size: 24px; font-weight: bold; color: #dc3545;">{len(alertas_excedidas)}</div>
                    <div style="font-size: 12px; color: #666; text-transform: uppercase;">Excedidos</div>
                </div>
                <div style="display: inline-block; margin: 0 20px;">
                    <div style="font-size: 24px; font-weight: bold; color: #ffa502;">{len(alertas_limite)}</div>
                    <div style="font-size: 12px; color: #666; text-transform: uppercase;">Cerca Límite</div>
                </div>
                <div style="display: inline-block; margin: 0 20px;">
                    <div style="font-size: 24px; font-weight: bold; color: #17a2b8;">{len(alertas_informativas)}</div>
                    <div style="font-size: 12px; color: #666; text-transform: uppercase;">Informativos</div>
                </div>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px 20px;">
                <h2 style="color: #333; text-align: center; margin-bottom: 30px;">
                    Hola {usuario.nombre}, tienes {total_alertas} alertas importantes
                </h2>
    """
    
    # Agregar presupuestos excedidos
    if alertas_excedidas:
        html += """
                <div style="margin: 25px 0;">
                    <h3 style="color: #dc3545; font-size: 20px; margin-bottom: 15px;">🚨 Presupuestos Excedidos</h3>
                    <p style="color: #666; margin-bottom: 20px;">Los siguientes presupuestos han superado el límite:</p>
        """
        
        for alerta in alertas_excedidas:
            categoria_nombre = obtener_nombre_categoria(db, alerta.get('categoria_id', alerta.get('categoria')))
            exceso = alerta.get('gasto_actual', 0) - alerta.get('monto_presupuesto', 0)
            
            html += f"""
                    <div style="background: #fff5f5; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 5px solid #dc3545;">
                        <div style="font-size: 18px; font-weight: 600; color: #333; margin-bottom: 10px;">{categoria_nombre}</div>
                        <div style="font-size: 16px; margin: 8px 0;">
                            <strong>💸 Gastado:</strong> <span style="color: #dc3545; font-weight: bold;">${alerta.get('gasto_actual', 0):.2f}</span><br>
                            <strong>📊 Presupuesto:</strong> ${alerta.get('monto_presupuesto', 0):.2f}<br>
                            <strong>🚨 Excedido por:</strong> <span style="color: #dc3545; font-weight: bold;">${exceso:.2f}</span>
                        </div>
                        <div style="background: #dc3545; color: white; padding: 8px; border-radius: 4px; text-align: center; margin-top: 10px;">
                            <strong>{alerta.get('porcentaje', 0):.1f}% del presupuesto usado</strong>
                        </div>
                    </div>
            """
        
        html += """
                </div>
        """
    
    # Agregar presupuestos cerca del límite
    if alertas_limite:
        html += """
                <div style="margin: 25px 0;">
                    <h3 style="color: #ffa502; font-size: 20px; margin-bottom: 15px;">⚠️ Cerca del Límite</h3>
                    <p style="color: #666; margin-bottom: 20px;">Los siguientes presupuestos están próximos a agotarse:</p>
        """
        
        for alerta in alertas_limite:
            categoria_nombre = obtener_nombre_categoria(db, alerta.get('categoria_id', alerta.get('categoria')))
            restante = alerta.get('monto_presupuesto', 0) - alerta.get('gasto_actual', 0)
            
            html += f"""
                    <div style="background: #fff8f0; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 5px solid #ffa502;">
                        <div style="font-size: 18px; font-weight: 600; color: #333; margin-bottom: 10px;">{categoria_nombre}</div>
                        <div style="font-size: 16px; margin: 8px 0;">
                            <strong>💸 Gastado:</strong> ${alerta.get('gasto_actual', 0):.2f}<br>
                            <strong>📊 Presupuesto:</strong> ${alerta.get('monto_presupuesto', 0):.2f}<br>
                            <strong>💰 Disponible:</strong> <span style="color: #27ae60; font-weight: bold;">${restante:.2f}</span>
                        </div>
                        <div style="background: #ffa502; color: white; padding: 8px; border-radius: 4px; text-align: center; margin-top: 10px;">
                            <strong>{alerta.get('porcentaje', 0):.1f}% del presupuesto usado</strong>
                        </div>
                    </div>
            """
        
        html += """
                </div>
        """
    
    # Agregar presupuestos informativos (50% o más)
    if alertas_informativas:
        html += """
                <div style="margin: 25px 0;">
                    <h3 style="color: #17a2b8; font-size: 20px; margin-bottom: 15px;">ℹ️ Estado de Presupuestos</h3>
                    <p style="color: #666; margin-bottom: 20px;">Los siguientes presupuestos han alcanzado el 50% o más:</p>
        """
        
        for alerta in alertas_informativas:
            categoria_nombre = obtener_nombre_categoria(db, alerta.get('categoria_id', alerta.get('categoria')))
            restante = alerta.get('monto_presupuesto', 0) - alerta.get('gasto_actual', 0)
            
            html += f"""
                    <div style="background: #e7f5ff; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 5px solid #17a2b8;">
                        <div style="font-size: 18px; font-weight: 600; color: #333; margin-bottom: 10px;">{categoria_nombre}</div>
                        <div style="font-size: 16px; margin: 8px 0;">
                            <strong>💸 Gastado:</strong> ${alerta.get('gasto_actual', 0):.2f}<br>
                            <strong>📊 Presupuesto:</strong> ${alerta.get('monto_presupuesto', 0):.2f}<br>
                            <strong>💰 Disponible:</strong> <span style="color: #27ae60; font-weight: bold;">${restante:.2f}</span>
                        </div>
                        <div style="background: #17a2b8; color: white; padding: 8px; border-radius: 4px; text-align: center; margin-top: 10px;">
                            <strong>{alerta.get('porcentaje', 0):.1f}% del presupuesto usado</strong>
                        </div>
                    </div>
            """
        
        html += """
                </div>
        """
    
    # Recomendaciones y footer
    html += f"""
                <!-- Recomendaciones -->
                <div style="background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%); color: white; padding: 20px; border-radius: 8px; margin: 25px 0;">
                    <h3 style="margin-top: 0; font-size: 18px;">💡 Recomendaciones</h3>
                    <ul style="margin: 15px 0; padding-left: 20px;">
                        <li style="margin: 8px 0; font-size: 14px;">📊 Revisa tus transacciones recientes</li>
                        <li style="margin: 8px 0; font-size: 14px;">🎯 Ajusta tus hábitos de gasto</li>
                        <li style="margin: 8px 0; font-size: 14px;">📈 Planifica mejor tus compras</li>
                        <li style="margin: 8px 0; font-size: 14px;">💰 Considera ajustar presupuestos</li>
                    </ul>
                </div>
                
                <!-- Action Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">
                        📱 Ver Presupuestos Detallados
                    </a>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8f9fa; color: #6c757d; padding: 20px; text-align: center; font-size: 12px; border-top: 1px solid #e9ecef;">
                <p><strong>📧 Control de Gastos - Alertas Automáticas</strong></p>
                <p>📅 Enviado el {fecha_actual}</p>
                <p>© 2025 Control de Gastos. Mantén tus finanzas organizadas.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def enviar_correo_alerta_presupuesto_consolidado(usuario: Usuario, alertas_excedidas: list, 
                                               alertas_limite: list, db: Session) -> bool:
    """
    ✅ FUNCIÓN CORREGIDA - Envía un solo correo consolidado con todas las alertas del usuario
    """
    try:
        if not alertas_excedidas and not alertas_limite:
            return True
        
        total_alertas = len(alertas_excedidas) + len(alertas_limite)
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        
        # Determinar asunto según tipo de alertas
        if alertas_excedidas:
            asunto = f"🚨 Control de Gastos: {len(alertas_excedidas)} Presupuesto(s) Excedido(s)"
        else:
            asunto = f"⚠️ Control de Gastos: {len(alertas_limite)} Presupuesto(s) Cerca del Límite"
        
        # Generar contenido HTML
        html_content = generar_html_alerta_presupuesto(
            usuario=usuario,
            alertas_excedidas=alertas_excedidas,
            alertas_limite=alertas_limite,
            fecha_actual=fecha_actual,
            db=db
        )
        
        # Generar contenido texto plano
        texto_content = generar_texto_alerta_presupuesto(
            usuario=usuario,
            alertas_excedidas=alertas_excedidas,
            alertas_limite=alertas_limite,
            fecha_actual=fecha_actual
        )
        
        # Enviar correo
        resultado = enviar_correo_html(
            destinatario=usuario.correo,
            asunto=asunto,
            contenido_html=html_content,
            contenido_texto=texto_content
        )
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error enviando correo consolidado de alertas: {e}")
        return False

def generar_html_alerta_presupuesto(usuario: Usuario, alertas_excedidas: list, 
                                   alertas_limite: list, fecha_actual: str, db: Session) -> str:
    """Genera el contenido HTML para el email de alertas de presupuesto"""
    
    total_alertas = len(alertas_excedidas) + len(alertas_limite)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Alertas de Presupuesto</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 0; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 20px auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px; font-weight: 600;">💰 Control de Gastos</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">Alertas de Presupuesto</p>
            </div>
            
            <!-- Stats -->
            <div style="padding: 20px; text-align: center; background: #f8f9fa;">
                <div style="display: inline-block; margin: 0 20px;">
                    <div style="font-size: 24px; font-weight: bold; color: #dc3545;">{len(alertas_excedidas)}</div>
                    <div style="font-size: 12px; color: #666; text-transform: uppercase;">Excedidos</div>
                </div>
                <div style="display: inline-block; margin: 0 20px;">
                    <div style="font-size: 24px; font-weight: bold; color: #ffa502;">{len(alertas_limite)}</div>
                    <div style="font-size: 12px; color: #666; text-transform: uppercase;">Cerca Límite</div>
                </div>
                <div style="display: inline-block; margin: 0 20px;">
                    <div style="font-size: 24px; font-weight: bold; color: #667eea;">{total_alertas}</div>
                    <div style="font-size: 12px; color: #666; text-transform: uppercase;">Total Alertas</div>
                </div>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px 20px;">
                <h2 style="color: #333; text-align: center; margin-bottom: 30px;">
                    Hola {usuario.nombre}, tienes alertas importantes
                </h2>
    """
    
    # Agregar presupuestos excedidos
    if alertas_excedidas:
        html += """
                <div style="margin: 25px 0;">
                    <h3 style="color: #dc3545; font-size: 20px; margin-bottom: 15px;">🚨 Presupuestos Excedidos</h3>
                    <p style="color: #666; margin-bottom: 20px;">Los siguientes presupuestos han superado el límite:</p>
        """
        
        for alerta in alertas_excedidas:
            # Obtener nombre de categoría
            categoria_nombre = obtener_nombre_categoria(db, alerta.get('categoria_id', alerta.get('categoria')))
            exceso = alerta.get('gasto_actual', 0) - alerta.get('monto_presupuesto', 0)
            
            html += f"""
                    <div style="background: #fff5f5; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 5px solid #dc3545;">
                        <div style="font-size: 18px; font-weight: 600; color: #333; margin-bottom: 10px;">{categoria_nombre}</div>
                        <div style="font-size: 16px; margin: 8px 0;">
                            <strong>💸 Gastado:</strong> <span style="color: #dc3545; font-weight: bold;">${alerta.get('gasto_actual', 0):.2f}</span><br>
                            <strong>📊 Presupuesto:</strong> ${alerta.get('monto_presupuesto', 0):.2f}<br>
                            <strong>🚨 Excedido por:</strong> <span style="color: #dc3545; font-weight: bold;">${exceso:.2f}</span>
                        </div>
                        <div style="background: #dc3545; color: white; padding: 8px; border-radius: 4px; text-align: center; margin-top: 10px;">
                            <strong>{alerta.get('porcentaje', 0):.1f}% del presupuesto usado</strong>
                        </div>
                    </div>
            """
        
        html += """
                </div>
        """
    
    # Agregar presupuestos cerca del límite
    if alertas_limite:
        html += """
                <div style="margin: 25px 0;">
                    <h3 style="color: #ffa502; font-size: 20px; margin-bottom: 15px;">⚠️ Cerca del Límite</h3>
                    <p style="color: #666; margin-bottom: 20px;">Los siguientes presupuestos están próximos a agotarse:</p>
        """
        
        for alerta in alertas_limite:
            categoria_nombre = obtener_nombre_categoria(db, alerta.get('categoria_id', alerta.get('categoria')))
            restante = alerta.get('monto_presupuesto', 0) - alerta.get('gasto_actual', 0)
            
            html += f"""
                    <div style="background: #fff8f0; margin: 15px 0; padding: 20px; border-radius: 8px; border-left: 5px solid #ffa502;">
                        <div style="font-size: 18px; font-weight: 600; color: #333; margin-bottom: 10px;">{categoria_nombre}</div>
                        <div style="font-size: 16px; margin: 8px 0;">
                            <strong>💸 Gastado:</strong> ${alerta.get('gasto_actual', 0):.2f}<br>
                            <strong>📊 Presupuesto:</strong> ${alerta.get('monto_presupuesto', 0):.2f}<br>
                            <strong>💰 Disponible:</strong> <span style="color: #27ae60; font-weight: bold;">${restante:.2f}</span>
                        </div>
                        <div style="background: #ffa502; color: white; padding: 8px; border-radius: 4px; text-align: center; margin-top: 10px;">
                            <strong>{alerta.get('porcentaje', 0):.1f}% del presupuesto usado</strong>
                        </div>
                    </div>
            """
        
        html += """
                </div>
        """
    
    # Recomendaciones y footer
    html += f"""
                <!-- Recomendaciones -->
                <div style="background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%); color: white; padding: 20px; border-radius: 8px; margin: 25px 0;">
                    <h3 style="margin-top: 0; font-size: 18px;">💡 Recomendaciones</h3>
                    <ul style="margin: 15px 0; padding-left: 20px;">
                        <li style="margin: 8px 0; font-size: 14px;">📊 Revisa tus transacciones recientes</li>
                        <li style="margin: 8px 0; font-size: 14px;">🎯 Ajusta tus hábitos de gasto</li>
                        <li style="margin: 8px 0; font-size: 14px;">📈 Planifica mejor tus compras</li>
                        <li style="margin: 8px 0; font-size: 14px;">💰 Considera ajustar presupuestos</li>
                    </ul>
                </div>
                
                <!-- Action Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600;">
                        📱 Ver Presupuestos Detallados
                    </a>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8f9fa; color: #6c757d; padding: 20px; text-align: center; font-size: 12px; border-top: 1px solid #e9ecef;">
                <p><strong>📧 Control de Gastos - Alertas Automáticas</strong></p>
                <p>📅 Enviado el {fecha_actual}</p>
                <p>© 2025 Control de Gastos. Mantén tus finanzas organizadas.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def generar_texto_alerta_presupuesto(usuario: Usuario, alertas_excedidas: list, 
                                    alertas_limite: list, fecha_actual: str) -> str:
    """Genera el contenido en texto plano para el email de alertas"""
    
    texto = f"""
Control de Gastos - Alertas de Presupuesto

Hola {usuario.nombre},

Tienes {len(alertas_excedidas) + len(alertas_limite)} alertas importantes sobre tus presupuestos:

"""
    
    if alertas_excedidas:
        texto += f"""
🚨 PRESUPUESTOS EXCEDIDOS ({len(alertas_excedidas)}):
"""
        for alerta in alertas_excedidas:
            exceso = alerta.get('gasto_actual', 0) - alerta.get('monto_presupuesto', 0)
            texto += f"""
- {alerta.get('categoria', 'Categoría')}: 
  * Gastado: ${alerta.get('gasto_actual', 0):.2f}
  * Presupuesto: ${alerta.get('monto_presupuesto', 0):.2f}
  * Excedido por: ${exceso:.2f}
  * Porcentaje usado: {alerta.get('porcentaje', 0):.1f}%
"""
    
    if alertas_limite:
        texto += f"""
⚠️ CERCA DEL LÍMITE ({len(alertas_limite)}):
"""
        for alerta in alertas_limite:
            restante = alerta.get('monto_presupuesto', 0) - alerta.get('gasto_actual', 0)
            texto += f"""
- {alerta.get('categoria', 'Categoría')}:
  * Gastado: ${alerta.get('gasto_actual', 0):.2f}
  * Presupuesto: ${alerta.get('monto_presupuesto', 0):.2f}
  * Disponible: ${restante:.2f}
  * Porcentaje usado: {alerta.get('porcentaje', 0):.1f}%
"""
    
    texto += f"""
💡 RECOMENDACIONES:
- Revisa tus transacciones recientes
- Ajusta tus hábitos de gasto
- Planifica mejor tus compras
- Considera ajustar presupuestos

📅 Fecha: {fecha_actual}
© 2025 Control de Gastos
"""
    
    return texto

def obtener_nombre_categoria(db: Session, categoria_id_o_nombre) -> str:
    """Obtiene el nombre de la categoría desde la base de datos o retorna el nombre si ya es string"""
    try:
        if isinstance(categoria_id_o_nombre, str):
            return categoria_id_o_nombre
        
        if isinstance(categoria_id_o_nombre, int):
            categoria = db.query(Categoria).filter(Categoria.id == categoria_id_o_nombre).first()
            return categoria.nombre if categoria else f"Categoría {categoria_id_o_nombre}"
        
        return "Sin categoría"
    except:
        return "Sin categoría"

def enviar_resumen_semanal_presupuestos(db: Session, usuario_id: int) -> bool:
    """✅ FUNCIÓN CORREGIDA - Envía un resumen semanal del estado de todos los presupuestos del usuario"""
    try:
        from Services.presupuestos_service import verificar_alertas
        
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            print(f"❌ Usuario {usuario_id} no encontrado para resumen semanal")
            return False
        
        alertas = verificar_alertas(db, usuario_id)
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        
        # Generar HTML del resumen
        html_resumen = generar_html_resumen_semanal(usuario, alertas, fecha_actual)
        
        # Generar texto plano
        texto_resumen = generar_texto_resumen_semanal(usuario, alertas, fecha_actual)
        
        # Enviar correo
        resultado = enviar_correo_html(
            destinatario=usuario.correo,
            asunto=f"📊 Resumen semanal de presupuestos - {fecha_actual}",
            contenido_html=html_resumen,
            contenido_texto=texto_resumen
        )
        
        if resultado:
            print(f"✅ Resumen semanal enviado a {usuario.nombre}")
        else:
            print(f"❌ Error enviando resumen semanal a {usuario.nombre}")
            
        return resultado
        
    except Exception as e:
        print(f"❌ Error enviando resumen semanal a usuario {usuario_id}: {e}")
        return False

def generar_html_resumen_semanal(usuario: Usuario, alertas: list, fecha_actual: str) -> str:
    """Genera HTML para el resumen semanal de presupuestos"""
    
    # Agrupar alertas
    excedidos = [a for a in alertas if a.get('tipo') == 'excedido']
    cerca_limite = [a for a in alertas if a.get('tipo') == 'cerca_limite']
    informativos = [a for a in alertas if a.get('tipo') == 'informativo']
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Resumen Semanal de Presupuestos</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #e9ecef;">
                <h1 style="color: #007bff; margin: 0;">📊 Control de Gastos</h1>
                <p style="color: #6c757d; margin: 5px 0 0 0;">Resumen Semanal de Presupuestos</p>
                <p style="color: #6c757d; font-size: 14px;">Fecha: {fecha_actual}</p>
            </div>

            <div style="padding: 20px 0;">
                <h2 style="color: #343a40; text-align: center; margin-bottom: 30px;">
                    Hola {usuario.nombre}, aquí tienes tu resumen semanal
                </h2>

                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #495057; margin-top: 0;">Estado de tus Presupuestos:</h3>
    """
    
    if not alertas:
        html += """
                    <div style="text-align: center; padding: 20px;">
                        <p style="color: #28a745; font-size: 18px; font-weight: bold;">🎉 ¡Excelente trabajo!</p>
                        <p style="color: #6c757d;">Todos tus presupuestos están bajo control.</p>
                    </div>
        """
    else:
        if excedidos:
            html += f"""
                    <div style="background-color: #f8d7da; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #dc3545;">
                        <h4 style="color: #721c24; margin: 0 0 10px 0;">🚨 Presupuestos Excedidos ({len(excedidos)})</h4>
            """
            for alerta in excedidos:
                html += f"<p style='color: #721c24; margin: 5px 0;'>• {alerta.get('categoria', 'Categoría')}: {alerta.get('porcentaje', 0):.1f}% usado</p>"
            html += "</div>"
        
        if cerca_limite:
            html += f"""
                    <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #ffc107;">
                        <h4 style="color: #856404; margin: 0 0 10px 0;">⚠️ Cerca del Límite ({len(cerca_limite)})</h4>
            """
            for alerta in cerca_limite:
                html += f"<p style='color: #856404; margin: 5px 0;'>• {alerta.get('categoria', 'Categoría')}: {alerta.get('porcentaje', 0):.1f}% usado</p>"
            html += "</div>"
        
        if informativos:
            html += f"""
                    <div style="background-color: #cce5ff; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #007bff;">
                        <h4 style="color: #004085; margin: 0 0 10px 0;">ℹ️ Estado Normal ({len(informativos)})</h4>
            """
            for alerta in informativos:
                html += f"<p style='color: #004085; margin: 5px 0;'>• {alerta.get('categoria', 'Categoría')}: {alerta.get('porcentaje', 0):.1f}% usado</p>"
            html += "</div>"
    
    html += f"""
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        Ver Detalles Completos
                    </a>
                </div>
            </div>

            <!-- Footer -->
            <div style="border-top: 2px solid #e9ecef; padding-top: 20px; text-align: center; color: #6c757d; font-size: 14px;">
                <p>Resumen semanal automático de Control de Gastos</p>
                <p>© 2025 Control de Gastos. Mantén tus finanzas organizadas.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def generar_texto_resumen_semanal(usuario: Usuario, alertas: list, fecha_actual: str) -> str:
    """Genera texto plano para el resumen semanal"""
    
    excedidos = [a for a in alertas if a.get('tipo') == 'excedido']
    cerca_limite = [a for a in alertas if a.get('tipo') == 'cerca_limite']
    informativos = [a for a in alertas if a.get('tipo') == 'informativo']
    
    texto = f"""
Control de Gastos - Resumen Semanal de Presupuestos
Fecha: {fecha_actual}

Hola {usuario.nombre},

Aquí tienes el resumen semanal del estado de tus presupuestos:

"""
    
    if not alertas:
        texto += """
🎉 ¡EXCELENTE TRABAJO!
Todos tus presupuestos están bajo control.

"""
    else:
        if excedidos:
            texto += f"""
🚨 PRESUPUESTOS EXCEDIDOS ({len(excedidos)}):
"""
            for alerta in excedidos:
                texto += f"• {alerta.get('categoria', 'Categoría')}: {alerta.get('porcentaje', 0):.1f}% usado\n"
            texto += "\n"
        
        if cerca_limite:
            texto += f"""
⚠️ CERCA DEL LÍMITE ({len(cerca_limite)}):
"""
            for alerta in cerca_limite:
                texto += f"• {alerta.get('categoria', 'Categoría')}: {alerta.get('porcentaje', 0):.1f}% usado\n"
            texto += "\n"
        
        if informativos:
            texto += f"""
ℹ️ ESTADO NORMAL ({len(informativos)}):
"""
            for alerta in informativos:
                texto += f"• {alerta.get('categoria', 'Categoría')}: {alerta.get('porcentaje', 0):.1f}% usado\n"
            texto += "\n"
    
    texto += """
Resumen semanal automático de Control de Gastos
© 2025 Control de Gastos. Mantén tus finanzas organizadas.
"""
    
    return texto

def enviar_correo_confirmacion_pago_creado(usuario: Usuario, pago: PagoProgramado, categoria: Categoria = None) -> bool:
    """Envía correo de confirmación cuando se crea un nuevo pago programado"""
    
    fecha_formatted = pago.fecha.strftime("%d/%m/%Y")
    monto_formatted = f"${pago.monto:,.2f}"
    fecha_creacion = datetime.now().strftime("%d/%m/%Y a las %H:%M")
    
    # Plantilla HTML para confirmación
    html_confirmacion = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pago Programado Creado</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
            
            <!-- Header -->
            <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #e9ecef;">
                <h1 style="color: #28a745; margin: 0;">Control de Gastos</h1>
                <p style="color: #6c757d; margin: 5px 0 0 0;">Confirmación de Pago Programado</p>
            </div>

            <!-- Success Badge -->
            <div style="text-align: center; margin: 20px 0;">
                <span style="background-color: #28a745; color: white; padding: 8px 16px; border-radius: 20px; font-weight: bold; font-size: 14px;">
                    ✓ CREADO EXITOSAMENTE
                </span>
            </div>

            <!-- Main Content -->
            <div style="padding: 20px 0;">
                <h2 style="color: #28a745; text-align: center; margin-bottom: 30px;">
                    ¡Tu pago programado ha sido registrado!
                </h2>

                <div style="background-color: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <h3 style="color: #155724; margin-top: 0;">Detalles del Pago Programado:</h3>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #c3e6cb;"><strong>Concepto:</strong></td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #c3e6cb; text-align: right;">{pago.nombre}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #c3e6cb;"><strong>Monto:</strong></td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #c3e6cb; text-align: right; color: #dc3545; font-weight: bold;">{monto_formatted}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #c3e6cb;"><strong>Fecha programada:</strong></td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #c3e6cb; text-align: right;">{fecha_formatted}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #c3e6cb;"><strong>Categoría:</strong></td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #c3e6cb; text-align: right;">{categoria.nombre if categoria else "Sin categoría"}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; border-bottom: 1px solid #c3e6cb;"><strong>Estado:</strong></td>
                            <td style="padding: 10px 0; border-bottom: 1px solid #c3e6cb; text-align: right;">
                                <span style="background-color: #ffc107; color: #856404; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold;">PENDIENTE</span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0;"><strong>Creado el:</strong></td>
                            <td style="padding: 10px 0; text-align: right; color: #6c757d; font-size: 14px;">{fecha_creacion}</td>
                        </tr>
                    </table>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <p style="color: #6c757d; font-size: 16px;">
                        Hola <strong>{usuario.nombre}</strong>, tu pago ha sido programado exitosamente. 
                        Te enviaremos recordatorios antes de la fecha de vencimiento.
                    </p>
                </div>

                <!-- Info Box -->
                <div style="background-color: #cce5ff; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #007bff;">
                    <h4 style="color: #004085; margin-top: 0;">¿Cuándo recibiré recordatorios?</h4>
                    <ul style="color: #004085; margin: 0; padding-left: 20px;">
                        <li>7 días antes del vencimiento</li>
                        <li>3 días antes del vencimiento</li>
                        <li>1 día antes del vencimiento</li>
                        <li>El día del vencimiento</li>
                    </ul>
                </div>
            </div>

            <!-- Footer -->
            <div style="border-top: 2px solid #e9ecef; padding-top: 20px; text-align: center; color: #6c757d; font-size: 14px;">
                <p>Tu pago programado está guardado y será monitoreado automáticamente.</p>
                <p>© 2025 Control de Gastos. Mantén tus finanzas organizadas.</p>
            </div>
        </div>
    </body>
    </html>
    """

    # Plantilla de texto plano
    texto_confirmacion = f"""
Control de Gastos - Confirmación de Pago Programado

¡Tu pago programado ha sido registrado exitosamente!

Hola {usuario.nombre},

Tu pago ha sido programado correctamente en nuestro sistema:

Detalles del Pago Programado:
- Concepto: {pago.nombre}
- Monto: {monto_formatted}
- Fecha programada: {fecha_formatted}
- Categoría: {categoria.nombre if categoria else "Sin categoría"}
- Estado: PENDIENTE
- Creado el: {fecha_creacion}

¿Cuándo recibiré recordatorios?
- 7 días antes del vencimiento
- 3 días antes del vencimiento  
- 1 día antes del vencimiento
- El día del vencimiento

Tu pago programado está guardado y será monitoreado automáticamente.

¡Gracias por usar Control de Gastos!
© 2025 Control de Gastos
"""

    return enviar_correo_html(
        destinatario=usuario.correo,
        asunto=f"Pago programado creado: {pago.nombre}",
        contenido_html=html_confirmacion,
        contenido_texto=texto_confirmacion
    )