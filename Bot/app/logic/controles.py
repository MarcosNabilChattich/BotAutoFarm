import pydirectinput
import random
import time
import logging

log = logging.getLogger("QA_Tool.controles")

# Configuración de seguridad
pydirectinput.FAILSAFE = True 
pydirectinput.PAUSE = 0.01

def click_en_rect(rect, duracion_press=None, modo_dry_run=False):
    """
    Realiza un clic en una coordenada aleatoria dentro de un rectángulo dado.
    """
    x, y, w, h = rect
    
    # Asegurarse de que w y h no sean 0
    w = max(1, w)
    h = max(1, h)

    # Calcular coordenada aleatoria dentro del AÁREA
    rand_x = x + random.randint(0, w - 1)
    rand_y = y + random.randint(0, h - 1)
    
    if modo_dry_run:
        accion = f"Clic en ({rand_x}, {rand_y})"
        if duracion_press:
            accion = f"Mantener presionado en ({rand_x}, {rand_y}) por {duracion_press}s"
        log.info(f"[DRY-RUN] {accion}")
        return (rand_x, rand_y)

    try:
        log.debug(f"Realizando acción en ({rand_x}, {rand_y})")
        if duracion_press:
            pydirectinput.moveTo(rand_x, rand_y)
            pydirectinput.mouseDown()
            time.sleep(duracion_press)
            pydirectinput.mouseUp()
        else:
            pydirectinput.click(rand_x, rand_y)
            
        return (rand_x, rand_y)
        
    except pydirectinput.FailSafeException:
        log.critical("FAILSAFE ACTIVADO: Movimiento del mouse a (0,0) detectado.")
        raise # Relanzar para que el worker lo capture
    except Exception as e:
        log.error(f"Error durante el clic: {e}")
        
def variar_tiempo_espera(min_seg, max_seg, modo_dry_run=False):
    """Genera una espera aleatoria."""
    espera = random.uniform(min_seg, max_seg)
    if modo_dry_run:
        log.info(f"[DRY-RUN] Esperando {espera:.2f} segundos...")
    else:
        log.debug(f"Esperando {espera:.2f} segundos...")
        time.sleep(espera)
    return espera