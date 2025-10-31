import cv2
import numpy as np
import logging

log = logging.getLogger("QA_Tool.vision")

def find_template(screen_image_np, template_image_path, threshold=0.8):
    """
    Busca una imagen de plantilla dentro de una imagen de pantalla.
    
    :param screen_image_np: Imagen de pantalla (captura) como array de NumPy (en BGR).
    :param template_image_path: Ruta a la imagen de plantilla (en BGR).
    :param threshold: Umbral de confianza (0.0 a 1.0).
    :return: Lista de tuplas (x, y, w, h) de todas las coincidencias encontradas.
    """
    try:
        template = cv2.imread(template_image_path)
        if template is None:
            log.warning(f"No se pudo cargar la plantilla {template_image_path}")
            return []
            
        t_h, t_w = template.shape[:2]
        
        # Realizar la coincidencia de plantillas
        result = cv2.matchTemplate(screen_image_np, template, cv2.TM_CCOEFF_NORMED)
        
        # Encontrar todas las ubicaciones que superen el umbral
        locations = np.where(result >= threshold)
        
        # Agrupar rectángulos superpuestos
        rectangles = []
        for (x, y) in zip(locations[1], locations[0]):
            rectangles.append([int(x), int(y), int(t_w), int(t_h)])
            
        # NMS (Non-Max Suppression) simple para agrupar rectángulos
        # OpenCV groupRectangles es mejor, pero esto funciona para UIs simples
        matches = []
        for (x, y, w, h) in rectangles:
            # Simple check para evitar duplicados muy cercanos
            found_close = False
            for (mx, my, mw, mh) in matches:
                if abs(x - mx) < 10 and abs(y - my) < 10:
                    found_close = True
                    break
            if not found_close:
                matches.append((x, y, w, h))
        
        if matches:
            log.debug(f"Plantilla {template_image_path} encontrada en {len(matches)} ubicaciones.")
            
        return matches
        
    except Exception as e:
        log.error(f"Error en find_template: {e}")
        return []