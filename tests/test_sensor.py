"""Tests for sensor module - specifically the _update_recurring_alarm method.

This module tests the fix for a critical bug in sensor.py where alarm.isoweekday
was used instead of alarm.isoweekday() - missing the parentheses to actually
call the method.

Without the parentheses, the condition would compare a method object to integers,
which would always be True (method objects are truthy and never equal to integers),
causing incorrect alarm scheduling.

The tests use source code analysis to verify the fix is in place, avoiding the
complexity of importing the actual module with its Home Assistant dependencies.
"""


class TestUpdateRecurringAlarmBugfix:
    """Test the _update_recurring_alarm method fix in sensor.py.

    These tests verify that isoweekday() is correctly called as a method
    (with parentheses) rather than accessed as an attribute (without parentheses).
    """

    def test_isoweekday_is_called_as_method_not_accessed_as_attribute(self) -> None:
        """Verify isoweekday() is called with parentheses in the while loop.

        This is the primary regression test for the bug where alarm.isoweekday
        was used without parentheses. The correct code is:

            while (
                alarm_on
                and recurrence
                and alarm.isoweekday() not in recurrence  # <-- parentheses required
                and alarm < dt.now()
            ):

        Without parentheses, the method object itself would be compared to the
        recurrence set, which would never match, causing incorrect behavior.
        """
        with open("custom_components/alexa_media/sensor.py", encoding="utf-8") as f:
            content = f.read()

        # Find the while loop with the isoweekday check
        # The correct pattern should have isoweekday() with parentheses
        assert "alarm.isoweekday()" in content, (
            "BUGFIX MISSING: alarm.isoweekday() not found in sensor.py. "
            "The method must be called with parentheses. "
            "Without parentheses, Python would compare the method object "
            "(not the return value) to the recurrence set."
        )

        # Verify it's used in the 'not in recurrence' check
        assert "isoweekday() not in recurrence" in content, (
            "The isoweekday() call should be used in a 'not in recurrence' check"
        )

    def test_while_loop_structure_is_correct(self) -> None:
        """Verify the while loop has the correct structure for recurring alarms.

        The while loop should check:
        1. alarm_on - alarm is enabled
        2. recurrence - there's a recurrence pattern
        3. alarm.isoweekday() not in recurrence - current day not in pattern
        4. alarm < dt.now() - alarm time is in the past
        """
        with open("custom_components/alexa_media/sensor.py", encoding="utf-8") as f:
            content = f.read()

        # Find the while loop block
        while_start = content.find("while (")
        assert while_start != -1, "while loop not found in sensor.py"

        # Get a reasonable chunk to analyze the loop structure
        while_block = content[while_start : while_start + 300]

        # Verify all required conditions are present
        assert "alarm_on" in while_block, "alarm_on condition missing from while loop"
        assert "recurrence" in while_block, (
            "recurrence condition missing from while loop"
        )
        assert "isoweekday()" in while_block, (
            "isoweekday() (with parentheses) missing from while loop"
        )
        assert "not in recurrence" in while_block, (
            "'not in recurrence' check missing from while loop"
        )

    def test_alarm_is_incremented_by_one_day_in_loop(self) -> None:
        """Verify the alarm is advanced by one day in the while loop body.

        The loop should increment the alarm by one day until it lands on
        a day that matches the recurrence pattern.
        """
        with open("custom_components/alexa_media/sensor.py", encoding="utf-8") as f:
            content = f.read()

        # Find the timedelta(days=1) addition
        assert "timedelta(days=1)" in content, (
            "The recurring alarm logic should increment by timedelta(days=1)"
        )

        # Find the while loop and verify the increment is inside it
        while_start = content.find("while (")
        while_end = content.find("alarm += datetime.timedelta", while_start)
        assert while_start != -1 and while_end != -1, (
            "Could not find while loop with alarm increment"
        )
        assert while_end > while_start, (
            "alarm += datetime.timedelta should appear after the while statement"
        )

    def test_no_isoweekday_without_parentheses_in_while_loop(self) -> None:
        """Verify there's no incorrect usage of isoweekday without parentheses.

        This test specifically checks for the bug pattern: using isoweekday
        without parentheses in a comparison context.
        """
        with open("custom_components/alexa_media/sensor.py", encoding="utf-8") as f:
            content = f.read()

        # Find the while loop section
        while_start = content.find("while (")
        if while_start == -1:
            return  # No while loop found, nothing to check

        # Get the while loop and its body
        while_block = content[while_start : while_start + 400]

        # Check for the buggy pattern: isoweekday followed by something
        # other than parentheses (like "isoweekday not in" which is wrong)
        import re

        # This pattern matches isoweekday NOT followed by ()
        buggy_pattern = re.compile(r"isoweekday(?!\s*\()")
        matches = buggy_pattern.findall(while_block)

        # All occurrences of isoweekday in the while block should have ()
        # If there are matches, they're bugs
        assert len(matches) == 0, (
            f"Found {len(matches)} occurrence(s) of 'isoweekday' without "
            "parentheses in the while loop. This is the bug that was fixed. "
            "isoweekday must be called as a method: alarm.isoweekday()"
        )


class TestRecurringPatternConstants:
    """Tests for recurring pattern constants in sensor.py."""

    def test_recurring_pattern_iso_set_constant_exists(self) -> None:
        """Verify RECURRING_PATTERN_ISO_SET constant is defined."""
        with open("custom_components/alexa_media/sensor.py", encoding="utf-8") as f:
            content = f.read()

        assert "RECURRING_PATTERN_ISO_SET" in content, (
            "RECURRING_PATTERN_ISO_SET constant not found in sensor.py"
        )

    def test_recurring_pattern_used_in_recurrence_check(self) -> None:
        """Verify the recurring pattern is used to get the recurrence set."""
        with open("custom_components/alexa_media/sensor.py", encoding="utf-8") as f:
            content = f.read()

        # The code should get the recurrence set from the pattern
        assert "recurringPattern" in content, (
            "recurringPattern key lookup not found in sensor.py"
        )
        assert "RECURRING_PATTERN_ISO_SET.get" in content, (
            "RECURRING_PATTERN_ISO_SET.get() call not found in sensor.py"
        )
