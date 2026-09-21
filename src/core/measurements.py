"""
Measurements - Cálculos geométricos para mediciones sobre la malla del pie

Responsabilidad:
- Definir el plano de apoyo a partir de 3 puntos pickeados en la base del pie
- Calcular la altura del arco: distancia perpendicular de un punto al plano
- Calcular distancias entre puntos proyectados sobre el plano
- Calcular el rectángulo (centro + dimensiones) que cubre la huella de la
  malla sobre el plano, para dibujarlo del tamaño correcto

Esta lógica se mantiene desacoplada de Qt/VTK (igual que MeshLoader) para
poder testearla sin depender de un entorno gráfico.
"""
import numpy as np
from src.models.foot_model import SupportPlane

# Puntos casi colineales o coincidentes no definen un plano estable.
# 1e-6 es conservador para coordenadas en mm (evita falsos positivos por
# redondeo de picking, pero rechaza planos realmente degenerados).
COLINEAR_TOLERANCE = 1e-6


class MeasurementError(Exception):
    """Error al calcular una medición geométrica"""
    pass


def compute_support_plane(
    point1: np.ndarray,
    point2: np.ndarray,
    point3: np.ndarray,
) -> SupportPlane:
    """
    Construir el plano de apoyo a partir de 3 puntos de la base del pie.

    Args:
        point1, point2, point3: Puntos 3D (picking en la vista 3D)

    Returns:
        SupportPlane con la ecuación del plano ya calculada (normal unitaria)

    Raises:
        MeasurementError: Si los puntos son colineales o coincidentes
                          (no definen un plano válido)
    """
    p1 = np.asarray(point1, dtype=np.float64)
    p2 = np.asarray(point2, dtype=np.float64)
    p3 = np.asarray(point3, dtype=np.float64)

    v1 = p2 - p1
    v2 = p3 - p1
    cross = np.cross(v1, v2)

    if np.linalg.norm(cross) < COLINEAR_TOLERANCE:
        raise MeasurementError(
            "Los 3 puntos seleccionados son colineales o coincidentes: "
            "no definen un plano válido. Elegí 3 puntos bien separados en la base."
        )

    plane = SupportPlane(point1=p1, point2=p2, point3=p3)
    plane.compute_plane_equation()
    return plane


def compute_arch_height(plane: SupportPlane, apex_point: np.ndarray) -> float:
    """
    Calcular la altura del arco: distancia perpendicular (siempre positiva)
    desde el plano de apoyo hasta el punto seleccionado sobre el arco.

    Args:
        plane: Plano de apoyo ya calculado (ver compute_support_plane)
        apex_point: Punto 3D seleccionado manualmente sobre el arco

    Returns:
        Distancia perpendicular en las mismas unidades que la malla (mm)
    """
    point = np.asarray(apex_point, dtype=np.float64)
    signed_distance = plane.distance_to_point(point)
    return abs(float(signed_distance))


def compute_plane_distance(plane: SupportPlane, point_a: np.ndarray, point_b: np.ndarray) -> float:
    """
    Calcular la distancia entre dos puntos "en el plano de apoyo": cada punto
    se proyecta primero sobre el plano y luego se mide la distancia entre las
    proyecciones. Sirve para medir extensiones de la superficie de apoyo
    (ancho, largo) sin que pequeñas diferencias de altura entre los dos
    puntos pickeados (ruido de picking, curvatura de la malla) distorsionen
    la medida.

    Args:
        plane: Plano de apoyo ya calculado (ver compute_support_plane)
        point_a: Primer punto 3D seleccionado
        point_b: Segundo punto 3D seleccionado

    Returns:
        Distancia entre las proyecciones de ambos puntos sobre el plano (mm)
    """
    a = np.asarray(point_a, dtype=np.float64)
    b = np.asarray(point_b, dtype=np.float64)
    projected_a = plane.project_point(a)
    projected_b = plane.project_point(b)
    return float(np.linalg.norm(projected_b - projected_a))


def compute_height_map(plane: SupportPlane, vertices: np.ndarray) -> np.ndarray:
    """
    Calcular la distancia perpendicular (valor absoluto) de cada vértice de
    la malla al plano de apoyo, vectorizado sobre todos los vértices a la
    vez. Es la versión "para toda la malla" de `compute_arch_height()`, para
    alimentar un mapa de calor.

    Args:
        plane: Plano de apoyo ya calculado
        vertices: Array Nx3 de vértices (ej. model.vertices)

    Returns:
        Array de N alturas (mm), siempre >= 0
    """
    vertices = np.asarray(vertices, dtype=np.float64)
    signed_distances = vertices @ plane.normal + plane.d
    return np.abs(signed_distances)


