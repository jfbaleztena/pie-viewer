"""
VTK 3D Viewer - Canvas para renderizar malla 3D del pie

Responsabilidades:
- Integrar VTK con PyQt6
- Cargar y renderizar malla STL
- Controlar cámara (rotación, zoom, pan)
- Dibujar plano de apoyo
- Mapear colores por altura
- Seleccionar puntos en la malla (picking)
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List
import logging

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QEvent, pyqtSignal

# vtkmodules es modular: estos imports no se usan directamente, pero registran
# los backends concretos (OpenGL, fuentes de texto) contra las fábricas
# abstractas de VTK. Sin ellos, vtkRenderWindow()/vtkTextActor() se crean pero
# no dibujan nada (sin lanzar ningún error) porque no hay implementación real
# detrás de la clase abstracta.
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
import vtkmodules.vtkRenderingFreeType  # noqa: F401

from vtkmodules.vtkRenderingCore import vtkRenderWindow, vtkRenderer, vtkActor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.vtkCommonDataModel import vtkPolyData, vtkCellArray
from vtkmodules.vtkRenderingCore import (
    vtkPolyDataMapper, vtkProperty, vtkCellPicker, vtkTextActor, vtkWindowToImageFilter, vtkTexture
)
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkFiltersSources import vtkSphereSource, vtkLineSource
from vtkmodules.vtkIOImage import vtkPNGWriter, vtkPNGReader, vtkJPEGReader
from vtkmodules.util.numpy_support import numpy_to_vtk

from src.core.measurements import intersect_ray_plane
from src.models.foot_model import FootModel, TextureData

logger = logging.getLogger(__name__)

# Defensive imports for VTK compatibility across versions
try:
    from vtkmodules.vtkRenderingQt import QVTKRenderWindowInteractor
except ImportError:
    try:
        from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    except ImportError:
        logger.warning("Could not import QVTKRenderWindowInteractor - VTK GUI rendering may fail")
        QVTKRenderWindowInteractor = None

# Try to import vtkPolyDataNormals (not available in all VTK versions)
try:
    from vtkmodules.vtkFiltersGeneral import vtkPolyDataNormals
except ImportError:
    try:
        from vtkmodules.vtkFiltersCore import vtkPolyDataNormals
    except ImportError:
        logger.warning("vtkPolyDataNormals not available - will render without explicit normal computation")
        vtkPolyDataNormals = None


class VTK3DView(QWidget):
    """
    Widget PyQt6 que renderiza modelos 3D usando VTK
    """

    # Señales
    point_selected = pyqtSignal(np.ndarray)  # Punto seleccionado en la malla
    mesh_loaded = pyqtSignal(FootModel)      # Malla cargada
    # Un marcador de distancia se está arrastrando sobre el plano:
    # (id de la medición, 0/1 = punto inicial/final, nueva posición)
    marker_dragged = pyqtSignal(int, int, np.ndarray)
    marker_drag_finished = pyqtSignal(int)   # Se soltó el marcador (id de la medición)

    def __init__(self, parent=None):
        """
        Inicializar widget VTK

        Args:
            parent: Widget padre PyQt6
        """
        super().__init__(parent)
        self.logger = logging.getLogger(__name__)
        self._interactor_initialized = False

        if QVTKRenderWindowInteractor is None:
            self.logger.error("VTK rendering not available - QVTKRenderWindowInteractor could not be imported")
            return

        # Interactor y renderer
        self.interactor = QVTKRenderWindowInteractor(self)
        self.render_window = self.interactor.GetRenderWindow()
        self.renderer = vtkRenderer()
        self.render_window.AddRenderer(self.renderer)
        # Capa superior (comparte la cámara): lo que se agrega acá se dibuja
        # siempre por encima de la malla. Se usa para los puntos y líneas de
        # distancia y la previsualización, que viven sobre el plano de apoyo
        # y, si el pie no apoya en él, quedarían tapados por la propia malla.
        self.overlay_renderer = vtkRenderer()
        self.render_window.SetNumberOfLayers(2)
        self.renderer.SetLayer(0)
        self.overlay_renderer.SetLayer(1)
        self.overlay_renderer.InteractiveOff()
        self.overlay_renderer.SetActiveCamera(self.renderer.GetActiveCamera())
        self.render_window.AddRenderer(self.overlay_renderer)

        # Estado
        self.current_model: Optional[FootModel] = None
        self.mesh_actor: Optional[vtkActor] = None
        self.support_plane_actor: Optional[vtkActor] = None
        self.axes_actor: Optional[vtkAxesActor] = None
        # Marcadores de los 3 puntos que definen el plano de apoyo: se
        # limpian todos juntos (no son mediciones individuales, no tiene
        # sentido borrar "un punto del plano" sin redefinirlo entero)
        self.plane_marker_actors: List[vtkActor] = []
        # Actores (marcador(es) + línea) de cada Measurement, indexados por
        # su id, para poder borrar una medición puntual sin tocar el resto
        self.measurement_visuals: dict = {}
        self.measurement_text_actor: Optional[vtkTextActor] = None

        # Textura: la malla "plana" (posiciones, para picking/heatmap/mapa de
        # calor) y la malla de render con textura (UV, más vértices en las
        # costuras) son polydata separadas — se guarda la plana para poder
        # volver a ella al apagar la textura, y la de textura se arma una
        # sola vez (cacheada) la primera vez que se activa.
        self._plain_polydata: Optional[vtkPolyData] = None
        self._texture_polydata: Optional[vtkPolyData] = None
        self._vtk_texture: Optional[vtkTexture] = None
        self._texture_visible = False

        # Picking de puntos sobre la malla
        self.picker = vtkCellPicker()
        self.picker.SetTolerance(0.005)
        self._picking_enabled = False
        self._press_pos = None  # QPointF del último LeftButtonPress, o None

        # Con el plano visible, los puntos se pueden ubicar sobre el plano
        # (intersección rayo-plano) en vez de sobre la malla, y los marcadores
        # de distancia se pueden arrastrar a lo largo de él.
        self._pick_on_plane = False
        self._plane_origin: Optional[np.ndarray] = None
        self._plane_normal: Optional[np.ndarray] = None
        # id de medición -> {'markers': [actor_inicial, actor_final], 'line': actor}
        self._drag_targets: dict = {}
        self._drag_state: Optional[Tuple[int, int]] = None  # (id medición, 0/1) mientras se arrastra
        # Marcadores de los puntos de referencia (metatarsianos, talón), por clave
        self.landmark_actors: dict = {}

        # Esfera de previsualización: sigue al cursor mientras hay un modo de
        # picking activo, mostrando dónde caería el click antes de hacerlo.
        # Se crea recién al primer hover (lazy) y se reposiciona in-place en
        # cada movimiento de mouse, en vez de crear un actor nuevo por frame.
        self._preview_marker_actor: Optional[vtkActor] = None
        self._preview_sphere_source: Optional[vtkSphereSource] = None

        # Configurar interacción
        self.interactor.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
        self.interactor.SetPicker(self.picker)
        # Initialize() se difiere a showEvent(): llamarlo acá (antes de que el
        # widget tenga una superficie nativa válida en pantalla) deja el
        # render window en negro hasta el primer resize manual.

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.interactor)
        self.setLayout(layout)

        # El filtro queda instalado siempre: lo que hace cada evento depende de
        # si el picking está activo o si hay marcadores arrastrables.
        self.interactor.installEventFilter(self)

        # Configurar renderer
        self._setup_renderer()

    def showEvent(self, event):
        super().showEvent(event)
        if not self._interactor_initialized:
            self.interactor.Initialize()
            self._interactor_initialized = True
            self.render_window.Render()

    def _setup_renderer(self):
        """
        Configurar parámetros iniciales del renderer
        """
        # Color de fondo (gris claro)
        self.renderer.SetBackground(0.3, 0.3, 0.35)

        # Iluminación
        self.renderer.ResetCamera()

    def load_mesh(self, model: FootModel):
        """
        Cargar y renderizar malla STL

        Args:
            model: FootModel con vértices y caras
        """
        if model.vertices is None or len(model.vertices) == 0:
            self.logger.error("Modelo sin vértices")
            return

        # Malla nueva: descartar plano/marcadores/medición de la malla anterior
        self.reset_measurements()
        self.enable_picking(False)
        # La malla de textura es específica del modelo anterior: descartar el
        # cache para que se reconstruya (o no) según la textura del nuevo modelo.
        self._texture_polydata = None
        self._vtk_texture = None
        self._texture_visible = False

        self.current_model = model
        self.logger.info(f"Cargando malla: {model.num_vertices} vértices, {model.num_triangles} triángulos")

        try:
            # Crear vtkPolyData
            poly_data = self._vertices_faces_to_polydata(
                model.vertices,
                model.faces
            )

            # Intentar calcular normales si está disponible
            if vtkPolyDataNormals is not None:
                try:
                    normals_filter = vtkPolyDataNormals()
                    normals_filter.SetInputData(poly_data)
                    normals_filter.SetFeatureAngle(45.0)
                    # SplittingOff(): por defecto vtkPolyDataNormals duplica
                    # vértices en bordes filosos (para shading plano ahí),
                    # lo que rompe la correspondencia 1:1 entre model.vertices
                    # y los puntos de la polydata que necesita
                    # set_vertex_colors() para pintar por vértice. Un pie
                    # escaneado no tiene bordes filosos reales, así que
                    # desactivarlo no cambia el shading visible.
                    normals_filter.SplittingOff()
                    # ConsistencyOn (default) solo iguala el sentido de las
                    # normales ENTRE sí, no determina cuál sentido es el
                    # "hacia afuera" real: eso depende del orden de vértices
                    # de cada cara en el archivo de origen. Distintos
                    # exportadores (ej. STL vs OBJ de CrealityScan) usan
                    # convenciones de winding distintas, así que sin
                    # AutoOrientNormalsOn() una malla puede terminar con
                    # todas las normales "para adentro" y mostrarse con el
                    # color de cara trasera en vistas donde antes se veía
                    # bien (visto con pie_mio_texturado.obj: la vista
                    # plantar se pintaba del color cálido de backface).
                    normals_filter.ConsistencyOn()
                    normals_filter.AutoOrientNormalsOn()
                    normals_filter.Update()
                    poly_data = normals_filter.GetOutput()
                    self.logger.debug("Normales calculadas con vtkPolyDataNormals")
                except Exception as e:
                    self.logger.warning(f"No se pudieron calcular normales: {e}")
                    # Continuar sin normales explícitas
            else:
                self.logger.debug("vtkPolyDataNormals no disponible - VTK calculará normales automáticamente")

            # Crear actor
            self._plain_polydata = poly_data
            mapper = vtkPolyDataMapper()
            mapper.SetInputData(poly_data)

            actor = vtkActor()
            actor.SetMapper(mapper)

            # Propiedades visuales
            prop = actor.GetProperty()
            prop.SetColor(0.8, 0.8, 0.85)  # Color gris claro (cara frontal)
            prop.SetSpecular(0.3)
            prop.SetSpecularPower(20)
            prop.EdgeVisibilityOff()

            # NOTA: antes había un color distinto para la cara posterior
            # (SetBackfaceProperty con tono cálido) para notar cuándo se
            # miraba la malla "del lado de adentro". Se desactivó porque
            # depende de que las normales estén orientadas de forma
            # GLOBALMENTE consistente hacia afuera, algo que
            # vtkPolyDataNormals (incluso con AutoOrientNormalsOn) no
            # garantiza en escaneos reales no cerrados/no-manifold: con
            # pie_mio_texturado.obj, toda la superficie plantar quedaba
            # marcada como "cara posterior" y se pintaba de ese tono cálido
            # en vez del gris esperado, justo la zona que más importa para
            # medir. Mismo vtkProperty para ambas caras = comportamiento
            # predecible sin importar el winding del archivo de origen.
            back_prop = vtkProperty()
            back_prop.SetColor(0.8, 0.8, 0.85)
            back_prop.SetSpecular(0.3)
            back_prop.SetSpecularPower(20)
            actor.SetBackfaceProperty(back_prop)

            # Remover actor anterior si existe
            if self.mesh_actor is not None:
                self.renderer.RemoveActor(self.mesh_actor)

            # Agregar nuevo actor
            self.mesh_actor = actor
            self.renderer.AddActor(self.mesh_actor)

            # Ajustar cámara
            self.renderer.ResetCamera()

            # Re-render
            self.render_window.Render()

            self.logger.info("Malla cargada exitosamente")
            self.mesh_loaded.emit(model)

        except Exception as e:
            self.logger.error(f"Error cargando malla: {e}")
            raise

    def _vertices_faces_to_polydata(
        self,
        vertices: np.ndarray,
        faces: np.ndarray
    ) -> vtkPolyData:
        """
        Convertir arrays de NumPy a vtkPolyData

        Args:
            vertices: Array Nx3 de coordenadas de vértices
            faces: Array Mx3 de índices de triángulos

        Returns:
            vtkPolyData listo para renderizar
        """
        # Crear puntos
        points = vtkPoints()
        points.SetNumberOfPoints(len(vertices))

        for i, vertex in enumerate(vertices):
            points.SetPoint(i, float(vertex[0]), float(vertex[1]), float(vertex[2]))

        # Crear celdas (triángulos)
        triangles = vtkCellArray()

        for face in faces:
            triangles.InsertNextCell(3)
            triangles.InsertCellPoint(int(face[0]))
            triangles.InsertCellPoint(int(face[1]))
            triangles.InsertCellPoint(int(face[2]))

        # Crear polydata
        poly_data = vtkPolyData()
        poly_data.SetPoints(points)
        poly_data.SetPolys(triangles)

        return poly_data

    def set_vertex_colors(self, colors: np.ndarray):
        """
        Colorear vértices según array RGB (ej. para el mapa de calor de
        altura). El número de filas debe coincidir con la cantidad de
        vértices de la malla cargada — `load_mesh()` desactiva el
        "splitting" de `vtkPolyDataNormals` específicamente para garantizar
        esta correspondencia 1:1 (sin eso, VTK duplica vértices en bordes
        filosos y el índice se desalinea).

        Args:
            colors: Array Nx3 con valores RGB (0-1) o (0-255)
        """
        if self.mesh_actor is None or self.current_model is None:
            self.logger.warning("No hay malla cargada")
            return

        colors = np.asarray(colors)
        # Escalar si es necesario
        if colors.max() > 1:
            colors = colors.astype(np.uint8)
        else:
            colors = (colors * 255).astype(np.uint8)

        self.current_model.vertex_colors = colors

        mapper = self.mesh_actor.GetMapper()
        poly_data = mapper.GetInput()
        if poly_data is None:
            self.logger.error("No hay polydata en mapper")
            return

        if len(colors) != poly_data.GetNumberOfPoints():
            self.logger.error(
                f"set_vertex_colors: {len(colors)} colores no coincide con "
                f"{poly_data.GetNumberOfPoints()} puntos de la malla"
            )
            return

        from vtkmodules.vtkCommonCore import VTK_UNSIGNED_CHAR

        color_array = numpy_to_vtk(np.ascontiguousarray(colors), deep=True, array_type=VTK_UNSIGNED_CHAR)
        color_array.SetName("Colors")
        poly_data.GetPointData().SetScalars(color_array)

        self.render_window.Render()
        self.logger.info("Colores de vértices aplicados")

    def clear_vertex_colors(self):
        """Quitar el coloreado por vértice (ej. al apagar el mapa de calor)"""
        if self.mesh_actor is None or self.current_model is None:
            return

        mapper = self.mesh_actor.GetMapper()
        poly_data = mapper.GetInput()
        if poly_data is not None:
            poly_data.GetPointData().SetScalars(None)

        self.current_model.vertex_colors = None
        self.render_window.Render()

    def has_texture(self) -> bool:
        """Si el modelo cargado tiene textura disponible para mostrar"""
        return self.current_model is not None and self.current_model.texture is not None

    def set_texture_visible(self, visible: bool):
        """
        Mostrar/ocultar la textura del pie sobre la malla. La malla con
        textura es una polydata separada de la "plana" (más vértices, por
        las costuras de UV — ver `TextureData`); activar la textura
        intercambia cuál polydata usa el mapper del actor, no modifica la
        malla plana que usan el picking, el mapa de calor o las mediciones.

        Args:
            visible: True para mostrar la textura, False para volver al
                     color sólido/mapa de calor
        """
        if self.mesh_actor is None or self.current_model is None:
            return

        mapper = self.mesh_actor.GetMapper()

        if visible:
            if self.current_model.texture is None:
                self.logger.warning("El modelo actual no tiene textura cargada")
                return
            if self._texture_polydata is None:
                self._texture_polydata, self._vtk_texture = self._build_texture_polydata(
                    self.current_model.texture
                )
            mapper.SetInputData(self._texture_polydata)
            mapper.ScalarVisibilityOff()
            self.mesh_actor.SetTexture(self._vtk_texture)
            self._texture_visible = True
        else:
            if self._plain_polydata is not None:
                mapper.SetInputData(self._plain_polydata)
            mapper.ScalarVisibilityOn()
            self.mesh_actor.SetTexture(None)
            self._texture_visible = False

        self.render_window.Render()

    def _build_texture_polydata(self, texture_data: TextureData) -> Tuple[vtkPolyData, vtkTexture]:
        """
        Armar la polydata de render con textura (posiciones expandidas +
        UV) y el objeto `vtkTexture` con la imagen ya cargada. Se llama una
        sola vez por modelo — el resultado se cachea en `_texture_polydata`
        / `_vtk_texture`.
        """
        points = vtkPoints()
        points.SetNumberOfPoints(len(texture_data.vertices))
        for i, vertex in enumerate(texture_data.vertices):
            points.SetPoint(i, float(vertex[0]), float(vertex[1]), float(vertex[2]))

        triangles = vtkCellArray()
        for face in texture_data.faces:
            triangles.InsertNextCell(3)
            triangles.InsertCellPoint(int(face[0]))
            triangles.InsertCellPoint(int(face[1]))
            triangles.InsertCellPoint(int(face[2]))

        poly_data = vtkPolyData()
        poly_data.SetPoints(points)
        poly_data.SetPolys(triangles)

        uv_array = numpy_to_vtk(np.ascontiguousarray(texture_data.uvs, dtype=np.float32), deep=True)
        uv_array.SetNumberOfComponents(2)
        poly_data.GetPointData().SetTCoords(uv_array)

        if vtkPolyDataNormals is not None:
            try:
                normals_filter = vtkPolyDataNormals()
                normals_filter.SetInputData(poly_data)
                normals_filter.SetFeatureAngle(45.0)
                normals_filter.SplittingOff()
                # Ver comentario equivalente en load_mesh(): sin esto la
                # orientación "hacia afuera" depende del winding del OBJ
                # de origen, que puede no coincidir con lo que espera la
                # cámara plantar/dorsal de la app.
                normals_filter.ConsistencyOn()
                normals_filter.AutoOrientNormalsOn()
                normals_filter.Update()
                poly_data = normals_filter.GetOutput()
            except Exception as e:
                self.logger.warning(f"No se pudieron calcular normales para la malla texturada: {e}")

        ext = Path(texture_data.image_path).suffix.lower()
        if ext == '.png':
            reader = vtkPNGReader()
        elif ext in ('.jpg', '.jpeg'):
            reader = vtkJPEGReader()
        else:
            raise ValueError(f"Formato de imagen de textura no soportado: {ext}")
        reader.SetFileName(texture_data.image_path)
        reader.Update()

        texture = vtkTexture()
        texture.SetInputConnection(reader.GetOutputPort())
        texture.InterpolateOn()

        return poly_data, texture

    def draw_support_plane(
        self,
        plane_center: np.ndarray,
        plane_normal: np.ndarray,
        width: float = 100,
        height: float = 100,
    ):
        """
        Dibujar plano de apoyo

        Args:
            plane_center: Centro del rectángulo a dibujar (no necesariamente
                uno de los 3 puntos clickeados: para que el rectángulo cubra
                bien la huella del pie, el caller debe pasar el centro real
                de la proyección de la malla sobre el plano, no un punto
                cualquiera sobre él — ver `compute_plane_footprint`)
            plane_normal: Normal al plano (vector 3D normalizado)
            width: Ancho del rectángulo a lo largo de la primera tangente
            height: Ancho del rectángulo a lo largo de la segunda tangente

        Nota: las tangentes se calculan acá con el mismo criterio
        determinístico que usa `compute_plane_footprint()` en
        `measurements.py` (mismo chequeo de `abs(normal[2]) < 0.9`), para que
        el rectángulo dibujado coincida con el que se usó para medir la
        huella. Si se cambia el criterio en un lado hay que cambiarlo en
        el otro.
        """
        try:
            # Crear dos vectores tangentes al plano
            # Si normal es cercano a [0,0,1], usar [1,0,0] como tangente
            if abs(plane_normal[2]) < 0.9:
                tangent1 = np.array([0, 0, 1])
            else:
                tangent1 = np.array([1, 0, 0])

            tangent1 = tangent1 - np.dot(tangent1, plane_normal) * plane_normal
            tangent1 = tangent1 / np.linalg.norm(tangent1)

            tangent2 = np.cross(plane_normal, tangent1)
            tangent2 = tangent2 / np.linalg.norm(tangent2)

            # Crear 4 esquinas del rectángulo
            half_width = width / 2
            half_height = height / 2
            corners = [
                plane_center + half_width * tangent1 + half_height * tangent2,
                plane_center - half_width * tangent1 + half_height * tangent2,
                plane_center - half_width * tangent1 - half_height * tangent2,
                plane_center + half_width * tangent1 - half_height * tangent2,
            ]

            # Crear polydata
            points = vtkPoints()
            for i, corner in enumerate(corners):
                points.InsertNextPoint(float(corner[0]), float(corner[1]), float(corner[2]))

            # Crear quad
            quad = vtkCellArray()
            quad.InsertNextCell(4, [0, 1, 2, 3])

            plane_poly = vtkPolyData()
            plane_poly.SetPoints(points)
            plane_poly.SetPolys(quad)

            # Crear actor
            mapper = vtkPolyDataMapper()
            mapper.SetInputData(plane_poly)

            actor = vtkActor()
            actor.SetMapper(mapper)

            # Propiedades: semi-transparente
            prop = actor.GetProperty()
            prop.SetColor(0.2, 0.6, 0.8)  # Azul claro
            prop.SetOpacity(0.3)
            prop.EdgeVisibilityOn()
            prop.SetEdgeColor(0.2, 0.4, 0.6)
            # El plano se dibuja con margen extra respecto a la huella real
            # (ver compute_plane_footprint), así que puede sobresalir un poco
            # más allá del borde de la malla — sin esto, un click cerca del
            # borde del pie podría seleccionar el plano en vez de la malla.
            actor.PickableOff()

            # Remover plano anterior si existe
            if self.support_plane_actor is not None:
                self.renderer.RemoveActor(self.support_plane_actor)

            self.support_plane_actor = actor
            self._plane_origin = np.asarray(plane_center, dtype=np.float64)
            self._plane_normal = np.asarray(plane_normal, dtype=np.float64)
            self.renderer.AddActor(self.support_plane_actor)

            self.render_window.Render()
            self.logger.info("Plano de apoyo dibujado")

        except Exception as e:
            self.logger.error(f"Error dibujando plano: {e}")

    def set_plane_visible(self, visible: bool):
        """
        Mostrar/ocultar el plano de apoyo sin borrarlo (a diferencia de
        `reset_measurements`, que sí lo elimina). Útil para dejar de ver el
        plano momentáneamente sin perder la medición ni tener que
        redefinirlo.
        """
        if self.support_plane_actor is not None:
            self.support_plane_actor.SetVisibility(1 if visible else 0)
            self.render_window.Render()

    def enable_picking(self, enabled: bool):
        """
        Activar/desactivar la selección de puntos sobre la malla con click izquierdo.

        Se distingue "click" de "arrastre" comparando la posición del mouse
        entre press y release: si no se movió (dentro de una tolerancia en
        píxeles), se interpreta como selección de punto y se emite
        `point_selected`. Si se movió, se asume que fue una rotación de
        cámara y no se dispara el picking. Así conviven la selección de
        puntos y la rotación con el mismo botón, sin bloquear la interacción
        normal de la cámara.

        Implementado con un `eventFilter` de Qt sobre el widget interactor en
        vez de `AddObserver` de VTK sobre LeftButtonPressEvent/ReleaseEvent:
        en la versión de VTK usada acá, el método dedicado
        `vtkGenericRenderWindowInteractor.LeftButtonReleaseEvent()` no siempre
        dispara el evento observado (comprobado: `InvokeEvent()` directo sí
        lo hace, el método dedicado no), lo que dejaba el picking sin
        funcionar nunca. El eventFilter de Qt es la vía confiable.

        Args:
            enabled: True para activar picking, False para desactivar
        """
        if enabled and not self._picking_enabled:
            self._picking_enabled = True
            self._set_drag_cursor(False)
        elif not enabled and self._picking_enabled:
            self._picking_enabled = False
            self._press_pos = None
            self.hide_pick_preview()

    def set_pick_on_plane(self, enabled: bool):
        """
        Hacer que los clicks (y la previsualización) caigan sobre el plano de
        apoyo en vez de sobre la malla. Solo tiene efecto mientras el plano
        existe y está visible; si está oculto se vuelve a pickear la malla.
        """
        self._pick_on_plane = enabled

    def _plane_interaction_active(self) -> bool:
        return (
            self.support_plane_actor is not None
            and self._plane_origin is not None
            and bool(self.support_plane_actor.GetVisibility())
        )

    def _can_drag_markers(self) -> bool:
        return (
            not self._picking_enabled
            and bool(self._drag_targets)
            and self._plane_interaction_active()
        )

    def eventFilter(self, obj, event):
        if obj is self.interactor:
            event_type = event.type()
            is_left = (
                event_type in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease)
                and event.button() == Qt.MouseButton.LeftButton
            )
            if event_type == QEvent.Type.MouseButtonPress and is_left:
                if self._can_drag_markers():
                    hit = self._find_marker_at(event.position())
                    if hit is not None:
                        self._drag_state = hit
                        # Consumir el evento: si no, la cámara también rotaría.
                        return True
                self._press_pos = event.position()
            elif event_type == QEvent.Type.MouseButtonRelease and is_left:
                if self._drag_state is not None:
                    measurement_id = self._drag_state[0]
                    self._drag_state = None
                    self.marker_drag_finished.emit(measurement_id)
                    return True
                self._handle_click_release(event)
            elif event_type == QEvent.Type.MouseMove:
                if self._drag_state is not None:
                    point = self._plane_point_at(event.position())
                    if point is not None:
                        self._move_dragged_marker(point)
                    return True
                if self._picking_enabled:
                    self._handle_hover_preview(event.position())
                else:
                    self._set_drag_cursor(
                        self._can_drag_markers() and self._find_marker_at(event.position()) is not None
                    )
            elif event_type == QEvent.Type.Leave:
                self.hide_pick_preview()
        return super().eventFilter(obj, event)

    def _qt_pos_to_vtk_pixel(self, pos) -> Tuple[int, int]:
        """
        Convertir una posición de Qt (local al widget, origen arriba-
        izquierda) a coordenadas de píxel de dispositivo de VTK (origen
        abajo-izquierda), como espera `vtkCellPicker.Pick()`.
        """
        scale = self.interactor.devicePixelRatioF()
        x = int(round(pos.x() * scale))
        y = int(round((self.interactor.height() - pos.y() - 1) * scale))
        return x, y

    def _display_to_world(self, x: float, y: float, depth: float) -> np.ndarray:
        self.renderer.SetDisplayPoint(x, y, depth)
        self.renderer.DisplayToWorld()
        world = self.renderer.GetWorldPoint()
        return np.array(world[:3]) / world[3]

    def _world_to_display(self, point: np.ndarray) -> Tuple[float, float]:
        self.renderer.SetWorldPoint(float(point[0]), float(point[1]), float(point[2]), 1.0)
        self.renderer.WorldToDisplay()
        display = self.renderer.GetDisplayPoint()
        return display[0], display[1]

    def _plane_point_at(self, pos) -> Optional[np.ndarray]:
        """Punto del plano de apoyo bajo el cursor (rayo de cámara ∩ plano)"""
        x, y = self._qt_pos_to_vtk_pixel(pos)
        near = self._display_to_world(x, y, 0.0)
        far = self._display_to_world(x, y, 1.0)
        return intersect_ray_plane(near, far - near, self._plane_origin, self._plane_normal)

    def _pick_point(self, pos) -> Optional[np.ndarray]:
        """Punto 3D bajo el cursor: sobre el plano si corresponde, si no sobre la malla"""
        if self._pick_on_plane and self._plane_interaction_active():
            return self._plane_point_at(pos)
        x, y = self._qt_pos_to_vtk_pixel(pos)
        picked = self.picker.Pick(x, y, 0, self.renderer)
        if picked and self.picker.GetCellId() != -1:
            return np.array(self.picker.GetPickPosition())
        return None

    def _handle_click_release(self, event) -> None:
        CLICK_TOLERANCE_PX = 3

        press_pos = self._press_pos
        self._press_pos = None

        if not self._picking_enabled or press_pos is None or self.mesh_actor is None:
            return

        release_pos = event.position()
        dx = release_pos.x() - press_pos.x()
        dy = release_pos.y() - press_pos.y()

        if (dx * dx + dy * dy) ** 0.5 > CLICK_TOLERANCE_PX:
            return  # Fue un arrastre (rotación de cámara), no un click

        position = self._pick_point(release_pos)
        if position is not None:
            self.point_selected.emit(position)

    def _handle_hover_preview(self, pos) -> None:
        """Actualizar la esfera de previsualización según dónde apunta el mouse"""
        if self.mesh_actor is None:
            return

        position = self._pick_point(pos)
        if position is not None:
            self.show_pick_preview(position)
        else:
            self.hide_pick_preview()

    def _set_drag_cursor(self, over_marker: bool):
        if over_marker:
            self.interactor.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.interactor.unsetCursor()

    @staticmethod
    def _source_of(actor: vtkActor):
        return actor.GetMapper().GetInputConnection(0, 0).GetProducer()

    def _find_marker_at(self, pos) -> Optional[Tuple[int, int]]:
        """(id de medición, 0/1) del marcador de distancia más cercano al cursor, si hay uno cerca"""
        MARKER_GRAB_RADIUS_PX = 14
        x, y = self._qt_pos_to_vtk_pixel(pos)
        threshold = MARKER_GRAB_RADIUS_PX * self.interactor.devicePixelRatioF()
        best = None
        for measurement_id, target in self._drag_targets.items():
            for index, marker in enumerate(target['markers']):
                mx, my = self._world_to_display(np.array(self._source_of(marker).GetCenter()))
                distance = ((mx - x) ** 2 + (my - y) ** 2) ** 0.5
                if distance <= threshold and (best is None or distance < best[0]):
                    best = (distance, measurement_id, index)
        return (best[1], best[2]) if best else None

    def _project_to_plane(self, point: np.ndarray) -> np.ndarray:
        offset = float(np.dot(point - self._plane_origin, self._plane_normal))
        return point - offset * self._plane_normal

    def _move_dragged_marker(self, point: np.ndarray):
        """Mover el marcador arrastrado y redibujar la línea entre los dos extremos"""
        measurement_id, index = self._drag_state
        target = self._drag_targets[measurement_id]
        self._source_of(target['markers'][index]).SetCenter(
            float(point[0]), float(point[1]), float(point[2])
        )
        centers = [np.array(self._source_of(m).GetCenter()) for m in target['markers']]
        start, end = (self._project_to_plane(c) for c in centers)
        line = self._source_of(target['line'])
        line.SetPoint1(*[float(c) for c in start])
        line.SetPoint2(*[float(c) for c in end])
        self.render_window.Render()
        self.marker_dragged.emit(measurement_id, index, np.array(point))

    def register_distance_drag(self, measurement_id: int, markers: List[vtkActor], line: vtkActor):
        """
        Hacer arrastrables (sobre el plano, mientras esté visible) los dos
        marcadores de una medición de distancia. `markers` va en orden
        [punto inicial, punto final]; `line` es la línea que los une.
        """
        self._drag_targets[measurement_id] = {'markers': list(markers), 'line': line}

    def show_pick_preview(self, point: np.ndarray):
        """
        Mostrar (o reposicionar, si ya existe) la esfera de previsualización
        en un punto, antes de que el usuario confirme el click. Semi-
        transparente y de color neutro para distinguirla claramente de un
        marcador ya confirmado.
        """
        if self._preview_sphere_source is None:
            self._preview_sphere_source = vtkSphereSource()
            self._preview_sphere_source.SetThetaResolution(16)
            self._preview_sphere_source.SetPhiResolution(16)

            mapper = vtkPolyDataMapper()
            mapper.SetInputConnection(self._preview_sphere_source.GetOutputPort())

            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(1.0, 1.0, 1.0)
            actor.GetProperty().SetOpacity(0.5)
            actor.PickableOff()

            self._preview_marker_actor = actor
            self.overlay_renderer.AddActor(actor)

        self._preview_sphere_source.SetRadius(self._default_marker_radius())
        self._preview_sphere_source.SetCenter(float(point[0]), float(point[1]), float(point[2]))
        self._preview_marker_actor.SetVisibility(1)
        self.render_window.Render()

    def hide_pick_preview(self):
        """Ocultar la esfera de previsualización (el cursor salió de la malla o del canvas)"""
        if self._preview_marker_actor is not None and self._preview_marker_actor.GetVisibility():
            self._preview_marker_actor.SetVisibility(0)
            self.render_window.Render()

    def _default_marker_radius(self) -> float:
        """Radio de marcador proporcional al tamaño del modelo cargado"""
        if self.current_model is not None and self.current_model.bounds is not None:
            x_min, x_max, y_min, y_max, z_min, z_max = self.current_model.bounds
            diag = max(x_max - x_min, y_max - y_min, z_max - z_min)
            return max(diag * 0.01, 0.5)
        return 1.0

    def _remove_actor(self, actor: vtkActor):
        """Quitar un actor de donde esté (capa normal o superior)"""
        self.renderer.RemoveActor(actor)
        self.overlay_renderer.RemoveActor(actor)

    def add_marker(
        self,
        point: np.ndarray,
        color: Tuple[float, float, float] = (1.0, 0.2, 0.2),
        on_top: bool = False,
    ) -> vtkActor:
        """
        Crear un marcador esférico en un punto (feedback visual de picking).
        No lo asocia a ningún seguimiento por sí solo — el caller decide si
        va a `plane_marker_actors` (vía `add_plane_marker`) o a los actores
        de una medición puntual (vía `register_measurement_visuals`).

        Args:
            point: Punto 3D donde dibujar el marcador
            color: Color RGB (0-1)
            on_top: Dibujarlo siempre por encima de la malla

        Returns:
            El actor VTK creado
        """
        sphere = vtkSphereSource()
        sphere.SetCenter(float(point[0]), float(point[1]), float(point[2]))
        sphere.SetRadius(self._default_marker_radius())
        sphere.SetThetaResolution(16)
        sphere.SetPhiResolution(16)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        # Que el propio marcador no se pueda picker: si no, un click cerca de
        # un punto ya marcado podría seleccionar la esfera del marcador en
        # vez de la malla real de abajo.
        actor.PickableOff()

        (self.overlay_renderer if on_top else self.renderer).AddActor(actor)
        self.render_window.Render()
        return actor

    def set_landmark_marker(self, key: str, point: np.ndarray, color: Tuple[float, float, float]):
        """Dibujar (o reemplazar) el marcador de un punto de referencia"""
        self.remove_landmark_marker(key)
        self.landmark_actors[key] = self.add_marker(point, color=color)

    def remove_landmark_marker(self, key: str):
        actor = self.landmark_actors.pop(key, None)
        if actor is not None:
            self._remove_actor(actor)
            self.render_window.Render()

    def add_plane_marker(self, point: np.ndarray) -> vtkActor:
        """Marcador de uno de los 3 puntos usados para definir el plano de apoyo"""
        actor = self.add_marker(point, color=(0.2, 0.8, 1.0))
        self.plane_marker_actors.append(actor)
        return actor

    def clear_plane_markers(self):
        """Quitar los marcadores de los puntos que definen el plano de apoyo"""
        for actor in self.plane_marker_actors:
            self._remove_actor(actor)
        self.plane_marker_actors = []
        self.render_window.Render()

    def remove_last_plane_marker(self):
        """Quitar solo el último marcador de punto del plano agregado (para deshacer un click)"""
        if self.plane_marker_actors:
            actor = self.plane_marker_actors.pop()
            self._remove_actor(actor)
            self.render_window.Render()

    def register_measurement_visuals(self, measurement_id: int, actors: List[vtkActor]):
        """
        Asociar uno o más actores (marcador(es), línea) a una medición, para
        poder borrarlos selectivamente más adelante con `remove_measurement`.

        Args:
            measurement_id: Id de la Measurement (ver `Measurement.id`)
            actors: Actores VTK ya agregados al renderer (creados con
                    `add_marker`/`add_measurement_line`)
        """
        self.measurement_visuals.setdefault(measurement_id, []).extend(actors)

    def remove_actors(self, actors: List[vtkActor]):
        """
        Quitar actores sueltos del canvas (ej. marcadores de una medición de
        2 clicks cancelada después del primero, que todavía no llegó a
        registrarse con `register_measurement_visuals`).
        """
        for actor in actors:
            self._remove_actor(actor)
        if actors:
            self.render_window.Render()

    def remove_measurement(self, measurement_id: int):
        """Quitar del canvas todos los actores asociados a una medición puntual"""
        actors = self.measurement_visuals.pop(measurement_id, [])
        self._drag_targets.pop(measurement_id, None)
        for actor in actors:
            self._remove_actor(actor)
        if actors:
            self.render_window.Render()

    def add_measurement_line(
        self,
        point_a: np.ndarray,
        point_b: np.ndarray,
        color: Tuple[float, float, float] = (1.0, 0.8, 0.0),
        on_top: bool = False,
    ) -> vtkActor:
        """
        Crear una línea entre dos puntos para visualizar una medición (altura
        de arco o distancia en el plano). No la asocia a ningún seguimiento
        por sí sola — usar `register_measurement_visuals` para poder
        borrarla junto con sus marcadores más adelante.

        Args:
            point_a: Primer extremo de la línea
            point_b: Segundo extremo de la línea
            color: Color RGB (0-1) de la línea
            on_top: Dibujarla siempre por encima de la malla

        Returns:
            El actor VTK creado
        """
        line = vtkLineSource()
        line.SetPoint1(*[float(c) for c in point_a])
        line.SetPoint2(*[float(c) for c in point_b])

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(line.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().SetLineWidth(3)
        actor.PickableOff()

        (self.overlay_renderer if on_top else self.renderer).AddActor(actor)
        self.render_window.Render()
        return actor

    def show_measurement_text(self, text: str):
        """
        Mostrar texto superpuesto en la esquina del canvas (ej. valor de medición)

        Args:
            text: Texto a mostrar
        """
        if self.measurement_text_actor is None:
            self.measurement_text_actor = vtkTextActor()
            text_prop = self.measurement_text_actor.GetTextProperty()
            text_prop.SetFontSize(20)
            text_prop.SetColor(1.0, 1.0, 1.0)
            text_prop.SetBold(True)
            self.measurement_text_actor.SetPosition(10, 10)
            # AddActor2D fue reemplazado por el AddActor genérico en VTK 9.7+
            # (que acepta vtkActor2D igual que vtkActor); AddActor2D directamente
            # no existe en vtkRenderer en esta versión instalada.
            self.renderer.AddActor(self.measurement_text_actor)

        self.measurement_text_actor.SetInput(text)
        self.render_window.Render()

    def clear_measurement_text(self):
        """Quitar el texto de medición superpuesto"""
        if self.measurement_text_actor is not None:
            self.renderer.RemoveActor(self.measurement_text_actor)
            self.measurement_text_actor = None
            self.render_window.Render()

    def reset_measurements(self):
        """Limpiar plano de apoyo, marcadores, líneas y texto de medición del canvas"""
        self.clear_plane_markers()
        if self.support_plane_actor is not None:
            self.renderer.RemoveActor(self.support_plane_actor)
            self.support_plane_actor = None
        self._plane_origin = None
        self._plane_normal = None
        self._drag_targets = {}
        self._drag_state = None
        for actor in self.landmark_actors.values():
            self._remove_actor(actor)
        self.landmark_actors = {}
        for actors in self.measurement_visuals.values():
            for actor in actors:
                self._remove_actor(actor)
        self.measurement_visuals = {}
        self.clear_measurement_text()
        self.render_window.Render()

    def show_axes(self, show: bool = True):
        """
        Mostrar/ocultar ejes de coordenadas

        Args:
            show: True para mostrar, False para ocultar
        """
        try:
            if show:
                if self.axes_actor is None:
                    self.axes_actor = vtkAxesActor()
                    self.axes_actor.PickableOff()
                    # Escalar ejes
                    if self.current_model and self.current_model.bounds:
                        x_min, x_max, y_min, y_max, z_min, z_max = self.current_model.bounds
                        scale = (max(x_max - x_min, y_max - y_min, z_max - z_min)) / 3
                        self.axes_actor.SetTotalLength(scale, scale, scale)

                self.renderer.AddActor(self.axes_actor)
            else:
                if self.axes_actor is not None:
                    self.renderer.RemoveActor(self.axes_actor)

            self.render_window.Render()
        except Exception as e:
            self.logger.error(f"Error al mostrar ejes: {e}")

    def _set_camera_view(self, position: np.ndarray, focal_point: np.ndarray, view_up: np.ndarray):
        """
        Establecer posición de cámara

        Args:
            position: Posición de la cámara
            focal_point: Punto focal
            view_up: Vector "arriba" de la vista
        """
        if self.current_model is None:
            return

        camera = self.renderer.GetActiveCamera()
        camera.SetPosition(position[0], position[1], position[2])
        camera.SetFocalPoint(focal_point[0], focal_point[1], focal_point[2])
        camera.SetViewUp(view_up[0], view_up[1], view_up[2])
        # ResetCamera() DESPUÉS de fijar dirección/foco: ajusta la distancia a
        # lo largo de esa dirección para que el bounding box completo entre en
        # cuadro, en vez de dejar la distancia fija que pasó el caller (que
        # puede quedar muy cerca o muy lejos según el tamaño real del modelo).
        # Llamarlo ANTES (como estaba) ajusta el clipping para la cámara
        # VIEJA y además el picking, que depende de ese rango, falla en
        # silencio aunque el render se vea bien.
        self.renderer.ResetCamera()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()

    def reset_camera(self):
        """Resetear cámara a vista inicial"""
        self.renderer.ResetCamera()
        self.render_window.Render()

    def capture_screenshot(self, filepath: str):
        """
        Capturar la vista actual del canvas (malla + plano + marcadores +
        mediciones tal como se ven en pantalla) y guardarla como PNG. Se usa
        para incluir una imagen del pie en el informe PDF.

        Args:
            filepath: Ruta del archivo .png a escribir
        """
        w2i = vtkWindowToImageFilter()
        w2i.SetInput(self.render_window)
        w2i.SetInputBufferTypeToRGB()
        w2i.ReadFrontBufferOff()
        w2i.Update()

        writer = vtkPNGWriter()
        writer.SetFileName(filepath)
        writer.SetInputConnection(w2i.GetOutputPort())
        writer.Write()
        self.logger.info(f"Captura de pantalla guardada: {filepath}")

    def set_view_dorsal(self):
        """Vista dorsal (desde arriba), con los dedos hacia arriba y el talón hacia abajo"""
        if self.current_model is None:
            return

        center = self.current_model.center if self.current_model.center is not None else np.array([0, 0, 0])
        position = center + np.array([0, 0, 200])
        focal_point = center
        # -Y arriba: gira la imagen 180° respecto de la convención anterior
        # (+Y arriba), que dejaba los dedos hacia abajo en los escaneos.
        view_up = np.array([0, -1, 0])
        self._set_camera_view(position, focal_point, view_up)

    def set_view_isometric(self):
        """Vista isométrica"""
        if self.current_model is None:
            return

        center = self.current_model.center if self.current_model.center is not None else np.array([0, 0, 0])
        distance = 150
        position = center + np.array([distance, distance, distance])
        focal_point = center
        view_up = np.array([0, 0, 1])
        self._set_camera_view(position, focal_point, view_up)

    def clear(self):
        """Limpiar canvas"""
        if self.mesh_actor is not None:
            self.renderer.RemoveActor(self.mesh_actor)
            self.mesh_actor = None

        self.reset_measurements()
        self.enable_picking(False)

        self.current_model = None
        self.render_window.Render()
        self.logger.info("Canvas limpiado")
