"""Tests de project_io: guardar y cargar el estado de una sesión"""
import pytest
import os
import tempfile
import numpy as np
from src.core.project_io import save_project, load_project
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
