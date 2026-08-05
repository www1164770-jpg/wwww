from __future__ import annotations

import unittest

from backend.crawler.queue.states import (
    CANCELLED,
    COMPLETED,
    DEAD,
    FAILED,
    LEASED,
    PENDING,
    InvalidTaskTransition,
    assert_task_transition,
)


class TaskStateTests(unittest.TestCase):
    def test_documented_task_transitions_are_accepted(self) -> None:
        legal_transitions = (
            (PENDING, LEASED),
            (PENDING, CANCELLED),
            (LEASED, COMPLETED),
            (LEASED, FAILED),
            (LEASED, PENDING),
            (FAILED, PENDING),
            (FAILED, DEAD),
            (FAILED, CANCELLED),
        )

        for current, target in legal_transitions:
            with self.subTest(current=current, target=target):
                self.assertIsNone(assert_task_transition(current, target))

    def test_terminal_or_unknown_transitions_are_rejected(self) -> None:
        illegal_transitions = (
            (COMPLETED, LEASED),
            (DEAD, LEASED),
            (CANCELLED, PENDING),
            (PENDING, COMPLETED),
            ("invented", PENDING),
            (PENDING, "invented"),
        )

        for current, target in illegal_transitions:
            with self.subTest(current=current, target=target):
                with self.assertRaises(InvalidTaskTransition):
                    assert_task_transition(current, target)


if __name__ == "__main__":
    unittest.main()
