"""
Modelo de datos para el pie y su malla 3D
"""
from dataclasses import dataclass, field
from typing import Optional, Tuple
import itertools
import numpy as np

_measurement_id_counter = itertools.count(1)

# Puntos de referencia anatómicos que marca el usuario sobre la malla (claves
# estables, que van tal cual al JSON del proyecto, y su nombre para mostrar).
LANDMARK_METATARSAL_1 = 'metatarsal_1'
LANDMARK_METATARSAL_5 = 'metatarsal_5'
LANDMARK_HEEL = 'heel_distal'
LANDMARK_LABELS = {
    LANDMARK_METATARSAL_1: "Cabeza 1er metatarsiano",
    LANDMARK_METATARSAL_5: "Cabeza 5to metatarsiano",
    LANDMARK_HEEL: "Punto distal del talón",
}


@dataclass
class TextureData:
    """
    Datos para renderizar la malla con su textura (foto del pie envuelta
    sobre la superficie), separados de FootModel.vertices/faces.

    Por qué separados: las coordenadas UV de un OBJ están indexadas aparte
    de las posiciones (un mismo vértice de posición puede necesitar varias
    UV distintas en las costuras del "unwrap" de textura), así que la malla
    de render con textura tiene más vértices que la malla de posiciones
    pura — no sirven para cálculos de medición (plano, alturas, distancias),
    que siguen usando exclusivamente FootModel.vertices/faces.
    """
    vertices: np.ndarray  # Nx3, posiciones (con duplicados en costuras UV)
    uvs: np.ndarray       # Nx2, coordenada UV de cada vértice de `vertices`
    faces: np.ndarray     # Mx3, índices de triángulos sobre `vertices`
    image_path: str       # ruta absoluta a la imagen de textura (map_Kd)


@dataclass
class FootModel:
    """
    Representa un modelo 3D de pie cargado desde STL
    """
    vertices: np.ndarray
    faces: np.ndarray
    filepath: str = ""
    filename: str = ""
    bounds: Optional[Tuple[float, float, float, float, float, float]] = None
    center: Optional[np.ndarray] = None
    scale: float = 1.0
    support_plane: Optional['SupportPlane'] = None
    num_triangles: int = 0
    num_vertices: int = 0
    vertex_colors: Optional[np.ndarray] = None
    texture: Optional[TextureData] = None
    is_valid: bool = True
    validation_warnings: list = field(default_factory=list)

    def __post_init__(self):
        if self.vertices is not None:
            self.num_vertices = len(self.vertices)
        if self.faces is not None:
            self.num_triangles = len(self.faces)

    def compute_bounds(self) -> Tuple[float, float, float, float, float, float]:
        if self.vertices is None or len(self.vertices) == 0:
            return (0, 0, 0, 0, 0, 0)
        min_coords = np.min(self.vertices, axis=0)
        max_coords = np.max(self.vertices, axis=0)
        self.bounds = tuple([val for pair in zip(min_coords, max_coords) for val in pair])
        return self.bounds

    def compute_center(self) -> np.ndarray:
        if self.vertices is None or len(self.vertices) == 0:
            self.center = np.array([0, 0, 0])
        else:
            self.center = np.mean(self.vertices, axis=0)
        return self.center

    def get_dimensions(self) -> Tuple[float, float, float]:
        if self.bounds is None:
            self.compute_bounds()
        if self.bounds:
            x_min, x_max, y_min, y_max, z_min, z_max = self.bounds
            return (x_max - x_min, y_max - y_min, z_max - z_min)
        return (0, 0, 0)

    def normalize_scale(self, target_scale: float = 100.0):
        dims = self.get_dimensions()
        max_dim = max(dims)
        if max_dim > 0:
            self.scale = target_scale / max_dim
            self.vertices = self.vertices * self.scale

    def center_at_origin(self):
        self.compute_center()
        if self.center is not None:
            self.vertices = self.vertices - self.center
            self.compute_center()


@dataclass
class SupportPlane:
    """Representa el plano de apoyo (base de vidrio del escáner)"""
    point1: np.ndarray
    point2: np.ndarray
    point3: np.ndarray
    normal: Optional[np.ndarray] = None
    d: Optional[float] = None

    def compute_plane_equation(self):
        v1 = self.point2 - self.point1
        v2 = self.point3 - self.point1
        self.normal = np.cross(v1, v2)
        magnitude = np.linalg.norm(self.normal)
        if magnitude > 1e-10:
            self.normal = self.normal / magnitude
        self.d = -np.dot(self.normal, self.point1)

    def distance_to_point(self, point: np.ndarray) -> float:
        if self.normal is None:
            self.compute_plane_equation()
        return np.dot(self.normal, point) + self.d

    def project_point(self, point: np.ndarray) -> np.ndarray:
        if self.normal is None:
            self.compute_plane_equation()
        dist = self.distance_to_point(point)
        return point - dist * self.normal


@dataclass
class Measurement:
    """Representa una medición realizada en el modelo"""
    name: str
    measurement_type: str
    value: float
    unit: str = 'mm'
    point1: Optional[np.ndarray] = None
    point2: Optional[np.ndarray] = None
    point3: Optional[np.ndarray] = None
    notes: str = ""
    timestamp: Optional[str] = None
    # Id único autogenerado (no pasar a mano): permite asociar cada medición
    # con sus actores visuales en el canvas para poder borrarla individualmente.
    id: int = field(default_factory=lambda: next(_measurement_id_counter))

    def __str__(self) -> str:
        return f"{self.name}: {self.value:.2f} {self.unit}"
