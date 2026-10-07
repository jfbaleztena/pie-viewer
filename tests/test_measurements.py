"""Tests de measurements: plano de apoyo y altura del arco"""
import pytest
import numpy as np
from src.core.measurements import (
    compute_support_plane,
    compute_arch_height,
    compute_plane_distance,
    compute_plane_footprint,
    compute_height_map,
    height_map_to_colors,
    intersect_ray_plane,
    MeasurementError,
)


class TestComputeSupportPlane:
    """Tests para la construcción del plano de apoyo a partir de 3 puntos"""

    def test_plane_in_xy_normal_is_z_axis(self):
        p1 = np.array([0, 0, 0])
        p2 = np.array([10, 0, 0])
        p3 = np.array([0, 10, 0])
        plane = compute_support_plane(p1, p2, p3)
        assert plane.normal is not None
        # La normal debe ser el eje Z (con signo dependiendo del orden de los puntos)
        assert np.allclose(np.abs(plane.normal), [0, 0, 1], atol=1e-9)

    def test_normal_is_unit_length(self):
        p1 = np.array([1, 2, 3])
        p2 = np.array([5, 2, 3])
        p3 = np.array([1, 9, 4])
        plane = compute_support_plane(p1, p2, p3)
        assert abs(np.linalg.norm(plane.normal) - 1.0) < 1e-9

    def test_plane_tilted(self):
        # Plano inclinado: z = x (normal proporcional a [-1, 0, 1])
        p1 = np.array([0, 0, 0])
        p2 = np.array([0, 10, 0])
        p3 = np.array([10, 0, 10])
        plane = compute_support_plane(p1, p2, p3)
        # Cualquier punto sobre el plano debe tener distancia ~0
        point_on_plane = np.array([5, 5, 5])
        assert abs(plane.distance_to_point(point_on_plane)) < 1e-9

    def test_colinear_points_raise_error(self):
        p1 = np.array([0, 0, 0])
        p2 = np.array([1, 0, 0])
        p3 = np.array([2, 0, 0])
        with pytest.raises(MeasurementError):
            compute_support_plane(p1, p2, p3)

    def test_coincident_points_raise_error(self):
        p1 = np.array([1, 1, 1])
        p2 = np.array([1, 1, 1])
        p3 = np.array([1, 1, 1])
        with pytest.raises(MeasurementError):
            compute_support_plane(p1, p2, p3)


