"""Independent D1 calculations and D2 repeated-shift stability checks."""

import math
import unittest

from engine import (
    BASE_CRUSHER_TPH, BASE_SPEED_KMH, CAPACITY_T, DUMP_SECONDS,
    LOAD_SECONDS, ROM_BIN_CAPACITY_T, ROUTE_KM, MineEngine, projection,
)


def advance(mine: MineEngine, hours: float, step_s: float = 60.0) -> None:
    for _ in range(int(round(hours * 3600 / step_s))):
        mine.step(step_s)


class IndependentCalculationTests(unittest.TestCase):
    """Recompute core values without calling the engine's projection helpers."""

    def test_free_cycle_and_service_capacities_match_independent_arithmetic(self):
        one_way_min = ROUTE_KM / BASE_SPEED_KMH * 60.0
        free_cycle_min = LOAD_SECONDS / 60.0 + DUMP_SECONDS / 60.0 + 2 * one_way_min
        loader_tph = CAPACITY_T * 60.0 / (LOAD_SECONDS / 60.0)
        dump_tph = CAPACITY_T * 60.0 / (DUMP_SECONDS / 60.0)

        self.assertAlmostEqual(one_way_min, 7.68, places=9)
        self.assertAlmostEqual(free_cycle_min, 22.36, places=9)
        self.assertAlmostEqual(loader_tph, 770.0, places=9)
        self.assertAlmostEqual(dump_tph, 4620.0, places=9)
        self.assertEqual(BASE_CRUSHER_TPH, 900.0)

        plan = projection("baseline")
        self.assertAlmostEqual(plan["free_cycle_min"], free_cycle_min, places=9)
        self.assertAlmostEqual(plan["limits_tph"]["loading resource"], loader_tph, places=9)
        self.assertAlmostEqual(plan["limits_tph"]["dump point"], dump_tph, places=9)

    def test_fleet_requirement_is_independently_derived(self):
        free_cycle_min = 6.0 + 1.0 + 2 * 3.2 / 25.0 * 60.0
        required = math.ceil(770.0 * free_cycle_min / (77.0 * 60.0) - 1e-12)
        self.assertEqual(required, 4)

        three_truck_supply = 3 * 77.0 * 60.0 / free_cycle_min
        four_truck_supply = 4 * 77.0 * 60.0 / free_cycle_min
        self.assertLess(three_truck_supply, 770.0)
        self.assertGreater(four_truck_supply, 770.0)
        self.assertAlmostEqual(projection("baseline", truck_count=3)["throughput_tph"],
                               three_truck_supply, places=9)
        self.assertAlmostEqual(projection("baseline", truck_count=4)["throughput_tph"],
                               770.0, places=9)

    def test_engine_cycle_components_reconcile(self):
        mine = MineEngine()
        advance(mine, 12)
        completed = [truck for truck in mine.trucks if truck.last_cycle_s > 0]
        self.assertTrue(completed)
        for truck in completed:
            expected = (
                truck.last_wait_s + LOAD_SECONDS
                + 2 * ROUTE_KM / BASE_SPEED_KMH * 3600.0 + DUMP_SECONDS
            )
            self.assertAlmostEqual(truck.last_cycle_s, expected, places=6, msg=truck.name)


class LongRunStabilityTests(unittest.TestCase):
    """Exercise eight simulated shifts with repeated state and policy changes."""

    def test_eight_shift_disruption_and_reset_sequence_stays_valid_and_bounded(self):
        mine = MineEngine(seed=42)
        schedule = (
            ("baseline", "fixed"),
            ("truck_breakdown", "smart"),
            ("road_closure", "fixed"),
            ("crusher_slowdown", "smart"),
        ) * 2
        previous_production = mine.production_t
        max_events = max_history = 0

        for scenario, dispatch in schedule:
            mine.set_dispatch(dispatch)
            mine.set_scenario(scenario)
            advance(mine, 8)

            self.assertAlmostEqual(mine.mass_balance_error_t(), 0.0, places=6)
            self.assertGreaterEqual(mine.rom_inventory_t, 0.0)
            self.assertLessEqual(mine.rom_inventory_t, ROM_BIN_CAPACITY_T + 1e-6)
            self.assertGreaterEqual(mine.production_t, previous_production)
            previous_production = mine.production_t

            exc = list(mine.excavator_queue)
            dump = list(mine.dump_queue)
            self.assertEqual(len(exc), len({t.name for t in exc}))
            self.assertEqual(len(dump), len({t.name for t in dump}))
            self.assertLessEqual(sum(t is mine.excavator_truck for t in mine.trucks), 1)
            self.assertLessEqual(sum(t is mine.dump_truck for t in mine.trucks), 1)
            for truck in mine.trucks:
                memberships = (
                    truck in exc, truck in dump,
                    truck is mine.excavator_truck, truck is mine.dump_truck,
                )
                self.assertLessEqual(sum(memberships), 1, truck.name)
                self.assertGreaterEqual(truck.payload_t, 0.0)
                self.assertLessEqual(truck.payload_t, CAPACITY_T)

            max_events = max(max_events, len(mine._events))
            max_history = max(max_history, len(mine._history))
            mine.set_dispatch("fixed")
            mine.set_scenario("baseline")
            advance(mine, 1)
            self.assertFalse([t for t in mine.trucks if t.state in {"breakdown", "blocked"}])
            self.assertIsNone(mine.blockage)

        self.assertAlmostEqual(mine.mass_balance_error_t(), 0.0, places=6)
        self.assertLess(max_events, 64, "event heap should not grow with completed shifts")
        self.assertLess(max_history, 128, "rolling history should remain bounded")


if __name__ == "__main__":
    unittest.main()
