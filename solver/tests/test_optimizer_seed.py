from __future__ import annotations

import hashlib
import unittest

import numpy as np

from solver.fit_field import optimize_de


def _population_fingerprint(seed: int) -> str:
    result = optimize_de(
        lambda values: float(np.dot(values, values)),
        seed=seed,
        maxiter=0,
        popsize=12,
        workers=1,
        polish=False,
        report_every=0,
    )
    population = np.ascontiguousarray(result.population)
    return hashlib.sha256(population.tobytes()).hexdigest()


class DifferentialEvolutionSeedTests(unittest.TestCase):
    def test_seed_is_reproducible_and_changes_initial_population(self) -> None:
        first = _population_fingerprint(20260915)
        repeat = _population_fingerprint(20260915)
        second = _population_fingerprint(20260916)
        third = _population_fingerprint(20260917)
        self.assertEqual(first, repeat)
        self.assertEqual(len({first, second, third}), 3)


if __name__ == "__main__":
    unittest.main()