class TestComputeArchHeight:
    """Tests para la distancia perpendicular punto-plano (altura del arco)"""

    def test_point_directly_above_plane(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        apex = np.array([3, 3, 25])
        assert abs(compute_arch_height(plane, apex) - 25.0) < 1e-9

    def test_point_below_plane_returns_positive(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        apex = np.array([3, 3, -25])
        assert abs(compute_arch_height(plane, apex) - 25.0) < 1e-9

    def test_point_on_plane_is_zero(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        apex = np.array([4, 6, 0])
        assert compute_arch_height(plane, apex) < 1e-9

    def test_height_on_tilted_plane(self):
        # Plano z=0 rotado no hace falta: usamos un plano ya inclinado
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([0, 10, 0]), np.array([10, 0, 10])
        )
        # Punto proyectado sobre el plano, desplazado a lo largo de la normal
        normal = plane.normal
        base_point = np.array([2.0, 2.0, 2.0])
        base_point = plane.project_point(base_point)
        apex = base_point + normal * 15.0
        assert abs(compute_arch_height(plane, apex) - 15.0) < 1e-6

    def test_project_point_lies_on_plane(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        point = np.array([3, 3, 40])
        projected = plane.project_point(point)
        assert abs(plane.distance_to_point(projected)) < 1e-9


class TestComputePlaneDistance:
    """Tests para la distancia entre dos puntos proyectados sobre el plano"""

    def test_distance_between_points_already_on_plane(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        a = np.array([0, 0, 0])
        b = np.array([3, 4, 0])
        assert abs(compute_plane_distance(plane, a, b) - 5.0) < 1e-9

    def test_height_difference_is_ignored(self):
        # Dos puntos con la misma posicion X/Y pero distinta altura sobre el
        # plano (Z): la distancia "en el plano" debe ser 0, no la distancia 3D
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        a = np.array([5, 5, 0])
        b = np.array([5, 5, 40])
        assert compute_plane_distance(plane, a, b) < 1e-9

    def test_distance_matches_3d_distance_for_points_on_plane(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        a = np.array([1, 1, 0])
        b = np.array([7, 9, 0])
        expected = np.linalg.norm(b - a)
        assert abs(compute_plane_distance(plane, a, b) - expected) < 1e-9

    def test_distance_on_tilted_plane(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([0, 10, 0]), np.array([10, 0, 10])
        )
        # Dos puntos ya sobre el plano, desplazados a lo largo de una tangente
        base = plane.project_point(np.array([2.0, 2.0, 2.0]))
        tangent = plane.point2 - plane.point1
        tangent = tangent / np.linalg.norm(tangent)
        other = base + tangent * 12.0
        assert abs(compute_plane_distance(plane, base, other) - 12.0) < 1e-6


class TestComputePlaneFootprint:
    """Tests para el rectángulo que cubre la huella de un conjunto de puntos sobre el plano"""

    def test_footprint_covers_flat_square_of_points(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        points = np.array([
            [0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0], [5, 5, 0],
        ])
        center, width, height = compute_plane_footprint(plane, points, margin=1.0)
        assert np.allclose(center, [5, 5, 0], atol=1e-9)
        assert abs(width - 10.0) < 1e-9
        assert abs(height - 10.0) < 1e-9

    def test_margin_scales_dimensions(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        points = np.array([[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]])
        _, width, height = compute_plane_footprint(plane, points, margin=1.2)
        assert abs(width - 12.0) < 1e-9
        assert abs(height - 12.0) < 1e-9

    def test_footprint_ignores_height_above_plane(self):
        # Puntos con la misma huella en X/Y pero distinta altura Z: el
        # rectangulo debe seguir cubriendo la misma huella proyectada
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        flat_points = np.array([[0, 0, 0], [10, 0, 0], [10, 10, 0], [0, 10, 0]])
        raised_points = flat_points + np.array([0, 0, 30])
        _, w1, h1 = compute_plane_footprint(plane, flat_points, margin=1.0)
        _, w2, h2 = compute_plane_footprint(plane, raised_points, margin=1.0)
        assert abs(w1 - w2) < 1e-9
        assert abs(h1 - h2) < 1e-9

    def test_center_lies_on_plane(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([0, 10, 0]), np.array([10, 0, 10])
        )
        points = np.array([[1, 1, 1], [5, 5, 6], [2, 8, 3], [9, 1, 9]])
        center, _, _ = compute_plane_footprint(plane, points)
        assert abs(plane.distance_to_point(center)) < 1e-9


class TestComputeHeightMap:
    """Tests para el mapa de alturas vectorizado (mapa de calor)"""

    def test_matches_compute_arch_height_per_point(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        vertices = np.array([[1, 1, 5], [2, 2, -8], [3, 3, 0]])
        heights = compute_height_map(plane, vertices)
        for v, h in zip(vertices, heights):
            assert abs(h - compute_arch_height(plane, v)) < 1e-9

    def test_all_nonnegative(self):
        plane = compute_support_plane(
            np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])
        )
        vertices = np.array([[1, 1, 5], [2, 2, -8], [3, 3, 0], [4, 4, 100]])
        heights = compute_height_map(plane, vertices)
        assert np.all(heights >= 0)


class TestHeightMapToColors:
    """Tests para el gradiente de color del mapa de calor"""

    def test_output_shape_and_range(self):
        heights = np.array([0, 5, 10, 15, 20], dtype=np.float64)
        colors = height_map_to_colors(heights)
        assert colors.shape == (5, 3)
        assert colors.dtype == np.uint8
        assert np.all(colors >= 0) and np.all(colors <= 255)

    def test_zero_height_maps_to_blue_end(self):
        heights = np.array([0, 10, 20], dtype=np.float64)
        colors = height_map_to_colors(heights)
        # El punto de altura 0 debe tener mas azul que rojo
        assert colors[0, 2] > colors[0, 0]

    def test_max_height_maps_to_red_end(self):
        heights = np.array([0, 10, 20], dtype=np.float64)
        colors = height_map_to_colors(heights)
        # El punto de altura maxima debe tener mas rojo que azul
        assert colors[-1, 0] > colors[-1, 2]

    def test_uniform_heights_dont_crash(self):
        heights = np.zeros(5)
        colors = height_map_to_colors(heights)
        assert colors.shape == (5, 3)

    def test_empty_array(self):
        colors = height_map_to_colors(np.array([]))
        assert colors.shape == (0, 3)


class TestIntersectRayPlane:
    def test_ray_hits_horizontal_plane(self):
        point = intersect_ray_plane([0, 0, 10], [0, 0, -1], [0, 0, 0], [0, 0, 1])
        assert np.allclose(point, [0, 0, 0])

    def test_oblique_ray(self):
        point = intersect_ray_plane([0, 0, 10], [1, 0, -1], [0, 0, 0], [0, 0, 1])
        assert np.allclose(point, [10, 0, 0])

    def test_parallel_ray_returns_none(self):
        assert intersect_ray_plane([0, 0, 10], [1, 0, 0], [0, 0, 0], [0, 0, 1]) is None

    def test_plane_behind_ray_returns_none(self):
        assert intersect_ray_plane([0, 0, 10], [0, 0, 1], [0, 0, 0], [0, 0, 1]) is None

    def test_result_lies_on_tilted_plane(self):
        plane = compute_support_plane(
            np.array([0.0, 0.0, 0.0]), np.array([10.0, 0.0, 5.0]), np.array([0.0, 10.0, 0.0])
        )
        point = intersect_ray_plane([3, 4, 50], [0, 0, -1], plane.point1, plane.normal)
        assert abs(plane.distance_to_point(point)) < 1e-9


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
