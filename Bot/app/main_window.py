from PySide6.QtWidgets import QMainWindow, QTabWidget, QMessageBox
from PySide6.QtCore import QSize, Slot
import logging
import keyboard  # <--- 1. IMPORTA KEYBOARD

from app.tabs.tab_elementos import ElementosTab
from app.tabs.tab_ejecucion import EjecucionTab
from app.tabs.tab_calibracion import CalibracionTab

log = logging.getLogger("QA_Tool.main_window")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        log.info("Inicializando MainWindow...")
        self.setWindowTitle("Herramienta de QA Local para Android (v0.1)")
        self.setMinimumSize(QSize(900, 700))

        # Contenedor central de pestañas
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Instanciar pestañas
        self.elementos_tab = ElementosTab()
        self.ejecucion_tab = EjecucionTab(tab_elementos=self.elementos_tab)
        self.calibracion_tab = CalibracionTab()

        # Añadir pestañas
        self.tab_widget.addTab(self.ejecucion_tab, "Modo de Ejecución")
        self.tab_widget.addTab(self.elementos_tab, "Configurar Elementos")
        self.tab_widget.addTab(self.calibracion_tab, "Calibración y Perfiles")
        
        # --- 2. REGISTRA LOS HOTKEYS GLOBALES ---
        self.setup_global_hotkeys()
        
        log.info("Pestañas añadidas y hotkeys registrados.")

    # --- 3. AÑADE ESTAS NUEVAS FUNCIONES ---
    
    def setup_global_hotkeys(self):
        """Registra las teclas rápidas globales para la aplicación."""
        try:
            # Tu nueva función de Iniciar/Detener
            keyboard.add_hotkey("f6", self.toggle_automation_f6)
            
            # La función de pánico que movimos aquí
            keyboard.add_hotkey("ctrl+alt+q", self.trigger_panic_hotkey)
            
            log.info("Hotkeys globales (F6 y Ctrl+Alt+Q) registrados correctamente.")
            
        except Exception as e:
            # Esto puede fallar si no se ejecuta como admin en algunos SO
            log.warning(f"No se pudieron registrar hotkeys globales: {e}")
            QMessageBox.warning(self, "Error de Hotkeys", 
                f"No se pudieron registrar las hotkeys globales (F6, Ctrl+Alt+Q).\n"
                f"Es posible que necesites ejecutar como administrador.\nError: {e}")

    @Slot()
    def toggle_automation_f6(self):
        """Inicia o detiene la automatización (llamado por F6)."""
        log.debug("¡Hotkey F6 presionada!")
        
        # Comprueba si el worker está corriendo
        if self.ejecucion_tab.worker_thread:
            # Si está corriendo, llama a la función de DETENER
            log.info("F6: Solicitando detención (worker activo).")
            self.ejecucion_tab.detener_ejecucion()
        else:
            # Si está detenido, llama a la función de INICIAR
            log.info("F6: Solicitando inicio (worker inactivo).")
            # Cambia a la pestaña de ejecución por comodidad
            self.tab_widget.setCurrentWidget(self.ejecucion_tab)
            self.ejecucion_tab.iniciar_ejecucion()

    @Slot()
    def trigger_panic_hotkey(self):
        """Activa la detención de emergencia (llamado por Ctrl+Alt+Q)."""
        log.warning("¡Hotkey DE PÁNICO (Ctrl+Alt+Q) presionada!")
        
        # Solo hace algo si el worker está corriendo
        if self.ejecucion_tab.worker_thread:
            # Llama directamente a la función de emergencia del worker
            self.ejecucion_tab.worker_thread.detener_emergencia()

    # ... (El resto del archivo, incluyendo closeEvent) ...

    def closeEvent(self, event):
        """Sobrescribe el evento de cierre de la ventana."""
        
        # --- 4. AÑADE ESTA LÍNEA PARA LIMPIAR LOS HOTKEYS AL CERRAR ---
        keyboard.unhook_all_hotkeys()
        
        if self.ejecucion_tab.worker_thread:
            log.warning("Intento de cierre mientras el worker está activo.")
            reply = QMessageBox.question(
                self,
                "Confirmar Salida",
                "Una prueba está en ejecución.\n¿Estás seguro de que quieres salir? Esto detendrá la prueba.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.ejecucion_tab.detener_ejecucion()
                event.accept() 
            else:
                event.ignore() 
        else:
            event.accept()