def height_map_to_colors(heights: np.ndarray) -> np.ndarray:
    """
    Convertir un array de alturas a colores RGB (0-255): gradiente azul
    (altura ~0, cerca del plano) → verde → rojo (altura máxima presente en
    el array). Se normaliza contra el máximo del propio array de entrada,
    no contra un valor absoluto fijo, para que el gradiente siempre use todo
    el rango de color disponible sea cual sea el tamaño real del pie.

    Args:
        heights: Array de N alturas no negativas (ver `compute_height_map`)

    Returns:
        Array Nx3 de enteros 0-255
    """
    heights = np.asarray(heights, dtype=np.float64)
    max_height = heights.max() if len(heights) > 0 else 0.0

    if max_height < 1e-9:
        # Toda la malla está sobre el plano (o casi): un solo color neutro
        return np.tile(np.array([60, 140, 220], dtype=np.uint8), (len(heights), 1))

    t = np.clip(heights / max_height, 0.0, 1.0)
    colors = np.zeros((len(heights), 3), dtype=np.uint8)

    lower = t <= 0.5
    upper = ~lower

    # Tramo bajo: azul (0,80,200) -> verde (0,200,80)
    t_lower = t[lower] / 0.5
    colors[lower, 0] = 0
    colors[lower, 1] = (80 + t_lower * 120).astype(np.uint8)
    colors[lower, 2] = (200 - t_lower * 120).astype(np.uint8)

    # Tramo alto: verde (0,200,80) -> rojo (220,40,40)
    t_upper = (t[upper] - 0.5) / 0.5
    colors[upper, 0] = (t_upper * 220).astype(np.uint8)
    colors[upper, 1] = (200 - t_upper * 160).astype(np.uint8)
    colors[upper, 2] = (80 - t_upper * 40).astype(np.uint8)

    return colors


def _plane_tangents(normal: np.ndarray):
    """
    Dos vectores tangentes ortonormales al plano. Mismo criterio
    determinístico (chequeo de `abs(normal[2]) < 0.9`) que usa
    `VTK3DView.draw_support_plane()` para elegir la tangente de partida —
    ambos lados deben coincidir para que el rectángulo dibujado sea
    consistente con el que se usó para calcular la huella.
    """
    if abs(normal[2]) < 0.9:
        tangent1 = np.array([0.0, 0.0, 1.0])
    else:
        tangent1 = np.array([1.0, 0.0, 0.0])

    tangent1 = tangent1 - np.dot(tangent1, normal) * normal
    tangent1 = tangent1 / np.linalg.norm(tangent1)

    tangent2 = np.cross(normal, tangent1)
    tangent2 = tangent2 / np.linalg.norm(tangent2)

    return tangent1, tangent2


def compute_plane_footprint(plane: SupportPlane, points: np.ndarray, margin: float = 1.15):
    """
    Calcular el centro y las dimensiones (ancho, alto) de un rectángulo sobre
    el plano de apoyo que cubre la proyección de un conjunto de puntos (por
    ejemplo, todos los vértices de la malla), con un margen extra.

    Se usa para dibujar el plano de apoyo del tamaño justo para cubrir toda
    la huella del pie, en vez de un tamaño arbitrario fijo que puede quedar
    más chico o descentrado según en qué 3 puntos haya clickeado el usuario
    para definirlo.

    Args:
        plane: Plano de apoyo ya calculado
        points: Array Nx3 de puntos a cubrir (ej. model.vertices)
        margin: Factor multiplicativo sobre el ancho/alto calculado, para
                dejar un borde visible más allá de la huella exacta (1.15 =
                15% de margen)

    Returns:
        Tupla (center, width, height): centro en coordenadas 3D, y
        dimensiones a lo largo de las tangentes del plano
    """
    points = np.asarray(points, dtype=np.float64)
    tangent1, tangent2 = _plane_tangents(plane.normal)

    # Proyección vectorizada de todos los puntos sobre el plano (evita un
    # loop en Python por vértice, relevante con mallas de decenas de miles
    # de puntos)
    signed_distances = points @ plane.normal + plane.d
    projected = points - np.outer(signed_distances, plane.normal)

    relative = projected - plane.point1
    coord1 = relative @ tangent1
    coord2 = relative @ tangent2

    width = (coord1.max() - coord1.min()) * margin
    height = (coord2.max() - coord2.min()) * margin

    center_coord1 = (coord1.max() + coord1.min()) / 2
    center_coord2 = (coord2.max() + coord2.min()) / 2
    center = plane.point1 + center_coord1 * tangent1 + center_coord2 * tangent2

    return center, float(width), float(height)
