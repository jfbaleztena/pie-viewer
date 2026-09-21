"""Tests de MeshLoader"""
import pytest
import numpy as np
from pathlib import Path
import tempfile
from src.core.mesh_loader import MeshLoader, STLParseError, OBJParseError, GeometryValidationError
from src.models.foot_model import FootModel


class TestMeshLoaderASCII:
    """Tests para carga ASCII"""

    def test_simple_triangle(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 0 1 0
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model.num_vertices == 3
            assert model.num_triangles == 1
        finally:
            Path(filepath).unlink()

    def test_multiple_triangles(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 0 1 0
  endloop
endfacet
facet normal 0 0 1
  outer loop
    vertex 1 0 0
    vertex 1 1 0
    vertex 0 1 0
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model.num_triangles == 2
        finally:
            Path(filepath).unlink()

    def test_vertex_deduplication(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 0 1 0
  endloop
endfacet
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 1 1 0
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model.num_vertices <= 4
        finally:
            Path(filepath).unlink()

    def test_invalid_format(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("invalid content")
            filepath = f.name
        try:
            loader = MeshLoader()
            with pytest.raises(STLParseError):
                loader.load(filepath)
        finally:
            Path(filepath).unlink()


class TestMeshLoaderValidation:
    """Tests para validación"""

    def test_bounds_calculation(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 10 5 20
    vertex 5 10 15
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            x_min, x_max, y_min, y_max, z_min, z_max = model.bounds
            assert x_min == 0
            assert x_max == 10
        finally:
            Path(filepath).unlink()

    def test_center_calculation(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 10 0 0
    vertex 0 10 0
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model.center is not None
        finally:
            Path(filepath).unlink()

    def test_no_vertices(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("solid test\nendsolid test")
            filepath = f.name
        try:
            loader = MeshLoader()
            with pytest.raises(STLParseError):
                loader.load(filepath)
        finally:
            Path(filepath).unlink()

    def test_geometry_validation(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 0 1 0
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model.is_valid
        finally:
            Path(filepath).unlink()


class TestMeshLoaderScaling:
    """Tests para escala"""

    def test_scale_detection(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 200 0 0
    vertex 0 200 0
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert len(model.validation_warnings) > 0
        finally:
            Path(filepath).unlink()

    def test_normalize_scale(self):
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
            loader.normalize_scale(model, target_dimension=50)
            max_dim = max(model.bounds[1] - model.bounds[0], model.bounds[3] - model.bounds[2])
            assert abs(max_dim - 50) < 1e-6
        finally:
            Path(filepath).unlink()


class TestMeshLoaderFormat:
    """Tests para detección de formato"""

    def test_ascii_detection(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 0 1 0
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            is_ascii = loader._is_ascii_stl(Path(filepath))
            assert is_ascii
        finally:
            Path(filepath).unlink()

    def test_file_not_found(self):
        loader = MeshLoader()
        with pytest.raises(FileNotFoundError):
            loader.load('/nonexistent/file.stl')


class TestMeshLoaderOBJ:
    """Tests para carga de archivos OBJ (Wavefront)"""

    def test_simple_triangle(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obj', delete=False) as f:
            f.write("""v 0 0 0
v 1 0 0
v 0 1 0
f 1 2 3
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model.num_vertices == 3
            assert model.num_triangles == 1
        finally:
            Path(filepath).unlink()

    def test_vertices_shared_across_faces(self):
        # A diferencia de STL, OBJ referencia vértices compartidos por índice:
        # 4 vértices y 2 caras deben dar exactamente 4 vértices (sin deduplicar)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obj', delete=False) as f:
            f.write("""v 0 0 0
v 10 0 0
v 10 10 0
v 0 10 0
f 1 2 3
f 1 3 4
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model.num_vertices == 4
            assert model.num_triangles == 2
        finally:
            Path(filepath).unlink()

    def test_ignores_normals_and_texture_coords(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obj', delete=False) as f:
            f.write("""# comentario
v 0 0 0
v 1 0 0
v 0 1 0
vn 0 0 1
vn 0 0 1
vn 0 0 1
vt 0 0
f 1 2 3
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model.num_vertices == 3
            assert model.num_triangles == 1
        finally:
            Path(filepath).unlink()

    def test_face_with_vertex_normal_index(self):
        # Formato "v//vn" (índice de vértice y normal, sin textura)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obj', delete=False) as f:
            f.write("""v 0 0 0
v 1 0 0
v 0 1 0
vn 0 0 1
f 1//1 2//1 3//1
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model.num_triangles == 1
        finally:
            Path(filepath).unlink()

    def test_quad_face_is_triangulated(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obj', delete=False) as f:
            f.write("""v 0 0 0
v 10 0 0
v 10 10 0
v 0 10 0
f 1 2 3 4
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert model.num_triangles == 2
        finally:
            Path(filepath).unlink()

    def test_bounds_calculation(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obj', delete=False) as f:
            f.write("""v 0 0 0
v 10 5 20
v 5 10 15
f 1 2 3
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            x_min, x_max, y_min, y_max, z_min, z_max = model.bounds
            assert x_min == 0
            assert x_max == 10
            assert z_max == 20
        finally:
            Path(filepath).unlink()

    def test_no_faces_raises_error(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obj', delete=False) as f:
            f.write("v 0 0 0\nv 1 0 0\nv 0 1 0\n")
            filepath = f.name
        try:
            loader = MeshLoader()
            with pytest.raises(OBJParseError):
                loader.load(filepath)
        finally:
            Path(filepath).unlink()

    def test_invalid_vertex_raises_error(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.obj', delete=False) as f:
            f.write("v 0 0\nf 1 2 3\n")
            filepath = f.name
        try:
            loader = MeshLoader()
            with pytest.raises(OBJParseError):
                loader.load(filepath)
        finally:
            Path(filepath).unlink()


class TestMeshLoaderIntegration:
    """Tests de integración"""

    def test_complete_workflow(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.stl', delete=False) as f:
            f.write("""solid test
facet normal 0 0 1
  outer loop
    vertex 0 0 0
    vertex 1 0 0
    vertex 0 1 0
  endloop
endfacet
endsolid test
""")
            filepath = f.name
        try:
            loader = MeshLoader()
            model = loader.load(filepath)
            assert isinstance(model, FootModel)
            assert model.is_valid
            assert model.num_vertices > 0
            assert model.num_triangles > 0
            assert model.bounds is not None
            assert model.center is not None
        finally:
            Path(filepath).unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
