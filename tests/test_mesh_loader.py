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


class TestMeshLoaderOBJTexture:
    """Tests para la carga de textura (UV + .mtl + imagen) de archivos OBJ"""

    @staticmethod
    def _write_square_obj(tmp_path, mtllib_line="mtllib test.mtl\n"):
        """Cuadrado de 2 triángulos con UV, comparte (v, vt) en 2 esquinas"""
        obj_path = tmp_path / "square.obj"
        obj_path.write_text(
            mtllib_line +
            "v 0 0 0\n"
            "v 1 0 0\n"
            "v 1 1 0\n"
            "v 0 1 0\n"
            "vt 0 0\n"
            "vt 1 0\n"
            "vt 1 1\n"
            "vt 0 1\n"
            "f 1/1 2/2 3/3\n"
            "f 1/1 3/3 4/4\n"
        )
        return obj_path

    @staticmethod
    def _write_mtl(tmp_path, image_name="test.png", filename="test.mtl"):
        mtl_path = tmp_path / filename
        mtl_path.write_text(f"newmtl material0\nmap_Kd {image_name}\n")
        return mtl_path

    @staticmethod
    def _write_png(tmp_path, name="test.png"):
        from PIL import Image
        img = Image.new('RGB', (4, 4), color=(200, 100, 50))
        img_path = tmp_path / name
        img.save(img_path)
        return img_path

    def test_obj_without_vt_has_no_texture(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            obj_path = tmp_path / "plain.obj"
            obj_path.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n")

            model = MeshLoader().load(str(obj_path))
            assert model.texture is None

    def test_obj_with_full_texture_loads_correctly(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            obj_path = self._write_square_obj(tmp_path)
            self._write_mtl(tmp_path)
            self._write_png(tmp_path)

            model = MeshLoader().load(str(obj_path))

            assert model.texture is not None
            assert model.num_vertices == 4
            assert model.num_triangles == 2
            # 6 "corners" entre las 2 caras, pero 2 pares (v, vt) se repiten
            # exactamente -> se deduplican a 4 vertices de textura
            assert len(model.texture.vertices) == 4
            assert len(model.texture.faces) == 2
            assert model.texture.uvs.shape == (4, 2)
            assert Path(model.texture.image_path).exists()
            assert Path(model.texture.image_path).name == "test.png"

    def test_obj_missing_mtl_has_no_texture_but_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            obj_path = self._write_square_obj(tmp_path, mtllib_line="mtllib no_existe.mtl\n")
            # No se escribe el .mtl a propósito

            model = MeshLoader().load(str(obj_path))

            assert model.texture is None
            assert model.num_vertices == 4  # la geometria igual carga bien

    def test_obj_missing_image_has_no_texture_but_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            obj_path = self._write_square_obj(tmp_path)
            self._write_mtl(tmp_path, image_name="no_existe.png")
            # No se escribe la imagen a propósito

            model = MeshLoader().load(str(obj_path))

            assert model.texture is None
            assert model.num_vertices == 4

    def test_obj_mtl_without_map_kd_has_no_texture(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            obj_path = self._write_square_obj(tmp_path)
            mtl_path = tmp_path / "test.mtl"
            mtl_path.write_text("newmtl material0\nKd 1.0 1.0 1.0\n")  # sin map_Kd

            model = MeshLoader().load(str(obj_path))

            assert model.texture is None

    def test_obj_without_mtllib_has_no_texture(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            obj_path = tmp_path / "square.obj"
            obj_path.write_text(
                "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\n"
                "vt 0 0\nvt 1 0\nvt 1 1\nvt 0 1\n"
                "f 1/1 2/2 3/3\nf 1/1 3/3 4/4\n"
            )
            self._write_png(tmp_path)

            model = MeshLoader().load(str(obj_path))

            assert model.texture is None

    def test_obj_partial_vt_coverage_has_no_texture(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            obj_path = tmp_path / "mixed.obj"
            obj_path.write_text(
                "mtllib test.mtl\n"
                "v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\n"
                "vt 0 0\nvt 1 0\nvt 1 1\n"
                "f 1/1 2/2 3/3\n"
                "f 1 3 4\n"  # esta cara no trae vt
            )
            self._write_mtl(tmp_path)
            self._write_png(tmp_path)

            model = MeshLoader().load(str(obj_path))

            assert model.texture is None
            assert model.num_triangles == 2  # la geometria igual carga bien


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
