from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                               QPushButton, QLabel, QGroupBox, QCheckBox, 
                               QComboBox, QPlainTextEdit)
from PySide6.QtGui import QFont, QColor
from PySide6.QtCore import Slot, Qt
import os
import re
import logging
import time

from app.logic.worker_automatizacion import AutomationWorker
from app.utils.config import RUTA_PERFILES

log = logging.getLogger("QA_Tool.ejecucion")

class EjecucionTab(QWidget):
    # Pasar referencias a las otras pestañas para obtener datos
    def __init__(self, tab_elementos):
        super().__init__()
        
        self.tab_elementos_ref = tab_elementos
        self.worker_thread = None

        layout = QVBoxLayout(self)
        
        # --- Grupo de Configuración ---
        group_config = QGroupBox("Configuración de Ejecución")
        config_layout = QFormLayout()
        
        self.input_duracion = QLineEdit("30")
        self.input_duracion.setPlaceholderText("HH:MM o minutos (ej: 1:30 o 90)")
        
        self.combo_perfil = QComboBox()
        self.actualizar_lista_perfiles()
        
        self.check_dry_run = QCheckBox("Modo Dry-Run (Solo logs, sin clics)")
        self.check_dry_run.setChecked(True)
        
        config_layout.addRow("Duración de prueba:", self.input_duracion)
        config_layout.addRow("Perfil de Calibración:", self.combo_perfil)
        config_layout.addRow(self.check_dry_run)
        
        group_config.setLayout(config_layout)
        
        # --- Grupo de Control ---
        group_control = QGroupBox("Control")
        control_layout = QVBoxLayout()
        
        self.btn_iniciar = QPushButton("Iniciar Prueba")
        self.btn_iniciar.setStyleSheet("background-color: #4CAF50; color: white;")
        
        self.btn_detener = QPushButton("Detener (Panic / Stop All)")
        self.btn_detener.setStyleSheet("background-color: #f44336; color: white;")
        self.btn_detener.setEnabled(False)
        
        control_layout.addWidget(self.btn_iniciar)
        control_layout.addWidget(self.btn_detener)
        
        group_control.setLayout(control_layout)
        
        # --- Grupo de Estado ---
        group_estado = QGroupBox("Estado y Contadores")
        estado_layout = QFormLayout()
        
        self.label_estado = QLabel("Detenido")
        self.label_estado.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.label_tiempo_restante = QLabel("00:00:00")
        
        # Contadores
        self.label_clics = QLabel("0")
        self.label_elementos = QLabel("0")
        self.label_errores = QLabel("0")
        
        estado_layout.addRow("Estado:", self.label_estado)
        estado_layout.addRow("Tiempo Restante:", self.label_tiempo_restante)
        estado_layout.addRow("Acciones (Clics):", self.label_clics)
        estado_layout.addRow("Elementos Encontrados:", self.label_elementos)
        estado_layout.addRow("Errores:", self.label_errores)
        
        group_estado.setLayout(estado_layout)

        # --- Grupo de Log ---
        group_log = QGroupBox("Log de Ejecución")
        log_layout = QVBoxLayout()
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Courier New", 9))
        self.log_output.setMaximumBlockCount(200) # Evitar que crezca indefinidamente
        log_layout.addWidget(self.log_output)
        group_log.setLayout(log_layout)
        
        # Añadir widgets al layout principal
        layout.addWidget(group_config)
        layout.addWidget(group_control)
        layout.addWidget(group_estado)
        layout.addWidget(group_log, 1) # Darle más espacio al log

        # Conexiones
        self.btn_iniciar.clicked.connect(self.iniciar_ejecucion)
        self.btn_detener.clicked.connect(self.detener_ejecucion)
        self.combo_perfil.activated.connect(self.actualizar_lista_perfiles) # Recargar lista

    def actualizar_lista_perfiles(self):
        """Lee los perfiles desde la carpeta."""
        self.combo_perfil.clear()
        try:
            perfiles = [f for f in os.listdir(RUTA_PERFILES) if f.endswith(".json")]
            self.combo_perfil.addItems(perfiles)
        except FileNotFoundError:
            self.log_gui("Advertencia: No se encontró la carpeta de perfiles.")
            
    def parse_duracion(self, texto_duracion):
        """Convierte 'HH:MM' o 'MM' a segundos."""
        match_hhmm = re.match(r"(\d+):(\d{1,2})", texto_duracion)
        match_mm = re.match(r"(\d+)", texto_duracion)
        
        if match_hhmm:
            horas = int(match_hhmm.group(1))
            minutos = int(match_hhmm.group(2))
            return (horas * 3600) + (minutos * 60)
        elif match_mm:
            minutos = int(match_mm.group(1))
            return minutos * 60
        else:
            raise ValueError("Formato de duración inválido.")

    def iniciar_ejecucion(self):
        # 1. Obtener configuración de esta pestaña
        try:
            duracion_seg = self.parse_duracion(self.input_duracion.text())
        except ValueError:
            self.log_gui("Error: Formato de duración inválido. Use 'HH:MM' o 'Minutos'.")
            return
            
        perfil_seleccionado = self.combo_perfil.currentText()
        if not perfil_seleccionado:
            self.log_gui("Error: Debe seleccionar un perfil de calibración.")
            return

        config_ejecucion = {
            "duracion_seg": duracion_seg,
            "dry_run": self.check_dry_run.isChecked()
        }
        
        # 2. Obtener configuración de la pestaña de elementos
        config_elementos = self.tab_elementos_ref.get_configuracion_ejecucion()
        if not config_elementos:
            self.log_gui("Advertencia: No hay elementos seleccionados para testear.")
            # Podríamos detenernos, pero es mejor continuar (quizás solo prueba timers)
            
        self.log_gui("Iniciando worker de automatización...")
        
        # 3. Resetear GUI
        self.limpiar_contadores()
        self.btn_iniciar.setEnabled(False)
        self.btn_detener.setEnabled(True)
        self.label_estado.setText("Ejecutando...")
        self.label_estado.setStyleSheet("color: green;")
        
        # 4. Crear e iniciar el Thread
        self.worker_thread = AutomationWorker(
            config_ejecucion=config_ejecucion,
            config_elementos=config_elementos,
            perfil_calibracion=perfil_seleccionado
        )
        
        # Conectar señales del worker a slots de la GUI
        self.worker_thread.estado_actualizado.connect(self.actualizar_estado)
        self.worker_thread.tiempo_restante_actualizado.connect(self.actualizar_tiempo)
        self.worker_thread.log_generado.connect(self.log_gui)
        self.worker_thread.contadores_actualizados.connect(self.actualizar_contador)
        self.worker_thread.finalizado.connect(self.ejecucion_finalizada)
        
        self.worker_thread.start()

    @Slot()
    def detener_ejecucion(self):
        self.log_gui("Solicitando detención del worker...")
        if self.worker_thread:
            self.worker_thread.detener() # Llama a la función de parada segura

    @Slot(str)
    def log_gui(self, mensaje):
        """Añade un mensaje al QPlainTextEdit de la GUI."""
        self.log_output.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {mensaje}")

    @Slot(str)
    def actualizar_estado(self, estado):
        self.label_estado.setText(estado)

    @Slot(str)
    def actualizar_tiempo(self, tiempo_str):
        self.label_tiempo_restante.setText(tiempo_str)
        
    @Slot(str, int)
    def actualizar_contador(self, nombre_contador, valor):
        if nombre_contador == "clics":
            self.label_clics.setText(str(valor))
        elif nombre_contador == "elementos_encontrados":
            self.label_elementos.setText(str(valor))
        elif nombre_contador == "errores":
            self.label_errores.setText(str(valor))

    @Slot()
    def ejecucion_finalizada(self):
        """Se activa cuando el thread confirma que ha terminado."""
        self.log_gui("Worker finalizado.")
        self.btn_iniciar.setEnabled(True)
        self.btn_detener.setEnabled(False)
        self.label_estado.setText("Detenido")
        self.label_estado.setStyleSheet("color: red;")
        self.label_tiempo_restante.setText("00:00:00")
        self.worker_thread = None

    def limpiar_contadores(self):
        self.label_clics.setText("0")
        self.label_elementos.setText("0")
        self.label_errores.setText("0")
        self.log_output.clear()