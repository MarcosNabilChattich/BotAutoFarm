from PySide6.QtCore import QThread, Signal, Slot
import time
import mss
import numpy as np
import cv2
#import keyboard
import logging

from app.logic.vision import find_template
from app.logic.controles import click_en_rect, variar_tiempo_espera
from app.logic.simulacion import SimulationManager
from app.utils.config import cargar_perfil

log = logging.getLogger("QA_Tool.worker")
#HOTKEY_PANICO = "ctrl+alt+q"

class AutomationWorker(QThread):
    # Señales para actualizar la GUI
    estado_actualizado = Signal(str)
    tiempo_restante_actualizado = Signal(str)
    log_generado = Signal(str) # Log para la GUI
    contadores_actualizados = Signal(str, int) # (nombre_contador, valor)
    finalizado = Signal()

    def __init__(self, config_ejecucion, config_elementos, perfil_calibracion):
        super().__init__()
        self.config_ejecucion = config_ejecucion
        self.config_elementos = config_elementos
        self.perfil_calibracion_nombre = perfil_calibracion
        
        self.zonas_calibradas = {}
        
        self._esta_corriendo = False
        self.modo_dry_run = config_ejecucion.get("dry_run", False)
        #self.hotkey_registrada = False
        
        self.contadores = {"clics": 0, "elementos_encontrados": 0, "errores": 0, "reintentos": 0}

    # def setup_panic_hotkey(self):
    #     try:
    #         keyboard.add_hotkey(HOTKEY_PANICO, self.detener_emergencia)
    #         self.hotkey_registrada = True
    #         msg = f"Hotkey de pánico registrada: {HOTKEY_PANICO}"
    #         log.info(msg)
    #         self.log_generado.emit(msg)
    #     except Exception as e:
    #         msg = f"Error al registrar hotkey (requiere admin?): {e}"
    #         log.error(msg)
    #         self.log_generado.emit(msg)

    def run(self):
        self._esta_corriendo = True
        #self.setup_panic_hotkey()

        # Cargar perfil
        self.zonas_calibradas = cargar_perfil(self.perfil_calibracion_nombre)
        if not self.zonas_calibradas:
            msg = f"Error: No se pudo cargar el perfil {self.perfil_calibracion_nombre}"
            log.critical(msg)
            self.log_generado.emit(msg)
            self.finalizado.emit()
            return
            
        self.log_generado.emit(f"Perfil {self.perfil_calibracion_nombre} cargado.")

        self.sim_manager = SimulationManager(self.config_elementos)

        duracion_total_seg = self.config_ejecucion.get("duracion_seg", 600)
        tiempo_inicio = time.time()
        tiempo_fin = tiempo_inicio + duracion_total_seg
        
        self.log_generado.emit(f"Iniciando prueba. Duración: {duracion_total_seg}s. Dry-Run: {self.modo_dry_run}")
        
        with mss.mss() as sct:
            while self._esta_corriendo and time.time() < tiempo_fin:
                
                tiempo_restante = tiempo_fin - time.time()
                self.tiempo_restante_actualizado.emit(time.strftime('%H:%M:%S', time.gmtime(tiempo_restante)))
                
                try:
                    # 1. Capturar pantalla
                    monitor = sct.monitors[1] # Monitor principal
                    sct_img = sct.grab(monitor)
                    screen_np = np.array(sct_img)
                    screen_np_bgr = cv2.cvtColor(screen_np, cv2.COLOR_BGRA2BGR)

                    # 2. Lógica de automatización
                    # Iterar sobre los elementos que el usuario configuró
                    for nombre_elem, config in self.config_elementos.items():
                        if not self._esta_corriendo: break # Salir si se detuvo
                        
                        self.estado_actualizado.emit(f"Buscando '{nombre_elem}'...")
                        
                        # Definir la zona de búsqueda
                        # Intenta buscar una zona específica, si no, busca en toda la pantalla
                        zona_busqueda_nombre = f"{nombre_elem}_ZonaBusqueda"
                        rect_busqueda = self.zonas_calibradas.get(zona_busqueda_nombre)
                        
                        imagen_a_buscar = screen_np_bgr
                        offset_x, offset_y = 0, 0

                        if rect_busqueda:
                            x, y, w, h = rect_busqueda
                            imagen_a_buscar = screen_np_bgr[y:y+h, x:x+w]
                            offset_x, offset_y = x, y
                            log.debug(f"Buscando en zona calibrada: {zona_busqueda_nombre}")
                        
                        coincidencias = find_template(imagen_a_buscar, config["path_template"], threshold=0.70)
                        
                        if coincidencias:
                            msg = f"'{nombre_elem}' encontrado en {len(coincidencias)} ubicaciones."
                            log.info(msg)
                            self.log_generado.emit(msg)
                            self.contadores["elementos_encontrados"] += 1
                            self.contadores_actualizados.emit("elementos_encontrados", self.contadores["elementos_encontrados"])
                            
                            # Clicar en la primera coincidencia
                            x, y, w, h = coincidencias[0]
                            # Ajustar coordenadas si se usó una zona de búsqueda
                            rect_clic = (x + offset_x, y + offset_y, w, h)
                            
                            click_en_rect(rect_clic, modo_dry_run=self.modo_dry_run)
                            self.contadores["clics"] += 1
                            self.contadores_actualizados.emit("clics", self.contadores["clics"])
                            
                            variar_tiempo_espera(1.5, 3.0, self.modo_dry_run)
                            
                        else:
                            log.debug(f"'{nombre_elem}' no encontrado.")
                            # Aquí iría la lógica de reintento (ej: buscar botón "cambiar pantalla")
                        
                        variar_tiempo_espera(0.5, 1.0, self.modo_dry_run) # Pequeña pausa entre elementos

                    # 3. Lógica de "Reparación" / Backoff
                    # (Ejemplo de cómo usar una zona calibrada fija)
                    if "BotonReparar" in self.zonas_calibradas:
                        # (Aquí iría la lógica de cuándo reparara)
                        # ej: if self.contadores["errores"] > 5:
                        pass
                        
                except pydirectinput.FailSafeException:
                    self.detener_emergencia()
                    break # Salir del bucle while
                except Exception as e:
                    msg = f"Error crítico en el bucle: {e}"
                    log.error(msg, exc_info=True)
                    self.log_generado.emit(msg)
                    self.contadores["errores"] += 1
                    self.contadores_actualizados.emit("errores", self.contadores["errores"])
                    variar_tiempo_espera(5.0, 10.0, self.modo_dry_run)

        msg = "Prueba finalizada (tiempo agotado o detenida)."
        log.info(msg)
        self.log_generado.emit(msg)
        self.detener()

    def detener(self):
        if self._esta_corriendo:
            self._esta_corriendo = False
            # if self.hotkey_registrada:
            #     try:
            #         keyboard.remove_hotkey(HOTKEY_PANICO)
            #         self.hotkey_registrada = False
            #         log.info("Hotkey de pánico des-registrada.")
            #     except Exception as e:
            #         log.warning(f"Error al remover hotkey: {e}")
            self.finalizado.emit()

    @Slot()
    def detener_emergencia(self):
        if self._esta_corriendo:
            msg = "¡DETENCIÓN DE EMERGENCIA (HOTKEY) ACTIVADA!"
            log.critical(msg)
            self.log_generado.emit(msg)
            self.estado_actualizado.emit("DETENIDO (PÁNICO)")
            self.detener()