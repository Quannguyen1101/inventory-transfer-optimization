import pytest
from src.forecasting.base import Forecaster


def test_cannot_instantiate_abstract_forecaster():
    with pytest.raises(TypeError):
        Forecaster()
