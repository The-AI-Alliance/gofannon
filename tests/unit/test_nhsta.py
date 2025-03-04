import pytest
from gofannon.nhsta import ComplaintsByVehicle

def test_complaints_by_vehicle():
    complaints_by_vehicle = ComplaintsByVehicle()
    result = complaints_by_vehicle.fn("Acura", "ILX", "2022")
    assert result is not None