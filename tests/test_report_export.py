"""Tests de report_export: CSV y PDF"""
import pytest
import csv
import os
import tempfile
from src.core.report_export import export_measurements_csv, export_report_pdf
from src.models.foot_model import Measurement


def make_measurements():
    return [
        Measurement(name="Altura arco 1", measurement_type="altura_arco", value=18.234, unit="mm"),
        Measurement(name="Distancia plano 1", measurement_type="distancia_plano", value=62.5, unit="mm"),
    ]


class TestExportMeasurementsCSV:
    def test_creates_file_with_header_and_rows(self):
        measurements = make_measurements()
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "out.csv")
            export_measurements_csv(measurements, filepath, source_filename="pie.stl")
            assert os.path.exists(filepath)
            with open(filepath, newline='', encoding='utf-8') as f:
                rows = list(csv.reader(f))
            assert rows[0] == ['Archivo', 'pie.stl']
            header_row = next(r for r in rows if r and r[0] == 'Medicion')
            assert header_row == ['Medicion', 'Tipo', 'Valor', 'Unidad']
            data_rows = rows[rows.index(header_row) + 1:]
            assert data_rows[0][0] == "Altura arco 1"
            assert data_rows[0][2] == "18.23"

    def test_empty_measurements_still_writes_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "out.csv")
            export_measurements_csv([], filepath)
            assert os.path.exists(filepath)


class TestExportReportPDF:
    def test_creates_nonempty_pdf(self):
        measurements = make_measurements()
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "out.pdf")
            export_report_pdf(measurements, filepath, source_filename="pie.stl")
            assert os.path.exists(filepath)
            assert os.path.getsize(filepath) > 0
            with open(filepath, 'rb') as f:
                assert f.read(4) == b'%PDF'

    def test_pdf_without_measurements(self):
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "out.pdf")
            export_report_pdf([], filepath, source_filename="pie.stl")
            assert os.path.exists(filepath)

    def test_pdf_with_missing_screenshot_does_not_fail(self):
        measurements = make_measurements()
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "out.pdf")
            export_report_pdf(
                measurements, filepath, source_filename="pie.stl",
                screenshot_path=os.path.join(tmp, "no_existe.png")
            )
            assert os.path.exists(filepath)

    def test_many_measurements_span_multiple_pages(self):
        measurements = [
            Measurement(name=f"Medicion {i}", measurement_type="altura_arco", value=float(i), unit="mm")
            for i in range(80)
        ]
        with tempfile.TemporaryDirectory() as tmp:
            filepath = os.path.join(tmp, "out.pdf")
            export_report_pdf(measurements, filepath, source_filename="pie.stl")
            assert os.path.exists(filepath)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
