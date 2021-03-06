from math import pi

import numpy as np


HALF_PI = pi / 2


class Universe:
    """
    Default length unit is micrometer
    """
    BACTERIA_STARTING_RADIUS = 0.5
    BACTERIA_STARTING_SIZE = BACTERIA_STARTING_RADIUS ** 2 * HALF_PI
    FOOD_ORGANISM_RADIUS = 0.3
    FOOD_ORGANISM_SIZE = FOOD_ORGANISM_RADIUS ** 2 * HALF_PI
    MIN_SPEED = 1
    MAX_SPEED = MIN_SPEED * 5
    MINIMAL_RADIUS_MODIFIER_TO_EAT = 1.25
    VIEW_DISTANCE = 20

    def __init__(
        self,
        *,
        total_nutrient: float,
        world_size: float,
    ):
        """
        :param total_nutrient: total area of nutrient
        :param world_size: total game area
        """
        self._total_nutrient = total_nutrient
        self._world_size = world_size
        self._half_world_size = self._world_size / 2

        self._speed_size_modifier = \
            (self.MIN_SPEED - self.MAX_SPEED) / (self._total_nutrient - self.BACTERIA_STARTING_SIZE)

    @property
    def total_nutrient(self) -> float:
        return self._total_nutrient

    @property
    def world_size(self) -> float:
        return self._world_size

    def calculate_organism_max_speed(self, radius: float) -> float:
        f"""
        Maximal speed of an organism.
        If an organism eats everything, it's speed becomes {self.MIN_SPEED} um/s.
        The smallest organism's max speed is {self.MAX_SPEED} um/s.
        Linear relationship.
        """
        size = radius ** 2 * HALF_PI

        return self.MAX_SPEED + self._speed_size_modifier * (size - self.BACTERIA_STARTING_SIZE)

    def calculate_position_vector_array(self, o: np.ndarray, p: np.ndarray) -> np.ndarray:
        vector = p - o
        vector[vector > self._half_world_size] -= self._world_size
        vector[vector < -self._half_world_size] += self._world_size

        return vector
