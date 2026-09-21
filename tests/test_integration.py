"""Tests de integración"""
import pytest
import numpy as np
from pathlib import Path
import tempfile
from src.core.mesh_loader import MeshLoader, STLParseError
from src.models.foot_model import FootModel


class TestIntegrationWorkflow:
    """Tests de integración del flujo completo"""

    def test_complete_load_workflow(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 10 0 0
    vertex 0 10 0
  endloop
endfacet
facet normal 0 0 1
  outer loop
    vertex 10 0 0
    vertex 10 10 0
    vertex 0 10 0
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model is not None
            assert isinstance(model, FootModel)
            assert model.num_vertices == 4
            assert model.num_triangles == 2
            assert model.is_valid
        finally:
            Path(filepath).unlink()

    def test_scale_workflow(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 100 0 0
    vertex 0 100 0
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            loader.normalize_scale(model, target_dimension=50.0)
            max_dim = max(model.bounds[1] - model.bounds[0], model.bounds[3] - model.bounds[2])
            assert abs(max_dim - 50) < 1e-6
        finally:
            Path(filepath).unlink()

    def test_center_workflow(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 10 10 10
    vertex 20 10 10
    vertex 10 20 10
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            loader.center_at_origin(model)
            assert np.linalg.norm(model.center) < 1e-6
        finally:
            Path(filepath).unlink()

    def test_multiple_files(self):
        files = []
        try:
            loader = MeshLoader()
            for i in range(2):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
                    scale = (i + 1) * 10
                    f.write(f"""solid test{i}
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex {scale} 0 0
    vertex 0 {scale} 0
  endloop
endfacet
endsolid test{i}
""")
                    filepath = f.name
                    files.append(filepath)
            models = []
            for filepath in files:
                model = loader.load(filepath)
                models.append(model)
                assert model is not None
        finally:
            for filepath in files:
                if Path(filepath).exists():
                    Path(filepath).unlink()

    def test_error_handling(self):
        with tempfile.NamedTemporaryFile(suffix='.stl', delete=False) as f:
            f.write(b'Invalid STL content')
            filepath = f.name
        try:
            loader = MeshLoader()
            with pytest.raises(STLParseError):
                loader.load(filepath)
        finally:
            Path(filepath).unlink()


class TestModelStructure:
    """Tests de la estructura del modelo"""

    def test_model_creation(self):
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float64)
        faces = np.array([[0, 1, 2]], dtype=np.uint32)
        model = FootModel(vertices=vertices, faces=faces)
        assert model.num_vertices == 3
        assert model.num_triangles == 1

    def test_model_bounds(self):
        vertices = np.array([[0, 0, 0], [10, 5, 20], [5, 10, 15]], dtype=np.float64)
        faces = np.array([[0, 1, 2]], dtype=np.uint32)
        model = FootModel(vertices=vertices, faces=faces)
        model.compute_bounds()
        x_min, x_max, y_min, y_max, z_min, z_max = model.bounds
        assert x_min == 0
        assert x_max == 10
        assert y_min == 0
        assert y_max == 10
        assert z_min == 0
        assert z_max == 20

    def test_model_center(self):
        vertices = np.array([[0, 0, 0], [10, 10, 10]], dtype=np.float64)
        faces = np.array([[0, 1, 0]], dtype=np.uint32)
        model = FootModel(vertices=vertices, faces=faces)
        model.compute_center()
        expected = np.array([5, 5, 5])
        assert np.allclose(model.center, expected)

    def test_model_center_at_origin(self):
        vertices = np.array([[10, 10, 10], [20, 20, 20]], dtype=np.float64)
        faces = np.array([[0, 1, 0]], dtype=np.uint32)
        model = FootModel(vertices=vertices, faces=faces)
        model.center_at_origin()
        assert np.linalg.norm(model.center) < 1e-10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
