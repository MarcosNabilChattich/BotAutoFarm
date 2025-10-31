import sys
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QFileDialog, QLineEdit, QComboBox, 
                               QGroupBox, QRubberBand, QScrollArea)
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QRect, QPoint, QSize
import mss
import mss.tools
import json
import os
import logging

from app.utils.config import guardar_perfil, cargar_perfil, RUTA_PERFILES

log = logging.getLogger("QA_Tool.calibracion")

# Widget de Label que permite dibujar rectángulos
class CalibrationLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.origin = None
        self.rubber_band = None
        self.current_rect = QRect()
        self.parent_tab = parent

    def set_parent_tab(self, tab):
        self.parent_tab = tab

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.pos()
            if not self.rubber_band:
                self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self)
            self.rubber_band.setGeometry(QRect(self.origin, QSize()))
            self.rubber_band.show()
            log.debug(f"Inicio de selección de área en {self.origin}")

    def mouseMoveEvent(self, event):
        if self.rubber_band and self.origin:
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.rubber_band:
            self.current_rect = self.rubber_band.geometry()
            self.rubber_band.hide()
            self.origin = None
            # Enviar el rectángulo (x, y, w, h) a la pestaña principal
            if self.parent_tab:
                log.debug(f"Área seleccionada: {self.current_rect}")
                self.parent_tab.set_current_coords(self.current_rect)

