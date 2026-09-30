"""Ventana principal de la aplicación"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QMessageBox, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QMenu
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QShortcut, QKeySequence
from pathlib import Path
import sys
import os
import json
import tempfile
import logging
import numpy as np
from src.utils.logger import setup_logger
from src.utils.constants import DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
from src.core.mesh_loader import MeshLoader, STLParseError, OBJParseError, GeometryValidationError
from src.core.measurements import (
    compute_support_plane,
    compute_arch_height,
    compute_plane_distance,
    compute_plane_footprint,
    compute_height_map,
    height_map_to_colors,
    MeasurementError,
)
from src.core.report_export import export_measurements_csv, export_report_pdf
from src.core.project_io import save_project, load_project
from src.models.foot_model import Measurement
from src.ui.widgets.view_3d import VTK3DView

logger = setup_logger(__name__)

# Colores de marcadores/líneas por tipo de medición — se usan tanto al
# picking en vivo como al restaurar mediciones de un proyecto guardado, para
# que se vean igual en ambos casos.
PLANE_MARKER_COLOR = (0.2, 0.8, 1.0)
HEIGHT_MARKER_COLOR = (1.0, 0.6, 0.0)
HEIGHT_LINE_COLOR = (1.0, 0.8, 0.0)
DISTANCE_MARKER_COLOR = (0.9, 0.2, 0.9)
DISTANCE_LINE_COLOR = (0.2, 0.9, 0.5)


class MainWindow(QMainWindow):
    """Ventana principal de la aplicación"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Visualización de Pies - MVP")
        self.setGeometry(100, 100, DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)
        self.current_model = None
        self.current_file = None
        self.mesh_loader = MeshLoader()

        # Estado de medición (plano de apoyo + mediciones acumuladas)
        self.support_plane = None
        self._pick_mode = None  # None | 'plane' | 'height' | 'distance'
        self._plane_points = []
        self._distance_points = []
        self._distance_marker_actors = []  # Marcadores del punto 1/2 de una distancia a medio pickear
        self.measurements = []  # Lista de Measurement (altura de arco, distancia en el plano)
        # True si hay mediciones/plano que todavía no se guardaron como proyecto
        self._unsaved_changes = False
        self._create_ui()
        self._create_menu()
        self._create_toolbar()
        self._create_status_bar()
        self._connect_signals()
        self._create_shortcuts()
        logger.info("MainWindow inicializada")

    def _mark_dirty(self):
        """Marcar que hay cambios (plano/mediciones) sin guardar como proyecto"""
        self._unsaved_changes = True

    def _create_ui(self):
        """Crear widgets principales"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas = VTK3DView()
        main_layout.addWidget(self.canvas, 1)
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        view_label = QLabel("Vistas Estándar:")
        right_layout.addWidget(view_label)
        self.btn_anterior = QPushButton("Anterior (Punta)")
        self.btn_anterior.clicked.connect(lambda: self.canvas.set_view_anterior())
        right_layout.addWidget(self.btn_anterior)
        self.btn_posterior = QPushButton("Posterior (Talón)")
        self.btn_posterior.clicked.connect(lambda: self.canvas.set_view_posterior())
        right_layout.addWidget(self.btn_posterior)
        self.btn_plantar = QPushButton("Plantar (Abajo)")
        self.btn_plantar.clicked.connect(lambda: self.canvas.set_view_plantar())
        right_layout.addWidget(self.btn_plantar)
        self.btn_dorsal = QPushButton("Dorsal (Arriba)")
        self.btn_dorsal.clicked.connect(lambda: self.canvas.set_view_dorsal())
        right_layout.addWidget(self.btn_dorsal)
        self.btn_medial = QPushButton("Medial (Interno)")
        self.btn_medial.clicked.connect(lambda: self.canvas.set_view_medial())
        right_layout.addWidget(self.btn_medial)
        self.btn_lateral = QPushButton("Lateral (Externo)")
        self.btn_lateral.clicked.connect(lambda: self.canvas.set_view_lateral())
        right_layout.addWidget(self.btn_lateral)
        self.btn_isometric = QPushButton("Isométrica")
        self.btn_isometric.clicked.connect(lambda: self.canvas.set_view_isometric())
        right_layout.addWidget(self.btn_isometric)

        measurements_label = QLabel("Mediciones (doble click para renombrar, click derecho para eliminar):")
        measurements_label.setWordWrap(True)
        right_layout.addWidget(measurements_label)
        self.measurement_table = QTableWidget(0, 2)
        self.measurement_table.setHorizontalHeaderLabels(["Medición", "Valor"])
        self.measurement_table.verticalHeader().setVisible(False)
        self.measurement_table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked)
        self.measurement_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.measurement_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.measurement_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.measurement_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.measurement_table.customContextMenuRequested.connect(self._show_measurement_context_menu)
        self.measurement_table.itemChanged.connect(self._on_measurement_name_edited)
        right_layout.addWidget(self.measurement_table, 1)

        right_panel.setLayout(right_layout)
        right_panel.setMaximumWidth(260)
        right_panel.setMinimumWidth(220)
        main_layout.addWidget(right_panel)
        central_widget.setLayout(main_layout)

    def _create_menu(self):
        """Crear barra de menú"""
        menubar = self.menuBar()
        file_menu = menubar.addMenu("Archivo")
        open_action = QAction("Abrir malla (STL/OBJ)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        file_menu.addSeparator()

        open_project_action = QAction("Abrir proyecto...", self)
        open_project_action.triggered.connect(self.open_project_dialog)
        file_menu.addAction(open_project_action)

        self.save_project_action = QAction("Guardar proyecto...", self)
        self.save_project_action.setEnabled(False)
        self.save_project_action.triggered.connect(self.save_project_dialog)
        file_menu.addAction(self.save_project_action)
        file_menu.addSeparator()

        self.export_csv_action = QAction("Exportar mediciones (CSV)...", self)
        self.export_csv_action.setEnabled(False)
        self.export_csv_action.triggered.connect(self.export_measurements_csv_dialog)
        file_menu.addAction(self.export_csv_action)

        self.export_pdf_action = QAction("Exportar informe (PDF)...", self)
        self.export_pdf_action.setEnabled(False)
        self.export_pdf_action.triggered.connect(self.export_report_pdf_dialog)
        file_menu.addAction(self.export_pdf_action)
        file_menu.addSeparator()

        exit_action = QAction("Salir", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        view_menu = menubar.addMenu("Ver")
        dorsal_action = QAction("Dorsal (Arriba)", self)
        dorsal_action.triggered.connect(lambda: self.canvas.set_view_dorsal())
        view_menu.addAction(dorsal_action)
        plantar_action = QAction("Plantar (Abajo)", self)
        plantar_action.triggered.connect(lambda: self.canvas.set_view_plantar())
        view_menu.addAction(plantar_action)
        medial_action = QAction("Medial (Interno)", self)
        medial_action.triggered.connect(lambda: self.canvas.set_view_medial())
        view_menu.addAction(medial_action)
        lateral_action = QAction("Lateral (Externo)", self)
        lateral_action.triggered.connect(lambda: self.canvas.set_view_lateral())
        view_menu.addAction(lateral_action)
        anterior_action = QAction("Anterior (Punta)", self)
        anterior_action.triggered.connect(lambda: self.canvas.set_view_anterior())
        view_menu.addAction(anterior_action)
        posterior_action = QAction("Posterior (Talón)", self)
        posterior_action.triggered.connect(lambda: self.canvas.set_view_posterior())
        view_menu.addAction(posterior_action)
        help_menu = menubar.addMenu("Ayuda")
        help_action = QAction("Acerca de", self)
        help_action.triggered.connect(self.show_about)
        help_menu.addAction(help_action)

    def _create_toolbar(self):
        """Crear barra de herramientas"""
        toolbar = self.addToolBar("Herramientas")
        toolbar.setMovable(False)
        dorsal_action = QAction("Dorsal", self)
        dorsal_action.triggered.connect(lambda: self.canvas.set_view_dorsal())
        toolbar.addAction(dorsal_action)
        plantar_action = QAction("Plantar", self)
        plantar_action.triggered.connect(lambda: self.canvas.set_view_plantar())
        toolbar.addAction(plantar_action)
        medial_action = QAction("Medial", self)
        medial_action.triggered.connect(lambda: self.canvas.set_view_medial())
        toolbar.addAction(medial_action)
        lateral_action = QAction("Lateral", self)
        lateral_action.triggered.connect(lambda: self.canvas.set_view_lateral())
        toolbar.addAction(lateral_action)

        self.action_show_axes = QAction("Ejes", self)
        self.action_show_axes.setCheckable(True)
        self.action_show_axes.toggled.connect(lambda checked: self.canvas.show_axes(checked))
        toolbar.addAction(self.action_show_axes)

        toolbar.addSeparator()

        self.action_define_plane = QAction("Definir plano de apoyo", self)
        self.action_define_plane.setCheckable(True)
        self.action_define_plane.setEnabled(False)
        self.action_define_plane.triggered.connect(self._toggle_define_plane)
        toolbar.addAction(self.action_define_plane)

        self.action_show_plane = QAction("Mostrar plano", self)
        self.action_show_plane.setCheckable(True)
        self.action_show_plane.setChecked(True)
        self.action_show_plane.setEnabled(False)
        self.action_show_plane.triggered.connect(self._toggle_plane_visibility)
        toolbar.addAction(self.action_show_plane)

        self.action_measure_height = QAction("Medir altura del arco", self)
        self.action_measure_height.setCheckable(True)
        self.action_measure_height.setEnabled(False)
        self.action_measure_height.triggered.connect(self._toggle_measure_height)
        toolbar.addAction(self.action_measure_height)

        self.action_measure_distance = QAction("Medir distancia en el plano", self)
        self.action_measure_distance.setCheckable(True)
        self.action_measure_distance.setEnabled(False)
        self.action_measure_distance.triggered.connect(self._toggle_measure_distance)
        toolbar.addAction(self.action_measure_distance)

        toolbar.addSeparator()

        self.action_heatmap = QAction("Mapa de calor", self)
        self.action_heatmap.setCheckable(True)
        self.action_heatmap.setEnabled(False)
        self.action_heatmap.triggered.connect(self._toggle_heatmap)
        toolbar.addAction(self.action_heatmap)

        self.action_show_texture = QAction("Mostrar textura", self)
        self.action_show_texture.setCheckable(True)
        self.action_show_texture.setEnabled(False)
        self.action_show_texture.triggered.connect(self._toggle_texture)
        toolbar.addAction(self.action_show_texture)

    def _create_status_bar(self):
        """Crear barra de estado"""
        self.status_label = QLabel("Listo")
        self.statusBar().addWidget(self.status_label)

    def _connect_signals(self):
        """Conectar señales del canvas"""
        if hasattr(self, 'canvas'):
            self.canvas.mesh_loaded.connect(self._on_mesh_loaded)
            self.canvas.point_selected.connect(self._on_point_picked)

    def _create_shortcuts(self):
        """Atajos de teclado: Escape cancela el picking activo, Supr borra la
        medición seleccionada en la tabla, Ctrl+Z deshace el último punto
        (o la última medición completa, si no hay una selección a medias)"""
        escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape_shortcut.activated.connect(self._cancel_active_pick_mode)

        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self.measurement_table)
        delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        delete_shortcut.activated.connect(self._delete_selected_measurement)

        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(self._handle_undo)

    def _on_mesh_loaded(self, model):
        """Callback cuando se carga malla"""
        info = (
            f"{model.filename} - "
            f"{model.num_vertices} vértices, "
            f"{model.num_triangles} triángulos"
        )
        self.status_label.setText(info)
        logger.info(f"Malla cargada: {info}")

        # Nueva malla: descartar plano de apoyo y mediciones anteriores
        self.support_plane = None
        self._pick_mode = None
        self._plane_points = []
        self._distance_points = []
        self._distance_marker_actors = []
        self.measurements = []
        self._rebuild_measurement_table()
        self.action_define_plane.setChecked(False)
        self.action_define_plane.setEnabled(True)
        self.action_measure_height.setChecked(False)
        self.action_measure_height.setEnabled(False)
        self.action_measure_distance.setChecked(False)
        self.action_measure_distance.setEnabled(False)
        self.action_show_plane.setChecked(True)
        self.action_show_plane.setEnabled(False)
        self.action_heatmap.setChecked(False)
        self.action_heatmap.setEnabled(False)
        # A diferencia del resto, la textura no depende del plano de apoyo —
        # se puede ver apenas se carga la malla, si el archivo la trae.
        self.action_show_texture.setChecked(False)
        self.action_show_texture.setEnabled(self.canvas.has_texture())
        self.save_project_action.setEnabled(True)
        self.export_csv_action.setEnabled(True)
        self.export_pdf_action.setEnabled(True)
        self._unsaved_changes = False

        self._show_validation_warnings_if_needed(model)

    def _show_validation_warnings_if_needed(self, model):
        """
        Mostrar un aviso solo si hay algo fuera de lo normal en la malla
        cargada (escala inusual, malla muy grande, triángulos degenerados).
        `MeshLoader` siempre agrega un mensaje informativo de escala aunque
        todo esté bien (ej. "probablemente MILÍMETROS (pie normal)") — ese
        caso no amerita interrumpir con un diálogo, así que se filtra.
        """
        NORMAL_SCALE_HINT = "MILÍMETROS (pie normal)"
        concerning = [w for w in model.validation_warnings if NORMAL_SCALE_HINT not in w]
        if concerning:
            QMessageBox.warning(
                self,
                "Revisar antes de medir",
                "Se detectó lo siguiente en la malla cargada:\n\n"
                + "\n".join(f"• {w}" for w in concerning)
                + "\n\nVerificá que la escala sea la esperada antes de tomar mediciones."
            )

    def _set_pick_mode_exclusive(self, active_action: QAction):
        """Desmarcar los otros botones de modo de picking al activar uno nuevo"""
        for action in (
            self.action_define_plane,
            self.action_measure_height,
            self.action_measure_distance,
        ):
            if action is not active_action and action.isChecked():
                action.setChecked(False)

    def _toggle_define_plane(self, checked: bool):
        """Activar/desactivar el modo de selección de 3 puntos para el plano de apoyo"""
        if checked:
            self._set_pick_mode_exclusive(self.action_define_plane)
            self._pick_mode = 'plane'
            self._plane_points = []
            # Redefinir el plano invalida las mediciones ya tomadas (altura y
            # distancia se calculan relativas a él), así que se descartan acá.
            self.measurements = []
            self._rebuild_measurement_table()
            self.canvas.reset_measurements()
            self.support_plane = None
            self.action_measure_height.setEnabled(False)
            self.action_measure_distance.setEnabled(False)
            self.action_show_plane.setChecked(True)
            self.action_show_plane.setEnabled(False)
            # El mapa de calor está pintado relativo al plano viejo: apagarlo
            # acá, no solo deshabilitarlo, para no dejar colores obsoletos.
            if self.action_heatmap.isChecked():
                self.action_heatmap.setChecked(False)
                self.canvas.clear_vertex_colors()
            self.action_heatmap.setEnabled(False)
            self.canvas.enable_picking(True)
            self.status_label.setText(
                "Plano de apoyo: click en 3 puntos de la base del pie (0/3)"
            )
        else:
            self._pick_mode = None
            self.canvas.enable_picking(False)
            self.status_label.setText("Selección de plano de apoyo cancelada")

    def _toggle_measure_height(self, checked: bool):
        """Activar/desactivar el modo de selección de un punto de altura de arco"""
        if checked:
            if self.support_plane is None:
                QMessageBox.warning(
                    self,
                    "Falta plano de apoyo",
                    "Primero definí el plano de apoyo (3 clicks en la base del pie)."
                )
                self.action_measure_height.setChecked(False)
                return
            self._set_pick_mode_exclusive(self.action_measure_height)
            self._pick_mode = 'height'
            self.canvas.enable_picking(True)
            self.status_label.setText(
                "Altura del arco: click en el punto más alto del arco plantar"
            )
        else:
            self._pick_mode = None
            self.canvas.enable_picking(False)
            self.status_label.setText("Medición de altura cancelada")

    def _toggle_measure_distance(self, checked: bool):
        """Activar/desactivar el modo de selección de 2 puntos para medir distancia en el plano"""
        if checked:
            if self.support_plane is None:
                QMessageBox.warning(
                    self,
                    "Falta plano de apoyo",
                    "Primero definí el plano de apoyo (3 clicks en la base del pie)."
                )
                self.action_measure_distance.setChecked(False)
                return
            self._set_pick_mode_exclusive(self.action_measure_distance)
            self._pick_mode = 'distance'
            self._distance_points = []
            self.canvas.enable_picking(True)
            self.status_label.setText(
                "Distancia en el plano: click en 2 puntos de la superficie de apoyo (0/2)"
            )
        else:
            self._pick_mode = None
            self._distance_points = []
            # Si ya se había clickeado el primer punto, su marcador queda
            # suelto (todavía no está asociado a ninguna Measurement) — hay
            # que limpiarlo a mano para no dejarlo huérfano en el canvas.
            self.canvas.remove_actors(self._distance_marker_actors)
            self._distance_marker_actors = []
            self.canvas.enable_picking(False)
            self.status_label.setText("Medición de distancia cancelada")

    def _toggle_plane_visibility(self, checked: bool):
        """Mostrar/ocultar el plano de apoyo sin borrarlo ni afectar las mediciones"""
        self.canvas.set_plane_visible(checked)

    def _toggle_heatmap(self, checked: bool):
        """Activar/desactivar el mapa de calor de altura sobre toda la malla"""
        if checked:
            if self.support_plane is None:
                QMessageBox.warning(
                    self,
                    "Falta plano de apoyo",
                    "Primero definí el plano de apoyo (3 clicks en la base del pie)."
                )
                self.action_heatmap.setChecked(False)
                return
            # El mapa de calor y la textura compiten por el mismo canal visual
            # (colorean toda la superficie) — son mutuamente excluyentes.
            if self.action_show_texture.isChecked():
                self.action_show_texture.setChecked(False)
                self.canvas.set_texture_visible(False)
            heights = compute_height_map(self.support_plane, self.current_model.vertices)
            colors = height_map_to_colors(heights)
            self.canvas.set_vertex_colors(colors)
            self.status_label.setText(f"Mapa de calor activado (máximo: {heights.max():.1f} mm respecto al plano)")
            logger.info(f"Mapa de calor activado, altura máxima: {heights.max():.2f} mm")
        else:
            self.canvas.clear_vertex_colors()
            self.status_label.setText("Mapa de calor desactivado")

    def _toggle_texture(self, checked: bool):
        """Activar/desactivar la textura (foto del pie) sobre la malla"""
        if checked:
            if not self.canvas.has_texture():
                QMessageBox.information(
                    self,
                    "Sin textura",
                    "Esta malla no tiene textura cargada (el archivo no trae "
                    "coordenadas UV, .mtl o imagen de textura válidos)."
                )
                self.action_show_texture.setChecked(False)
                return
            if self.action_heatmap.isChecked():
                self.action_heatmap.setChecked(False)
                self.canvas.clear_vertex_colors()
            self.canvas.set_texture_visible(True)
            self.status_label.setText("Textura activada")
            logger.info("Textura activada")
        else:
            self.canvas.set_texture_visible(False)
            self.status_label.setText("Textura desactivada")

    def _next_measurement_name(self, prefix: str) -> str:
        """Numerar mediciones del mismo tipo: 'Altura arco 1', 'Altura arco 2', etc."""
        count = sum(1 for m in self.measurements if m.name.startswith(prefix))
        return f"{prefix} {count + 1}"

    def _refresh_measurement_display(self):
        """Actualizar el texto superpuesto del canvas con todas las mediciones acumuladas"""
        if self.measurements:
            text = "\n".join(str(m) for m in self.measurements)
            self.canvas.show_measurement_text(text)
        else:
            self.canvas.clear_measurement_text()

    def _add_measurement_row(self, measurement: Measurement):
        """Agregar una fila a la tabla de mediciones (columnas: nombre editable, valor fijo)"""
        # blockSignals evita que insertar la fila dispare itemChanged como si
        # fuera una edición del usuario (que marcaría cambios sin guardar y
        # podría interferir con una reconstrucción completa de la tabla).
        self.measurement_table.blockSignals(True)
        try:
            row = self.measurement_table.rowCount()
            self.measurement_table.insertRow(row)

            name_item = QTableWidgetItem(measurement.name)
            # El id se guarda en el item para poder ubicar la Measurement al
            # eliminar o renombrar, sin depender de que el índice de fila no cambie.
            name_item.setData(Qt.ItemDataRole.UserRole, measurement.id)

            value_item = QTableWidgetItem(f"{measurement.value:.2f} {measurement.unit}")
            # El valor es calculado, no algo que tenga sentido editar a mano.
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.measurement_table.setItem(row, 0, name_item)
            self.measurement_table.setItem(row, 1, value_item)
        finally:
            self.measurement_table.blockSignals(False)

    def _on_measurement_name_edited(self, item: QTableWidgetItem):
        """Aplicar el renombre de una medición hecho a mano en la tabla (columna 0)"""
        if item.column() != 0:
            return

        measurement_id = item.data(Qt.ItemDataRole.UserRole)
        measurement = next((m for m in self.measurements if m.id == measurement_id), None)
        if measurement is None:
            return

        new_name = item.text().strip()
        if not new_name:
            # Nombre vacío: revertir en vez de dejar una medición sin nombre.
            self.measurement_table.blockSignals(True)
            item.setText(measurement.name)
            self.measurement_table.blockSignals(False)
            return

        measurement.name = new_name
        self._refresh_measurement_display()
        self._mark_dirty()
        logger.info(f"Medición renombrada: {measurement_id} -> {new_name}")

    def _rebuild_measurement_table(self):
        """Reconstruir la tabla completa a partir de self.measurements"""
        self.measurement_table.setRowCount(0)
        for measurement in self.measurements:
            self._add_measurement_row(measurement)

    def _show_measurement_context_menu(self, pos):
        """Menú contextual (click derecho) sobre una fila de la tabla de mediciones"""
        item = self.measurement_table.itemAt(pos)
        if item is None:
            return
        row = item.row()
        measurement_id = self.measurement_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        menu = QMenu(self)
        delete_action = menu.addAction("Eliminar medición")
        chosen = menu.exec(self.measurement_table.viewport().mapToGlobal(pos))
        if chosen == delete_action:
            self._delete_measurement(measurement_id)

    def _delete_measurement(self, measurement_id: int):
        """Eliminar una medición puntual: de la lista, del canvas y de la tabla"""
        removed = next((m for m in self.measurements if m.id == measurement_id), None)
        if removed is None:
            return
        self.measurements = [m for m in self.measurements if m.id != measurement_id]
        self.canvas.remove_measurement(measurement_id)
        self._rebuild_measurement_table()
        self._refresh_measurement_display()
        self._mark_dirty()
        self.status_label.setText(f"{removed.name} eliminada ({len(self.measurements)} mediciones restantes)")
        logger.info(f"Medición eliminada: {removed.name}")

    def _delete_selected_measurement(self):
        """Atajo Supr: eliminar la medición de la fila seleccionada en la tabla"""
        selected_items = self.measurement_table.selectedItems()
        if not selected_items:
            return
        row = selected_items[0].row()
        measurement_id = self.measurement_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self._delete_measurement(measurement_id)

    def _cancel_active_pick_mode(self):
        """Atajo Escape: cancelar el modo de picking activo, si hay alguno"""
        if self.action_define_plane.isChecked():
            self.action_define_plane.setChecked(False)
            self._toggle_define_plane(False)
        elif self.action_measure_height.isChecked():
            self.action_measure_height.setChecked(False)
            self._toggle_measure_height(False)
        elif self.action_measure_distance.isChecked():
            self.action_measure_distance.setChecked(False)
            self._toggle_measure_distance(False)

    def _handle_undo(self):
        """
        Atajo Ctrl+Z: si hay una selección de plano (3 puntos) o distancia
        (2 puntos) a medio hacer, deshace el último punto clickeado. Si no
        hay ninguna selección en curso, deshace la última medición
        completa (reusa `_delete_measurement`).
        """
        if self._pick_mode == 'plane' and self._plane_points:
            self._plane_points.pop()
            self.canvas.remove_last_plane_marker()
            n = len(self._plane_points)
            self.status_label.setText(
                f"Plano de apoyo: click en 3 puntos de la base del pie ({n}/3)"
            )
        elif self._pick_mode == 'distance' and self._distance_points:
            self._distance_points.pop()
            if self._distance_marker_actors:
                self.canvas.remove_actors([self._distance_marker_actors.pop()])
            n = len(self._distance_points)
            self.status_label.setText(
                f"Distancia en el plano: click en 2 puntos de la superficie de apoyo ({n}/2)"
            )
        elif self.measurements:
            self._delete_measurement(self.measurements[-1].id)

    def _on_point_picked(self, point: np.ndarray):
        """Callback cuando el usuario selecciona un punto sobre la malla en modo picking"""
        if self._pick_mode == 'plane':
            self._on_plane_point_picked(point)
        elif self._pick_mode == 'height':
            self._on_height_point_picked(point)
        elif self._pick_mode == 'distance':
            self._on_distance_point_picked(point)

    def _on_plane_point_picked(self, point: np.ndarray):
        self._plane_points.append(point)
        self.canvas.add_plane_marker(point)
        n = len(self._plane_points)

        if n < 3:
            self.status_label.setText(
                f"Plano de apoyo: click en 3 puntos de la base del pie ({n}/3)"
            )
            return

        try:
            self.support_plane = compute_support_plane(*self._plane_points)
        except MeasurementError as e:
            QMessageBox.warning(self, "Puntos inválidos", str(e))
            logger.warning(f"Plano de apoyo inválido: {e}")
            self._plane_points = []
            self.canvas.clear_plane_markers()
            self.status_label.setText(
                "Plano de apoyo: click en 3 puntos de la base del pie (0/3)"
            )
            return

        # El rectángulo se dimensiona para cubrir toda la huella de la malla
        # sobre el plano (no un tamaño fijo ni centrado en uno de los 3
        # puntos clickeados, que puede quedar chico o descentrado respecto
        # al pie real).
        center, width, height = compute_plane_footprint(
            self.support_plane, self.current_model.vertices
        )
        self.canvas.draw_support_plane(
            center,
            self.support_plane.normal,
            width=width,
            height=height,
        )
        self.canvas.enable_picking(False)
        self.action_define_plane.setChecked(False)
        self._pick_mode = None
        self.action_measure_height.setEnabled(True)
        self.action_measure_distance.setEnabled(True)
        self.action_show_plane.setEnabled(True)
        self.action_show_plane.setChecked(True)
        self.action_heatmap.setEnabled(True)
        self.status_label.setText(
            "Plano de apoyo definido. Ahora podés medir altura del arco o distancias."
        )
        self._mark_dirty()
        logger.info("Plano de apoyo definido con 3 puntos")

    def _on_height_point_picked(self, point: np.ndarray):
        projected = self.support_plane.project_point(point)
        height = compute_arch_height(self.support_plane, point)

        measurement = Measurement(
            name=self._next_measurement_name("Altura arco"),
            measurement_type='altura_arco',
            value=height,
            unit='mm',
            point1=point,
            point2=projected,
        )
        self.measurements.append(measurement)

        marker = self.canvas.add_marker(point, color=HEIGHT_MARKER_COLOR)
        line = self.canvas.add_measurement_line(point, projected, color=HEIGHT_LINE_COLOR)
        self.canvas.register_measurement_visuals(measurement.id, [marker, line])
        self._add_measurement_row(measurement)
        self._refresh_measurement_display()
        self._mark_dirty()

        self.status_label.setText(f"{measurement} agregada ({len(self.measurements)} mediciones en total)")

        self.canvas.enable_picking(False)
        self.action_measure_height.setChecked(False)
        self._pick_mode = None
        logger.info(f"{measurement.name} medida: {height:.2f} mm")

    def _on_distance_point_picked(self, point: np.ndarray):
        self._distance_points.append(point)
        marker = self.canvas.add_marker(point, color=DISTANCE_MARKER_COLOR)
        self._distance_marker_actors.append(marker)
        n = len(self._distance_points)

        if n < 2:
            self.status_label.setText(
                f"Distancia en el plano: click en 2 puntos de la superficie de apoyo ({n}/2)"
            )
            return

        point_a, point_b = self._distance_points
        distance = compute_plane_distance(self.support_plane, point_a, point_b)
        projected_a = self.support_plane.project_point(point_a)
        projected_b = self.support_plane.project_point(point_b)

        measurement = Measurement(
            name=self._next_measurement_name("Distancia plano"),
            measurement_type='distancia_plano',
            value=distance,
            unit='mm',
            point1=point_a,
            point2=point_b,
        )
        self.measurements.append(measurement)

        line = self.canvas.add_measurement_line(projected_a, projected_b, color=DISTANCE_LINE_COLOR)
        self.canvas.register_measurement_visuals(measurement.id, self._distance_marker_actors + [line])
        self._distance_marker_actors = []
        self._add_measurement_row(measurement)
        self._refresh_measurement_display()
        self._mark_dirty()

        self.status_label.setText(f"{measurement} agregada ({len(self.measurements)} mediciones en total)")

        self.canvas.enable_picking(False)
        self.action_measure_distance.setChecked(False)
        self._pick_mode = None
        self._distance_points = []
        logger.info(f"{measurement.name} medida: {distance:.2f} mm")

    def open_file(self):
        """Diálogo para abrir archivo STL u OBJ"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir archivo de malla 3D",
            "",
            "Mallas 3D (*.stl *.obj);;STL Files (*.stl);;OBJ Files (*.obj);;Todos los archivos (*)"
        )
        if filepath:
            self.current_file = filepath
            filename = Path(filepath).name
            self.status_label.setText(f"Cargando: {filename}")
            logger.info(f"Archivo seleccionado: {filepath}")
            try:
                self.status_label.setText(f"Parseando: {filename}")
                self.current_model = self.mesh_loader.load(filepath)
                self.status_label.setText(f"Renderizando: {filename}")
                self.canvas.load_mesh(self.current_model)
                self.canvas.set_view_dorsal()
                self.status_label.setText(
                    f"✓ {filename} - "
                    f"{self.current_model.num_vertices} vértices, "
                    f"{self.current_model.num_triangles} triángulos"
                )
            except FileNotFoundError as e:
                self.status_label.setText("Error: Archivo no encontrado")
                QMessageBox.critical(self, "Error", f"Archivo no encontrado:\n{e}")
                logger.error(f"Archivo no encontrado: {filepath}")
            except (STLParseError, OBJParseError, GeometryValidationError) as e:
                self.status_label.setText("Error: malla inválida")
                QMessageBox.critical(self, "Error", f"Error parseando archivo:\n{e}")
                logger.error(f"Error de malla: {e}")
            except Exception as e:
                self.status_label.setText("Error: Fallo al cargar")
                QMessageBox.critical(self, "Error", f"Error inesperado:\n{e}")
                logger.error(f"Error inesperado: {e}")

    def export_measurements_csv_dialog(self):
        """Diálogo para exportar las mediciones actuales a un archivo CSV"""
        if not self.measurements:
            QMessageBox.information(self, "Sin mediciones", "No hay mediciones para exportar.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Exportar mediciones a CSV", "", "CSV (*.csv)")
        if not filepath:
            return
        if not filepath.lower().endswith('.csv'):
            filepath += '.csv'

        try:
            source_name = self.current_model.filename if self.current_model else ""
            export_measurements_csv(self.measurements, filepath, source_filename=source_name)
            self.status_label.setText(f"Mediciones exportadas: {Path(filepath).name}")
            logger.info(f"CSV exportado: {filepath}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar el CSV:\n{e}")
            logger.error(f"Error exportando CSV: {e}")

    def export_report_pdf_dialog(self):
        """Diálogo para exportar un informe PDF con una captura del pie y las mediciones"""
        if self.current_model is None:
            QMessageBox.information(self, "Sin malla cargada", "Cargá una malla antes de generar el informe.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Exportar informe a PDF", "", "PDF (*.pdf)")
        if not filepath:
            return
        if not filepath.lower().endswith('.pdf'):
            filepath += '.pdf'

        screenshot_path = os.path.join(tempfile.gettempdir(), f"pie_viewer_screenshot_{os.getpid()}.png")
        try:
            self.canvas.capture_screenshot(screenshot_path)
            export_report_pdf(
                self.measurements,
                filepath,
                source_filename=self.current_model.filename,
                screenshot_path=screenshot_path,
            )
            self.status_label.setText(f"Informe exportado: {Path(filepath).name}")
            logger.info(f"PDF exportado: {filepath}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar el informe:\n{e}")
            logger.error(f"Error exportando PDF: {e}")
        finally:
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)

    def save_project_dialog(self):
        """Diálogo para guardar el estado actual (malla + plano + mediciones) como proyecto"""
        if self.current_model is None:
            QMessageBox.information(self, "Sin malla cargada", "Cargá una malla antes de guardar el proyecto.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Guardar proyecto", "", "Proyecto pie-viewer (*.json)")
        if not filepath:
            return
        if not filepath.lower().endswith('.json'):
            filepath += '.json'

        plane_points = None
        if self.support_plane is not None:
            plane_points = [self.support_plane.point1, self.support_plane.point2, self.support_plane.point3]

        try:
            save_project(filepath, self.current_file, plane_points, self.measurements)
            self._unsaved_changes = False
            self.status_label.setText(f"Proyecto guardado: {Path(filepath).name}")
            logger.info(f"Proyecto guardado: {filepath}")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el proyecto:\n{e}")
            logger.error(f"Error guardando proyecto: {e}")

    def open_project_dialog(self):
        """Diálogo para abrir un proyecto guardado: recarga la malla y restaura plano + mediciones"""
        filepath, _ = QFileDialog.getOpenFileName(self, "Abrir proyecto", "", "Proyecto pie-viewer (*.json)")
        if not filepath:
            return

        try:
            mesh_filepath, plane, measurements = load_project(filepath)
        except (ValueError, OSError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer el proyecto:\n{e}")
            logger.error(f"Error leyendo proyecto {filepath}: {e}")
            return

        if not Path(mesh_filepath).exists():
            QMessageBox.critical(
                self,
                "Malla no encontrada",
                f"El proyecto hace referencia a:\n{mesh_filepath}\n\n"
                "Ese archivo ya no está en esa ubicación. Movelo de vuelta "
                "o volvé a generar el proyecto desde la malla actual."
            )
            return

        try:
            self.current_model = self.mesh_loader.load(mesh_filepath)
        except (STLParseError, OBJParseError, GeometryValidationError, FileNotFoundError) as e:
            QMessageBox.critical(self, "Error", f"No se pudo cargar la malla del proyecto:\n{e}")
            logger.error(f"Error cargando malla del proyecto: {e}")
            return

        self.current_file = mesh_filepath
        # load_mesh() dispara mesh_loaded -> _on_mesh_loaded, que resetea
        # plano/mediciones/tabla; restauramos todo DESPUÉS de esa llamada.
        self.canvas.load_mesh(self.current_model)
        self.canvas.set_view_dorsal()

        if plane is not None:
            self.support_plane = plane
            center, width, height = compute_plane_footprint(plane, self.current_model.vertices)
            self.canvas.draw_support_plane(center, plane.normal, width=width, height=height)
            for plane_point in (plane.point1, plane.point2, plane.point3):
                self.canvas.add_plane_marker(plane_point)
            self.action_measure_height.setEnabled(True)
            self.action_measure_distance.setEnabled(True)
            self.action_show_plane.setEnabled(True)
            self.action_show_plane.setChecked(True)
            self.action_heatmap.setEnabled(True)

        for measurement in measurements:
            self.measurements.append(measurement)
            if measurement.measurement_type == 'altura_arco' and measurement.point1 is not None:
                marker = self.canvas.add_marker(measurement.point1, color=HEIGHT_MARKER_COLOR)
                line = self.canvas.add_measurement_line(measurement.point1, measurement.point2, color=HEIGHT_LINE_COLOR)
                self.canvas.register_measurement_visuals(measurement.id, [marker, line])
            elif measurement.measurement_type == 'distancia_plano' and measurement.point1 is not None and self.support_plane is not None:
                projected_a = self.support_plane.project_point(measurement.point1)
                projected_b = self.support_plane.project_point(measurement.point2)
                marker_a = self.canvas.add_marker(measurement.point1, color=DISTANCE_MARKER_COLOR)
                marker_b = self.canvas.add_marker(measurement.point2, color=DISTANCE_MARKER_COLOR)
                line = self.canvas.add_measurement_line(projected_a, projected_b, color=DISTANCE_LINE_COLOR)
                self.canvas.register_measurement_visuals(measurement.id, [marker_a, marker_b, line])
            self._add_measurement_row(measurement)

        self._refresh_measurement_display()
        self.status_label.setText(f"Proyecto cargado: {Path(filepath).name} ({len(measurements)} mediciones)")
        logger.info(f"Proyecto cargado: {filepath}")

    def show_about(self):
        """Mostrar diálogo Acerca de"""
        QMessageBox.information(
            self,
            "Acerca de",
            "Sistema de Visualización de Pies\n"
            "Versión 0.1.0 MVP\n\n"
            "Para análisis y medición de modelos 3D de pies\n"
            "en ortopedia."
        )

    def closeEvent(self, event):
        """Evento al cerrar ventana: confirma si hay mediciones sin guardar"""
        if self._unsaved_changes and self.measurements:
            reply = QMessageBox.question(
                self,
                "Mediciones sin guardar",
                "Hay mediciones sin guardar. ¿Querés guardarlas antes de salir?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if reply == QMessageBox.StandardButton.Save:
                self.save_project_dialog()
                if self._unsaved_changes:
                    # El usuario canceló el diálogo de guardado (o falló):
                    # no cerrar la ventana para no perder las mediciones.
                    event.ignore()
                    return

        logger.info("Cerrando aplicación")
        event.accept()
