"""
Project IO - Guardar y cargar el estado de una sesión de medición

Responsabilidad:
- Serializar a JSON: ruta al archivo de malla original, los 3 puntos del
  plano de apoyo y la lista de mediciones
- Reconstruir ese estado al cargar un proyecto guardado

No guarda la malla en sí (sería redundante y pesado): guarda la ruta al
archivo .stl/.obj original, y quien cargue el proyecto es responsable de
volver a leerlo con MeshLoader. Desacoplado de Qt/VTK, igual que
mesh_loader.py y measurements.py.
"""
import json
import numpy as np
from typing import List, Optional, Tuple

from src.models.foot_model import Measurement, SupportPlane
from src.core.measurements import compute_support_plane

PROJECT_FORMAT_VERSION = 1


def save_project(
    filepath: str,
    mesh_filepath: str,
    plane_points: Optional[List[np.ndarray]],
    measurements: List[Measurement],
):
    """
    Guardar el estado de la sesión en un archivo JSON.

    Args:
        filepath: Ruta del archivo .json a escribir
        mesh_filepath: Ruta al archivo de malla (.stl/.obj) original
        plane_points: Los 3 puntos usados para definir el plano de apoyo, o
                      None/lista vacía si todavía no se definió
        measurements: Lista de Measurement a guardar
    """
    data = {
        'format_version': PROJECT_FORMAT_VERSION,
        'mesh_filepath': mesh_filepath,
        'plane_points': [np.asarray(p).tolist() for p in plane_points] if plane_points else None,
        'measurements': [
            {
                'name': m.name,
                'measurement_type': m.measurement_type,
                'value': m.value,
                'unit': m.unit,
                'point1': np.asarray(m.point1).tolist() if m.point1 is not None else None,
                'point2': np.asarray(m.point2).tolist() if m.point2 is not None else None,
                'point3': np.asarray(m.point3).tolist() if m.point3 is not None else None,
                'notes': m.notes,
            }
            for m in measurements
        ],
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def load_project(filepath: str) -> Tuple[str, Optional[SupportPlane], List[Measurement]]:
    """
    Cargar un proyecto guardado con `save_project`.

    Args:
        filepath: Ruta del archivo .json a leer

    Returns:
        Tupla (mesh_filepath, support_plane o None, lista de Measurement)

    Raises:
        ValueError: Si el archivo no tiene el formato esperado
        FileNotFoundError: Si el archivo de proyecto no existe
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'mesh_filepath' not in data:
        raise ValueError("Archivo de proyecto inválido: falta 'mesh_filepath'")

    mesh_filepath = data['mesh_filepath']

    plane = None
    if data.get('plane_points'):
        points = [np.array(p, dtype=np.float64) for p in data['plane_points']]
        plane = compute_support_plane(*points)

    measurements = []
    for item in data.get('measurements', []):
        measurements.append(Measurement(
            name=item['name'],
            measurement_type=item['measurement_type'],
            value=item['value'],
            unit=item.get('unit', 'mm'),
            point1=np.array(item['point1'], dtype=np.float64) if item.get('point1') is not None else None,
            point2=np.array(item['point2'], dtype=np.float64) if item.get('point2') is not None else None,
            point3=np.array(item['point3'], dtype=np.float64) if item.get('point3') is not None else None,
            notes=item.get('notes', ''),
        ))

    return mesh_filepath, plane, measurements
