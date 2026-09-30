"""
MeshLoader - Módulo para cargar y validar archivos STL y OBJ

Responsabilidad:
- Leer archivos STL (formato binario y ASCII)
- Leer archivos OBJ (Wavefront, formato texto)
- Validar geometría (triángulos degenerados, normales)
- Normalizar escala (detectar mm, cm, m)
- Retornar FootModel con vértices y caras
"""

import struct
import numpy as np
from pathlib import Path
from typing import Tuple, Optional, List
import logging

from src.models.foot_model import FootModel, TextureData
from src.utils.constants import MAX_TRIANGLES, WARNING_TRIANGLES, GEOMETRY_TOLERANCE

logger = logging.getLogger(__name__)


class MeshLoaderError(Exception):
    """Excepción base para errores de carga de malla"""
    pass


class STLParseError(MeshLoaderError):
    """Error al parsear archivo STL"""
    pass


class OBJParseError(MeshLoaderError):
    """Error al parsear archivo OBJ"""
    pass


class GeometryValidationError(MeshLoaderError):
    """Error en validación de geometría"""
    pass


class MeshLoader:
    """
    Cargador de archivos STL con validación y normalización
    """

    # Constantes
    STL_HEADER_SIZE = 80  # Bytes
    STL_TRIANGLE_SIZE = 50  # Bytes (12 bytes normal + 9*4 bytes vértices + 2 bytes atributo)
    STL_ASCII_FACET = "facet normal"
    STL_ASCII_OUTER = "outer loop"
    STL_ASCII_VERTEX = "vertex"
    STL_ASCII_END_FACET = "endfacet"

    def __init__(self):
        """Inicializar el loader"""
        self.logger = logging.getLogger(__name__)
        self.validation_warnings: List[str] = []

    def load(self, filepath: str) -> FootModel:
        """
        Cargar archivo STL y retornar FootModel

        Args:
            filepath: Ruta al archivo STL

        Returns:
            FootModel con vértices y caras cargados

        Raises:
            FileNotFoundError: Si archivo no existe
            STLParseError: Si hay error al parsear
            GeometryValidationError: Si geometría es inválida
        """
        filepath_obj = Path(filepath)

        # Verificar que archivo existe
        if not filepath_obj.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {filepath}")

        self.logger.info(f"Cargando STL: {filepath}")
        self.validation_warnings = []

        try:
            # Detectar formato por extensión: OBJ vs STL (ASCII o Binario)
            texture = None
            if filepath_obj.suffix.lower() == '.obj':
                self.logger.debug("Detectado formato OBJ")
                vertices, faces, texture = self._load_obj(filepath_obj)
            elif self._is_ascii_stl(filepath_obj):
                self.logger.debug("Detectado formato STL ASCII")
                vertices, faces = self._load_ascii(filepath_obj)
            else:
                self.logger.debug("Detectado formato STL Binario")
                vertices, faces = self._load_binary(filepath_obj)

            # Validar geometría
            self._validate_geometry(vertices, faces)

            # Crear FootModel
            model = FootModel(
                vertices=vertices,
                faces=faces,
                filepath=str(filepath),
                filename=filepath_obj.name,
                texture=texture,
            )

            # Calcular propiedades
            model.compute_bounds()
            model.compute_center()

            # Detectar y sugerir escala
            self._detect_and_suggest_scale(model)

            # Advertir si malla es grande
            if model.num_triangles > WARNING_TRIANGLES:
                warning = f"Malla grande: {model.num_triangles:,} triángulos (>500k puede ser lento)"
                self.validation_warnings.append(warning)
                self.logger.warning(warning)

            model.validation_warnings = self.validation_warnings
            model.is_valid = True

            self.logger.info(
                f"STL cargado exitosamente: {model.num_vertices} vértices, "
                f"{model.num_triangles} triángulos"
            )
            if model.texture is not None:
                self.logger.info(f"Textura cargada: {model.texture.image_path}")

            return model

        except (STLParseError, OBJParseError, GeometryValidationError):
            raise
        except Exception as e:
            raise STLParseError(f"Error al cargar malla: {str(e)}") from e

    def _is_ascii_stl(self, filepath: Path) -> bool:
        """
        Detectar si archivo STL es ASCII o Binario

        Args:
            filepath: Ruta del archivo

        Returns:
            True si es ASCII, False si es binario
        """
        try:
            with open(filepath, 'rb') as f:
                # Leer primeros bytes
                header = f.read(5).lower()

                # STL ASCII comienza con "solid"
                if header.startswith(b'solid'):
                    # Verificar que sea texto válido
                    f.seek(0)
                    text = f.read(100).decode('ascii', errors='ignore')
                    return 'facet normal' in text.lower()

            return False
        except Exception:
            return False

    def _load_ascii(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """
        Parsear archivo STL ASCII

        Formato:
            solid name
              facet normal n_x n_y n_z
                outer loop
                  vertex v_x v_y v_z
                  vertex v_x v_y v_z
                  vertex v_x v_y v_z
                endloop
              endfacet
            endsolid name

        Args:
            filepath: Ruta del archivo

        Returns:
            Tupla (vertices, faces) como numpy arrays

        Raises:
            STLParseError: Si hay error al parsear
        """
        vertices_list = []
        faces_list = []
        vertex_dict = {}  # Para deduplicación
        current_face_vertices = []

        try:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    if not line or line.startswith('solid') or line.startswith('endsolid'):
                        continue

                    if line.startswith(self.STL_ASCII_VERTEX):
                        # Parsear vertex: "vertex x y z"
                        parts = line.split()
                        if len(parts) != 4:
                            raise STLParseError(f"Formato inválido en línea {line_num}: {line}")

                        try:
                            v = tuple(float(parts[i]) for i in range(1, 4))
                        except ValueError as e:
                            raise STLParseError(f"Coordenadas inválidas en línea {line_num}: {e}")

                        # Deduplicar vértices (con tolerancia)
                        v_idx = self._find_or_add_vertex(v, vertices_list, vertex_dict)
                        current_face_vertices.append(v_idx)

                    elif line.startswith(self.STL_ASCII_END_FACET):
                        # Fin de faceta: agregar cara
                        if len(current_face_vertices) == 3:
                            faces_list.append(tuple(current_face_vertices))
                        elif len(current_face_vertices) > 0:
                            self.logger.warning(
                                f"Faceta con {len(current_face_vertices)} vértices (esperado 3)"
                            )
                        current_face_vertices = []

            if len(vertices_list) == 0:
                raise STLParseError("No se encontraron vértices en archivo ASCII")

            vertices = np.array(vertices_list, dtype=np.float64)
            faces = np.array(faces_list, dtype=np.uint32)

            return vertices, faces

        except STLParseError:
            raise
        except Exception as e:
            raise STLParseError(f"Error parseando ASCII STL: {e}") from e

    def _load_binary(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray]:
        """
        Parsear archivo STL Binario

        Formato:
            80 bytes: header
            4 bytes:  número de triángulos
            Para cada triángulo:
              12 bytes: normal (3 floats)
              36 bytes: 3 vértices (9 floats)
              2 bytes:  attribute count

        Args:
            filepath: Ruta del archivo

        Returns:
            Tupla (vertices, faces) como numpy arrays

        Raises:
            STLParseError: Si hay error al parsear
        """
        vertices_list = []
        faces_list = []
        vertex_dict = {}

        try:
            with open(filepath, 'rb') as f:
                # Leer header
                header = f.read(self.STL_HEADER_SIZE)
                if len(header) < self.STL_HEADER_SIZE:
                    raise STLParseError(f"Header truncado ({len(header)} bytes)")

                # Leer número de triángulos
                num_triangles_bytes = f.read(4)
                if len(num_triangles_bytes) != 4:
                    raise STLParseError("Número de triángulos truncado")

                num_triangles = struct.unpack('<I', num_triangles_bytes)[0]

                # Verificar límite
                if num_triangles > MAX_TRIANGLES:
                    raise GeometryValidationError(
                        f"Demasiados triángulos: {num_triangles:,} (máximo: {MAX_TRIANGLES:,})"
                    )

                # Leer triángulos
                for tri_idx in range(num_triangles):
                    # Leer normal (3 floats)
                    normal_bytes = f.read(12)
                    if len(normal_bytes) != 12:
                        raise STLParseError(f"Normal truncada en triángulo {tri_idx}")

                    # Leer 3 vértices (9 floats)
                    vertices_bytes = f.read(36)
                    if len(vertices_bytes) != 36:
                        raise STLParseError(f"Vértices truncados en triángulo {tri_idx}")

                    # Parsear vértices
                    v_indices = []
                    for v_idx in range(3):
                        v_bytes = vertices_bytes[v_idx * 12:(v_idx + 1) * 12]
                        v_float = struct.unpack('<fff', v_bytes)
                        v_tuple = tuple(float(x) for x in v_float)

                        # Deduplicar
                        v_id = self._find_or_add_vertex(v_tuple, vertices_list, vertex_dict)
                        v_indices.append(v_id)

                    faces_list.append(tuple(v_indices))

                    # Leer atributo (2 bytes, ignorar)
                    _ = f.read(2)

            if len(vertices_list) == 0:
                raise STLParseError("No se encontraron vértices en archivo binario")

            vertices = np.array(vertices_list, dtype=np.float64)
            faces = np.array(faces_list, dtype=np.uint32)

            return vertices, faces

        except (STLParseError, GeometryValidationError):
            raise
        except struct.error as e:
            raise STLParseError(f"Error de formato binario: {e}") from e
        except Exception as e:
            raise STLParseError(f"Error parseando binario STL: {e}") from e

    def _load_obj(self, filepath: Path) -> Tuple[np.ndarray, np.ndarray, Optional[TextureData]]:
        """
        Parsear archivo OBJ (Wavefront)

        Soporta:
            v x y z        -> vértice
            vn nx ny nz    -> normal (ignorada, VTK las recalcula al renderizar)
            vt u v         -> coordenada de textura
            mtllib archivo -> referencia al .mtl (para encontrar la imagen de textura)
            f a b c ...    -> cara (índices 1-based, o negativos relativos);
                              acepta 'a', 'a/vt', 'a/vt/vn' o 'a//vn' por vértice;
                              caras con más de 3 vértices se triangulan en abanico

        A diferencia de STL, OBJ ya referencia vértices compartidos por índice,
        así que no hace falta deduplicar como en `_load_ascii`/`_load_binary`.

        Si el archivo trae coordenadas de textura (`vt`) en todas las caras y
        un `mtllib` que resuelve a una imagen existente, se arma además una
        `TextureData` con una malla de render separada: las UV están
        indexadas aparte de las posiciones (un mismo vértice de posición
        puede necesitar varias UV distintas en las costuras del "unwrap" de
        textura), así que esa malla puede tener más vértices que la de
        posiciones puras — nunca se usa para mediciones, solo para mostrar
        la textura.

        Args:
            filepath: Ruta del archivo

        Returns:
            Tupla (vertices, faces, texture): `texture` es None si el
            archivo no trae textura o si falta el .mtl/la imagen referenciada
            (la textura es opcional: su ausencia no impide cargar ni medir)

        Raises:
            OBJParseError: Si hay error al parsear la geometría
        """
        vertices_list: List[Tuple[float, float, float]] = []
        faces_list: List[Tuple[int, int, int]] = []
        texcoords_list: List[Tuple[float, float]] = []
        mtllib_name: Optional[str] = None

        # Malla de render con textura: se arma en paralelo a la de
        # posiciones, deduplicando por el par (v_idx, vt_idx) de cada
        # "corner" de cada cara — no alcanza con deduplicar solo por v_idx.
        tex_vertex_dict: dict = {}
        tex_vertices_list: List[Tuple[float, float, float]] = []
        tex_uvs_list: List[Tuple[float, float]] = []
        tex_faces_list: List[Tuple[int, int, int]] = []
        all_faces_have_vt = True

        try:
            with open(filepath, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()

                    if not line or line.startswith('#'):
                        continue

                    parts = line.split()
                    tag = parts[0]

                    if tag == 'v':
                        if len(parts) < 4:
                            raise OBJParseError(f"Vértice inválido en línea {line_num}: {line}")
                        try:
                            vertices_list.append(tuple(float(p) for p in parts[1:4]))
                        except ValueError as e:
                            raise OBJParseError(f"Coordenadas inválidas en línea {line_num}: {e}")

                    elif tag == 'vt':
                        if len(parts) < 3:
                            raise OBJParseError(f"Coordenada de textura inválida en línea {line_num}: {line}")
                        try:
                            texcoords_list.append((float(parts[1]), float(parts[2])))
                        except ValueError as e:
                            raise OBJParseError(f"Coordenada de textura inválida en línea {line_num}: {e}")

                    elif tag == 'mtllib':
                        mtllib_name = line[len('mtllib'):].strip()

                    elif tag == 'f':
                        if len(parts) < 4:
                            raise OBJParseError(f"Cara inválida en línea {line_num}: {line}")
                        try:
                            tokens = [
                                self._parse_obj_face_token(p, len(vertices_list), len(texcoords_list))
                                for p in parts[1:]
                            ]
                        except ValueError as e:
                            raise OBJParseError(f"Índice de cara inválido en línea {line_num}: {e}")

                        indices = [v_idx for v_idx, _vt_idx in tokens]
                        # Triangulación en abanico para caras con más de 3 vértices
                        for i in range(1, len(indices) - 1):
                            faces_list.append((indices[0], indices[i], indices[i + 1]))

                        # Misma triangulación para la malla de textura, si
                        # todas las caras vistas hasta ahora traen vt.
                        if all_faces_have_vt:
                            if any(vt_idx is None for _v_idx, vt_idx in tokens):
                                all_faces_have_vt = False
                            else:
                                tex_indices = []
                                for v_idx, vt_idx in tokens:
                                    key = (v_idx, vt_idx)
                                    tex_idx = tex_vertex_dict.get(key)
                                    if tex_idx is None:
                                        tex_idx = len(tex_vertices_list)
                                        tex_vertex_dict[key] = tex_idx
                                        tex_vertices_list.append(vertices_list[v_idx])
                                        tex_uvs_list.append(texcoords_list[vt_idx])
                                    tex_indices.append(tex_idx)
                                for i in range(1, len(tex_indices) - 1):
                                    tex_faces_list.append(
                                        (tex_indices[0], tex_indices[i], tex_indices[i + 1])
                                    )

                    # 'vn', 'o', 'g', 's', 'usemtl', etc. se ignoran

            if len(vertices_list) == 0:
                raise OBJParseError("No se encontraron vértices en archivo OBJ")
            if len(faces_list) == 0:
                raise OBJParseError("No se encontraron caras en archivo OBJ")

            vertices = np.array(vertices_list, dtype=np.float64)
            faces = np.array(faces_list, dtype=np.uint32)

            texture = None
            if all_faces_have_vt and texcoords_list and mtllib_name:
                texture = self._resolve_obj_texture(
                    filepath, mtllib_name, tex_vertices_list, tex_uvs_list, tex_faces_list
                )

            return vertices, faces, texture

        except OBJParseError:
            raise
        except Exception as e:
            raise OBJParseError(f"Error parseando OBJ: {e}") from e

    def _resolve_obj_texture(
        self,
        obj_filepath: Path,
        mtllib_name: str,
        tex_vertices_list: List[Tuple[float, float, float]],
        tex_uvs_list: List[Tuple[float, float]],
        tex_faces_list: List[Tuple[int, int, int]],
    ) -> Optional[TextureData]:
        """
        Leer el .mtl referenciado por el OBJ para encontrar la imagen de
        textura (`map_Kd`) y armar el `TextureData`. Cualquier problema acá
        (falta el .mtl, no tiene map_Kd, falta la imagen) se resuelve
        devolviendo None con un warning en el log — la textura es opcional,
        nunca debe impedir cargar o medir la malla.
        """
        mtl_path = obj_filepath.parent / mtllib_name
        if not mtl_path.exists():
            self.logger.warning(f"No se encontró el archivo .mtl referenciado: {mtl_path}")
            return None

        image_name = None
        try:
            with open(mtl_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('map_Kd'):
                        image_name = line[len('map_Kd'):].strip()
                        break
        except OSError as e:
            self.logger.warning(f"No se pudo leer el archivo .mtl {mtl_path}: {e}")
            return None

        if image_name is None:
            self.logger.warning(f"El archivo .mtl no tiene 'map_Kd': {mtl_path}")
            return None

        image_path = obj_filepath.parent / image_name
        if not image_path.exists():
            self.logger.warning(f"No se encontró la imagen de textura: {image_path}")
            return None

        return TextureData(
            vertices=np.array(tex_vertices_list, dtype=np.float64),
            uvs=np.array(tex_uvs_list, dtype=np.float64),
            faces=np.array(tex_faces_list, dtype=np.uint32),
            image_path=str(image_path),
        )

    @staticmethod
    def _parse_obj_face_token(token: str, num_vertices: int, num_texcoords: int):
        """
        Parsear un token de cara OBJ ('12', '12/5', '12//3', '12/5/3').

        Args:
            token: Token individual de la línea 'f'
            num_vertices: Cantidad de vértices leídos hasta el momento
            num_texcoords: Cantidad de coordenadas de textura leídas hasta el momento

        Returns:
            Tupla (índice de vértice 0-based, índice de UV 0-based o None
            si el token no incluye coordenada de textura)

        Raises:
            ValueError: Si algún índice es 0 o no numérico
        """
        parts = token.split('/')
        v_idx = MeshLoader._parse_obj_index(parts[0], num_vertices)
        vt_idx = None
        if len(parts) >= 2 and parts[1] != '':
            vt_idx = MeshLoader._parse_obj_index(parts[1], num_texcoords)
        return v_idx, vt_idx

    @staticmethod
    def _parse_obj_index(token: str, count: int) -> int:
        """
        Convertir un índice OBJ (1-based, o negativo relativo) a 0-based.

        Args:
            token: El índice como string
            count: Cantidad de elementos leídos hasta el momento, usado
                   para resolver índices negativos (relativos)

        Raises:
            ValueError: Si el índice es 0 o el token no es numérico
        """
        idx = int(token)
        if idx > 0:
            return idx - 1
        elif idx < 0:
            return count + idx
        raise ValueError(f"Índice inválido: {token}")

    def _find_or_add_vertex(
        self,
        vertex: Tuple[float, float, float],
        vertices_list: List,
        vertex_dict: dict,
        tolerance: float = GEOMETRY_TOLERANCE
    ) -> int:
        """
        Encontrar vértice duplicado o agregar nuevo

        Args:
            vertex: Coordenada (x, y, z)
            vertices_list: Lista de vértices
            vertex_dict: Diccionario para búsqueda rápida
            tolerance: Tolerancia para considerar duplicado

        Returns:
            Índice del vértice en vertices_list
        """
        # Crear clave con tolerancia
        key = tuple(round(v / tolerance) * tolerance for v in vertex)

        if key in vertex_dict:
            return vertex_dict[key]

        # Nuevo vértice
        idx = len(vertices_list)
        vertices_list.append(vertex)
        vertex_dict[key] = idx
        return idx

    def _validate_geometry(self, vertices: np.ndarray, faces: np.ndarray):
        """
        Validar geometría de la malla

        Args:
            vertices: Array Nx3 de vértices
            faces: Array Mx3 de índices de caras

        Raises:
            GeometryValidationError: Si hay problemas
        """
        # Verificar que hay datos
        if len(vertices) == 0:
            raise GeometryValidationError("No hay vértices")

        if len(faces) == 0:
            raise GeometryValidationError("No hay caras")

        # Verificar índices válidos
        max_idx = len(vertices)
        for face_idx, face in enumerate(faces):
            if not all(0 <= v_idx < max_idx for v_idx in face):
                raise GeometryValidationError(
                    f"Índice fuera de rango en cara {face_idx}: {face}"
                )

        # Verificar triángulos degenerados (área ~0)
        degenerate_count = 0
        for face_idx, face in enumerate(faces):
            v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]

            # Calcular área usando producto cruz
            edge1 = v1 - v0
            edge2 = v2 - v0
            normal = np.cross(edge1, edge2)
            area = np.linalg.norm(normal) / 2.0

            if area < GEOMETRY_TOLERANCE:
                degenerate_count += 1

        if degenerate_count > 0:
            warning = f"{degenerate_count} triángulos degenerados (área ~0)"
            self.validation_warnings.append(warning)
            self.logger.warning(warning)

        self.logger.info(f"Validación: {len(vertices)} vértices, {len(faces)} caras válidas")

    def _detect_and_suggest_scale(self, model: FootModel):
        """
        Detectar escala probable del modelo y sugerir normalización

        Args:
            model: FootModel a analizar
        """
        if model.bounds is None:
            return

        # Calcular dimensión máxima
        x_min, x_max, y_min, y_max, z_min, z_max = model.bounds
        max_dim = max(x_max - x_min, y_max - y_min, z_max - z_min)

        # Sugerir escala basada en tamaño típico de pie
        # Pie típico: 20-30 cm
        if max_dim < 0.5:
            # Probablemente en metros (0.2-0.3m = 20-30cm)
            suggestion = "Escala: probablemente METROS (20-30 cm foot es 0.2-0.3m)"
            model.scale = 1.0  # Mantener metros
            scale_factor = 1000  # Convertir a mm para display
        elif max_dim < 1:
            # Probablemente en decímetros
            suggestion = "Escala: probablemente DECÍMETROS"
            model.scale = 1.0
            scale_factor = 100  # Convertir a mm
        elif 100 < max_dim < 400:
            # Probablemente en milímetros (100-300mm = 10-30cm)
            suggestion = "Escala: probablemente MILÍMETROS (pie normal)"
            model.scale = 1.0  # Mantener mm
            scale_factor = 1
        elif 1000 < max_dim < 4000:
            # Probablemente en centímetros (100-300cm? no, eso sería grande)
            # O milímetros escalados
            suggestion = "Escala: REVISAR (tamaño inusual)"
            model.scale = 1.0
            scale_factor = 0.1
        else:
            suggestion = "Escala: desconocida (verificar manualmente)"
            model.scale = 1.0
            scale_factor = 1

        self.validation_warnings.append(suggestion)
        self.logger.info(suggestion)

    def normalize_scale(self, model: FootModel, target_dimension: float = 100.0):
        """
        Normalizar escala del modelo

        Args:
            model: FootModel a normalizar
            target_dimension: Dimensión máxima objetivo (default: 100 mm)
        """
        if model.bounds is None:
            model.compute_bounds()

        x_min, x_max, y_min, y_max, z_min, z_max = model.bounds
        max_dim = max(x_max - x_min, y_max - y_min, z_max - z_min)

        if max_dim > 0:
            scale_factor = target_dimension / max_dim
            model.vertices = model.vertices * scale_factor
            model.scale = scale_factor
            model.compute_bounds()
            self.logger.info(f"Escala normalizada: factor {scale_factor:.4f}")

    def center_at_origin(self, model: FootModel):
        """
        Centrar modelo en el origen

        Args:
            model: FootModel a centrar
        """
        model.center_at_origin()
        self.logger.info("Modelo centrado en origen")

