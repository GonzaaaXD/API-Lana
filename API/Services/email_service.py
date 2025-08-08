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

    # Plantilla HTML
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

                <!-- Action Button -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background-color: #007bff; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">
                        Marcar como Pagado
                    </a>
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

def enviar_correo_bienvenida(usuario: Usuario) -> bool:
    """Envía correo de bienvenida a nuevos usuarios"""
    html_bienvenida = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Bienvenido a Control de Gastos</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
            
            <div style="text-align: center; padding: 20px 0;">
                <h1 style="color: #28a745; margin: 0;">🎉 ¡Bienvenido a Control de Gastos!</h1>
            </div>

            <div style="padding: 20px 0;">
                <h2 style="color: #343a40;">Hola {usuario.nombre},</h2>
                
                <p style="font-size: 16px; color: #495057;">
                    ¡Gracias por unirte a nuestra aplicación de gestión financiera! Estamos emocionados de ayudarte a tomar el control de tus finanzas personales.
                </p>

                <div style="background-color: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #155724; margin-top: 0;">¿Qué puedes hacer con Control de Gastos?</h3>
                    <ul style="color: #155724;">
                        <li>Registrar tus ingresos y gastos diarios</li>
                        <li>Programar pagos y recibir recordatorios automáticos</li>
                        <li>Establecer presupuestos por categorías</li>
                        <li>Visualizar el resumen de tus finanzas</li>
                        <li>Recibir notificaciones importantes por correo</li>
                    </ul>
                </div>

                <p style="font-size: 16px; color: #495057;">
                    Tu cuenta ha sido creada exitosamente con el correo: <strong>{usuario.correo}</strong>
                </p>

                <div style="text-align: center; margin: 30px 0;">
                    <p style="color: #6c757d; font-style: italic;">
                        "El control de tus gastos es el primer paso hacia la libertad financiera"
                    </p>
                </div>
            </div>

            <div style="border-top: 2px solid #e9ecef; padding-top: 20px; text-align: center; color: #6c757d; font-size: 14px;">
                <p>¡Comienza a gestionar tus finanzas hoy mismo!</p>
                <p>© 2025 Control de Gastos</p>
            </div>
        </div>
    </body>
    </html>
    """

    texto_bienvenida = f"""
Control de Gastos - ¡Bienvenido!

Hola {usuario.nombre},

¡Gracias por unirte a nuestra aplicación de gestión financiera!

Tu cuenta ha sido creada exitosamente con el correo: {usuario.correo}

¿Qué puedes hacer con Control de Gastos?
- Registrar tus ingresos y gastos diarios
- Programar pagos y recibir recordatorios automáticos  
- Establecer presupuestos por categorías
- Visualizar el resumen de tus finanzas
- Recibir notificaciones importantes por correo

¡Comienza a gestionar tus finanzas hoy mismo!

© 2025 Control de Gastos
"""

    return enviar_correo_html(
        destinatario=usuario.correo,
        asunto="🎉 ¡Bienvenido a Control de Gastos!",
        contenido_html=html_bienvenida,
        contenido_texto=texto_bienvenida
    )
    
# Agregar esta función al final del archivo email_service.py

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

                <!-- Action Buttons -->
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin: 0 10px;">
                        Ver Mis Pagos
                    </a>
                    <a href="#" style="background-color: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; margin: 0 10px;">
                        Crear Otro Pago
                    </a>
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