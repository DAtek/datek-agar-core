import numpy as np
from datek_agar_core.universe import Universe
from pydantic import BaseModel


class TestUniverse:
    def test_calculate_position_vector_array(self):
        universe = Universe(
            total_nutrient=20,
            world_size=1000,
        )

        o = np.array([[1, 3], [1, 3], [999.787, 0]], np.float32)

        p = np.array([[7, 8], [999, 998], [0.25, 0.33]])

        wanted_result = np.array([[6, 5], [-2, -5], [0.463, 0.33]])

        result = universe.calculate_position_vector_array(o, p)

        is_close = np.isclose(result, wanted_result, rtol=0.001)
        assert np.all(is_close)
