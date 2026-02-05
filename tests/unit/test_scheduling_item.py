import pytest
from app.models.scheduling import SchedulingItem
from datetime import datetime


def test_render_filename_basic():
    s = SchedulingItem(
        query='TEST-001.sql',
        connection='A00',
        output_filename_template='{query_name}_{date}.xlsx',
        output_date_format='%Y-%m-%d',
        output_offset_days=0
    )
    fname = s.render_filename(datetime(2025,10,12,8,0))
    assert 'TEST-001' in fname
    assert '2025-10-12' in fname


def test_render_filename_date_minus_one():
    s = SchedulingItem(
        query='REPORT.sql',
        connection='A00',
        output_filename_template='{query_name}_{date-1}.xlsx',
        output_date_format='%Y-%m-%d',
        output_offset_days=0
    )
    fname = s.render_filename(datetime(2025,10,12,8,0))
    assert '2025-10-11' in fname


def test_render_filename_timestamp_append():
    # Usa il token {timestamp} direttamente nel template invece del flag deprecato
    s = SchedulingItem(
        query='RPT.sql',
        connection='A00',
        output_filename_template='{query_name}_{date}_{timestamp}.xlsx',
        output_date_format='%Y%m%d'
    )
    fname = s.render_filename(datetime(2025,1,2,9,5))
    assert '20250102' in fname
    assert '_' in fname
