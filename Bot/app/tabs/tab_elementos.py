from PySide6.QtWidgets import (QWidget, QHBoxLayout, QListWidget, QTableWidget,
                               QTableWidgetItem, QAbstractItemView, QHeaderView,
                               QSpinBox, QGroupBox, QVBoxLayout, QListWidgetItem)
from PySide6.QtCore import Qt
import os


Ruta_TEMPLATES = "resources/templates"

class ElementosTab(QWidget):
    def __init__(self):
        super().__init__()
        
        self.elementos_config = {} # { "NombreElemento": {"max_permitido": 10, "path": "..."} }
        self.cargar_elementos_desde_templates()

        layout = QHBoxLayout(self)
        
        # 1. Lista de elementos a testear
        group_seleccionar = QGroupBox("Seleccionar Elementos (desde /resources/templates/)")
        seleccionar_layout = QVBoxLayout()
        
        self.lista_elementos = QListWidget()
        for nombre in self.elementos_config.keys():
            item = QListWidgetItem(nombre)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.lista_elementos.addItem(item)
            
        self.lista_elementos.itemChanged.connect(self.actualizar_panel_inferior)
        seleccionar_layout.addWidget(self.lista_elementos)
        group_seleccionar.setLayout(seleccionar_layout)
        
        # 2. Panel inferior con niveles
        group_niveles = QGroupBox("Configuración de Niveles (Opcional, para OCR/lógica)")
        niveles_layout = QVBoxLayout()
        self.tabla_niveles = QTableWidget()
        self.tabla_niveles.setColumnCount(4)
        self.tabla_niveles.setHorizontalHeaderLabels(["Elemento", "Nivel Mínimo", "Nivel Máximo", "Máx. Permitido"])
        self.tabla_niveles.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabla_niveles.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        
        niveles_layout.addWidget(self.tabla_niveles)
        group_niveles.setLayout(niveles_layout)

        layout.addWidget(group_seleccionar, 1) # 1 parte de espacio
        layout.addWidget(group_niveles, 2)     # 2 partes de espacio
        
        self.actualizar_panel_inferior()

    def cargar_elementos_desde_templates(self):
        """Escanea la carpeta de templates y los carga en la configuración."""
        self.elementos_config.clear()
        try:
            for f in os.listdir(Ruta_TEMPLATES):
                if f.endswith((".png", ".jpg")):
                    nombre = os.path.splitext(f)[0]
                    # Datos ficticios - esto debería cargarse de un config
                    max_permitido = 10 
                    self.elementos_config[nombre] = {
                        "max_permitido": max_permitido,
                        "path": os.path.join(Ruta_TEMPLATES, f)
                    }
        except FileNotFoundError:
            print(f"Advertencia: No se encontró el directorio {Ruta_TEMPLATES}")

    def actualizar_panel_inferior(self):
        """Re-dibuja la tabla de niveles basado en los elementos chequeados."""
        self.tabla_niveles.setRowCount(0)
        
        for i in range(self.lista_elementos.count()):
            item = self.lista_elementos.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                nombre = item.text()
                config = self.elementos_config.get(nombre)
                
                if not config:
                    continue
                
                row = self.tabla_niveles.rowCount()
                self.tabla_niveles.insertRow(row)
                
                # Nombre
                item_nombre = QTableWidgetItem(nombre)
                item_nombre.setFlags(item_nombre.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # Max Permitido (preconfigurado)
                item_max_permitido = QTableWidgetItem(str(config["max_permitido"]))
                item_max_permitido.setFlags(item_max_permitido.flags() & ~Qt.ItemFlag.ItemIsEditable)
                
                # SpinBox Mínimo
                spin_min = QSpinBox()
                spin_min.setMinimum(0)
                spin_min.setMaximum(config["max_permitido"])
                spin_min.setValue(1)
                
                # SpinBox Máximo
                spin_max = QSpinBox()
                spin_max.setMinimum(0)
                spin_max.setMaximum(config["max_permitido"])
                spin_max.setValue(config["max_permitido"])

                # Validación de rango
                spin_min.valueChanged.connect(lambda val, s_max=spin_max: s_max.setMinimum(val))
                spin_max.valueChanged.connect(lambda val, s_min=spin_min: s_min.setMaximum(val))

                self.tabla_niveles.setItem(row, 0, item_nombre)
                self.tabla_niveles.setCellWidget(row, 1, spin_min)
                self.tabla_niveles.setCellWidget(row, 2, spin_max)
                self.tabla_niveles.setItem(row, 3, item_max_permitido)

    def get_configuracion_ejecucion(self):
        """Devuelve la configuración de los elementos seleccionados."""
        config_final = {}
        for i in range(self.tabla_niveles.rowCount()):
            nombre = self.tabla_niveles.item(i, 0).text()
            spin_min = self.tabla_niveles.cellWidget(i, 1)
            spin_max = self.tabla_niveles.cellWidget(i, 2)
            
            if nombre in self.elementos_config:
                config_final[nombre] = {
                    "nivel_min": spin_min.value(),
                    "nivel_max": spin_max.value(),
                    "max_permitido": self.elementos_config[nombre]["max_permitido"],
                    "path_template": self.elementos_config[nombre]["path"]
                }
        return config_final