class CalibracionTab(QWidget):
    def __init__(self):
        super().__init__()
        self.zonas_calibradas = {} # { "nombre_zona": (x, y, w, h), ... }
        self.current_rect = None
        self.current_pixmap = None # Almacenar pixmap original

        layout = QHBoxLayout(self)
        
        # --- Columna Izquierda (Controles) ---
        controles_layout = QVBoxLayout()
        controles_layout.setSpacing(15)
        
        # Cargar/Guardar Perfil
        group_perfil = QGroupBox("Perfiles de Calibración")
        perfil_layout = QVBoxLayout()
        self.combo_perfil = QComboBox()
        self.actualizar_lista_perfiles()
        
        btn_cargar_perfil = QPushButton("Cargar Perfil")
        btn_cargar_perfil.clicked.connect(self.cargar_perfil_seleccionado)
        
        self.nombre_perfil_input = QLineEdit("nuevo_perfil")
        btn_guardar_perfil = QPushButton("Guardar Perfil Actual")
        btn_guardar_perfil.clicked.connect(self.guardar_perfil_actual)
        
        perfil_layout.addWidget(QLabel("Seleccionar perfil existente:"))
        perfil_layout.addWidget(self.combo_perfil)
        perfil_layout.addWidget(btn_cargar_perfil)
        perfil_layout.addSpacing(10)
        perfil_layout.addWidget(QLabel("Guardar como nuevo perfil (ej: emulador_1920x1080):"))
        perfil_layout.addWidget(self.nombre_perfil_input)
        perfil_layout.addWidget(btn_guardar_perfil)
        group_perfil.setLayout(perfil_layout)

        # Cargar Imagen
        group_imagen = QGroupBox("Fuente de Imagen")
        imagen_layout = QVBoxLayout()
        btn_capturar_pantalla = QPushButton("Capturar Pantalla Completa")
        btn_capturar_pantalla.clicked.connect(self.capturar_pantalla)
        btn_cargar_imagen_mock = QPushButton("Cargar Imagen de Prueba (desde test_images/)")
        btn_cargar_imagen_mock.clicked.connect(self.cargar_imagen_mock)
        imagen_layout.addWidget(btn_capturar_pantalla)
        imagen_layout.addWidget(btn_cargar_imagen_mock)
        group_imagen.setLayout(imagen_layout)

        # Definir Zonas
        group_zonas = QGroupBox("Definir Zonas")
        zonas_layout = QVBoxLayout()
        self.nombre_zona_input = QLineEdit("ej: BotonCambiarPantalla")
        self.coords_label = QLabel("Coords (x, y, w, h): No definida")
        btn_guardar_zona = QPushButton("Guardar Zona Actual")
        btn_guardar_zona.clicked.connect(self.guardar_zona)
        
        zonas_layout.addWidget(QLabel("Nombre de la Zona:"))
        zonas_layout.addWidget(self.nombre_zona_input)
        zonas_layout.addWidget(self.coords_label)
        zonas_layout.addWidget(btn_guardar_zona)
        group_zonas.setLayout(zonas_layout)

        controles_layout.addWidget(group_perfil)
        controles_layout.addWidget(group_imagen)
        controles_layout.addWidget(group_zonas)
        controles_layout.addStretch()

        # --- Columna Derecha (Visualizador) ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.image_label = CalibrationLabel()
        self.image_label.set_parent_tab(self)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll_area.setWidget(self.image_label)
        
        layout.addLayout(controles_layout, 1) # 1 parte de espacio
        layout.addWidget(scroll_area, 3)         # 3 partes de espacio

    def set_pixmap(self, pixmap):
        """Establece el pixmap base y lo muestra."""
        self.current_pixmap = pixmap
        self.image_label.setPixmap(self.current_pixmap)
        
    def capturar_pantalla(self):
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[0] # Captura todos los monitores como uno solo
                sct_img = sct.grab(monitor)
                log.info(f"Pantalla capturada: {sct_img.size}")
                
                # Convertir a QPixmap
                img_bytes = mss.tools.to_png(sct_img.rgb, sct_img.size)
                pixmap = QPixmap()
                pixmap.loadFromData(img_bytes)
                self.set_pixmap(pixmap)
                self.zonas_calibradas.clear() # Limpiar zonas al tomar nueva captura
                
        except Exception as e:
            log.error(f"Error al capturar pantalla: {e}")
            self.coords_label.setText(f"Error: {e}")

    def cargar_imagen_mock(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Imagen Mock", "test_images/", "Images (*.png *.jpg *.bmp)"
        )
        if filepath:
            pixmap = QPixmap(filepath)
            self.set_pixmap(pixmap)
            self.zonas_calibradas.clear() # Limpiar zonas al cargar nueva imagen
            log.info(f"Imagen mock cargada: {filepath}")

    def set_current_coords(self, rect):
        self.current_rect = rect
        self.coords_label.setText(f"Coords: ({rect.x()}, {rect.y()}, {rect.width()}, {rect.height()})")

    def guardar_zona(self):
        nombre_zona = self.nombre_zona_input.text()
        if not nombre_zona or not self.current_rect:
            self.coords_label.setText("Error: Define un nombre y selecciona un área")
            log.warning("Intento de guardar zona sin nombre o área.")
            return
            
        coords = (self.current_rect.x(), self.current_rect.y(), self.current_rect.width(), self.current_rect.height())
        self.zonas_calibradas[nombre_zona] = coords
        log.info(f"Zona guardada: {nombre_zona} -> {coords}")
        self.coords_label.setText(f"Guardado: {nombre_zona}")
        
        # Dibujar el rectángulo guardado
        self.dibujar_rectangulos_guardados()

    def dibujar_rectangulos_guardados(self):
        if not self.current_pixmap:
            return
            
        # Empezar desde la imagen original limpia
        temp_pixmap = self.current_pixmap.copy()
        painter = QPainter(temp_pixmap)
        font = self.font()
        font.setPointSize(10)
        painter.setFont(font)
        
        for nombre, (x, y, w, h) in self.zonas_calibradas.items():
            rect = QRect(x, y, w, h)
            
            # Dibujar rectángulo
            painter.setPen(QColor(255, 0, 0, 200)) # Rojo semi-transparente
            painter.drawRect(rect)
            
            # Dibujar texto con fondo
            painter.setPen(Qt.GlobalColor.white)
            text_rect = QRect(rect.topLeft() - QPoint(0, 15), QSize(len(nombre) * 8, 15))
            painter.fillRect(text_rect, QColor(0, 0, 0, 150)) # Fondo negro semi-transparente
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, nombre)
            
        painter.end()
        self.image_label.setPixmap(temp_pixmap)

    def guardar_perfil_actual(self):
        nombre = self.nombre_perfil_input.text()
        if not nombre.endswith(".json"):
            nombre += ".json"
        
        if guardar_perfil(nombre, self.zonas_calibradas):
            log.info(f"Perfil guardado: {nombre}")
            self.actualizar_lista_perfiles()
            self.combo_perfil.setCurrentText(nombre)
        else:
            log.error(f"No se pudo guardar el perfil {nombre}")

    def cargar_perfil_seleccionado(self):
        nombre = self.combo_perfil.currentText()
        if not nombre:
            return
            
        data = cargar_perfil(nombre)
        if data:
            self.zonas_calibradas = data
            self.nombre_perfil_input.setText(nombre.replace(".json", ""))
            self.dibujar_rectangulos_guardados()
            log.info(f"Perfil cargado: {nombre}")
        else:
            log.warning(f"No se pudo cargar el perfil {nombre}")

    def actualizar_lista_perfiles(self):
        self.combo_perfil.clear()
        try:
            perfiles = [f for f in os.listdir(RUTA_PERFILES) if f.endswith(".json")]
            self.combo_perfil.addItems(perfiles)
        except FileNotFoundError:
            log.warning(f"No se encontró el directorio de perfiles: {RUTA_PERFILES}")