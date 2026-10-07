"""Tests de project_io: guardar y cargar el estado de una sesión"""
import pytest
import os
import tempfile
import numpy as np
from src.core.project_io import (
    save_project, load_project, get_autosave_path, read_project_vertex_count, load_landmarks,
)
from src.models.foot_model import Measurement


class TestSaveLoadProject:
    def test_round_trip_with_plane_and_measurements(self):
        plane_points = [np.array([0, 0, 0]), np.array([10, 0, 0]), np.array([0, 10, 0])]
        measurements = [
            Measurement(
                name="Altura arco 1", measurement_type="altura_arco", value=15.5, unit="mm",
                point1=np.array([1, 1, 15.5]), point2=np.array([1, 1, 0]),
            ),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "proyecto.json")
            save_project(filepath, r"C:\ruta\pie.stl", plane_points, measurements)

            mesh_filepath, plane, loaded_measurements = load_project(filepath)

            assert mesh_filepath == r"C:\ruta\pie.stl"
            assert plane is not None
            assert np.allclose(np.abs(plane.normal), [0, 0, 1])
            assert len(loaded_measurements) == 1
            assert loaded_measurements[0].name == "Altura arco 1"
            assert abs(loaded_measurements[0].value - 15.5) < 1e-9
            assert np.allclose(loaded_measurements[0].point1, [1, 1, 15.5])

    def test_round_trip_without_plane(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "proyecto.json")
            save_project(filepath, "pie.obj", None, [])
            mesh_filepath, plane, measurements = load_project(filepath)
            assert mesh_filepath == "pie.obj"
            assert plane is None
            assert measurements == []

    def test_multiple_measurements_preserve_order(self):
        measurements = [
            Measurement(name="Altura arco 1", measurement_type="altura_arco", value=10.0, unit="mm"),
            Measurement(name="Altura arco 2", measurement_type="altura_arco", value=20.0, unit="mm"),
            Measurement(name="Distancia plano 1", measurement_type="distancia_plano", value=30.0, unit="mm"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "proyecto.json")
            save_project(filepath, "pie.stl", None, measurements)
            _, _, loaded = load_project(filepath)
            assert [m.name for m in loaded] == [m.name for m in measurements]
            assert [m.value for m in loaded] == [m.value for m in measurements]

    def test_invalid_file_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "invalido.json")
            with open(filepath, 'w') as f:
                f.write('{"otra_cosa": 1}')
            with pytest.raises(ValueError):
                load_project(filepath)


class TestAutosaveHelpers:
    def test_autosave_path_is_next_to_mesh_with_full_name(self):
        path = get_autosave_path(os.path.join("carpeta", "pie.obj"))
        assert path == os.path.join("carpeta", "pie.obj.pieviewer.json")

    def test_stl_and_obj_with_same_stem_do_not_collide(self):
        assert get_autosave_path("pie.stl") != get_autosave_path("pie.obj")

    def test_vertex_count_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "p.json")
            save_project(filepath, "pie.obj", None, [], mesh_num_vertices=28014)
            assert read_project_vertex_count(filepath) == 28014
            _, plane, measurements = load_project(filepath)
            assert plane is None and measurements == []

    def test_vertex_count_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "p.json")
            save_project(filepath, "pie.obj", None, [])
            assert read_project_vertex_count(filepath) is None


class TestLandmarks:
    def test_round_trip(self):
        landmarks = {
            "metatarsal_1": np.array([10.0, 20.0, 30.0]),
            "metatarsal_5": np.array([40.0, 50.0, 60.0]),
            "heel_distal": np.array([1.5, 2.5, 3.5]),
        }
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "p.json")
            save_project(filepath, "pie.obj", None, [], landmarks=landmarks)
            loaded = load_landmarks(filepath)
            assert set(loaded) == set(landmarks)
            for key in landmarks:
                assert np.allclose(loaded[key], landmarks[key])

    def test_partial_landmarks(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "p.json")
            save_project(filepath, "pie.obj", None, [], landmarks={"heel_distal": np.array([1.0, 2.0, 3.0])})
            assert list(load_landmarks(filepath)) == ["heel_distal"]

    def test_project_without_landmarks_loads_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "p.json")
            save_project(filepath, "pie.obj", None, [])
            assert load_landmarks(filepath) == {}

    def test_old_project_file_without_landmarks_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "viejo.json")
            with open(filepath, 'w') as f:
                f.write('{"mesh_filepath": "pie.stl", "plane_points": null, "measurements": []}')
            assert load_landmarks(filepath) == {}
            assert load_project(filepath)[0] == "pie.stl"


class TestLandmarks:
    def test_round_trip(self):
        landmarks = {
            "metatarsal_1": np.array([10.0, 20.0, 30.0]),
            "metatarsal_5": np.array([40.0, 50.0, 60.0]),
            "heel_distal": np.array([1.5, 2.5, 3.5]),
        }
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "p.json")
            save_project(filepath, "pie.obj", None, [], landmarks=landmarks)
            loaded = load_landmarks(filepath)
            assert set(loaded) == set(landmarks)
            for key in landmarks:
                assert np.allclose(loaded[key], landmarks[key])

    def test_partial_landmarks(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "p.json")
            save_project(filepath, "pie.obj", None, [], landmarks={"heel_distal": np.array([1.0, 2.0, 3.0])})
            assert list(load_landmarks(filepath)) == ["heel_distal"]

    def test_project_without_landmarks_loads_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "p.json")
            save_project(filepath, "pie.obj", None, [])
            assert load_landmarks(filepath) == {}

    def test_old_project_file_without_landmarks_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "viejo.json")
            with open(filepath, 'w') as f:
                f.write('{"mesh_filepath": "pie.stl", "plane_points": null, "measurements": []}')
            assert load_landmarks(filepath) == {}
            assert load_project(filepath)[0] == "pie.stl"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
