"""Regression tests for voice-only history selection and timestamp arbitration.

Load the production helpers in isolation so these tests need neither an Amazon
session nor a running Home Assistant instance.
"""

import ast
import asyncio
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock

SOURCE = Path(__file__).parents[1] / "custom_components/alexa_media/__init__.py"
NOW = 1_800_000_000_000


def record(serial="A", ts=NOW, kind="GENERAL", summary="turn on lights"):
    """Build a normalized alexapy history record."""
    return {
        "deviceSerialNumber": serial,
        "creationTimestamp": ts,
        "utteranceType": kind,
        "description": {"summary": summary},
        "alexaResponse": "OK",
    }


def load_helpers():
    """Compile actual production functions with explicit external dependencies."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    names = {
        "_valid_voice_summary",
        "_valid_utterance_type",
        "_select_last_called_payload_from_records",
        "_collect_new_voice_records",
        "_store_and_dispatch_last_called",
        "_async_select_last_called",
        "_async_get_last_called_history",
        "_async_update_last_called_global",
        "_network_allowed",
        "_entity_backed_serials",
        "_take_new_voice_records",
        "_snapshot_last_called_activity_queue",
        "_remove_last_called_activity_queue_entries",
    }
    nodes = [node for node in tree.body if getattr(node, "name", "") in names]
    ns = {
        "HomeAssistant": object,
        "DATA_ALEXAMEDIA": "alexa_media",
        "DOMAIN": "alexa_media",
        "LAST_CALLED_ITEMS": 10,
        "LAST_CALLED_STALE_FUDGE_MS": 5000,
        "asyncio": SimpleNamespace(
            CancelledError=asyncio.CancelledError, sleep=AsyncMock()
        ),
        "_LOGGER": logging.getLogger(__name__),
        "hide_email": lambda v: v,
        "hide_serial": lambda v: v,
        "async_dispatcher_send": Mock(),
        "_existing_serials": lambda *args: {"A", "B"},
        "LAST_CALLED_HISTORY_MAX_PAGES": 25,
        "LAST_CALLED_HISTORY_BUDGET_S": 10.0,
        "time": SimpleNamespace(
            time=lambda: NOW / 1000, monotonic=Mock(return_value=0)
        ),
        "get_json_value": AsyncMock(
            side_effect=lambda response, *args: (response, isinstance(response, dict))
        ),
        "AlexaAPI": SimpleNamespace(
            _static_request=AsyncMock(),
            _normalize_history_record=AsyncMock(side_effect=lambda login, raw: raw),
        ),
    }

    async def public_page(
        login,
        start_time=None,
        end_time=None,
        max_record_size=None,
        *,
        continuation=None,
    ):
        """Model the public page contract over the existing mocked IO fixture."""
        payload = await ns["AlexaAPI"]._static_request(
            "post",
            login,
            data={"previousRequestToken": continuation.token if continuation else None},
            additional_headers={
                "anti-csrftoken-a2z": (
                    await login.get_csrf_token()
                    if login.csrf_token is None
                    else login.csrf_token
                )
            },
            query={
                "startTime": start_time,
                "endTime": end_time,
                "maxRecordSize": max_record_size,
            },
        )

        def result(status, records=None, cursor=None):
            return SimpleNamespace(
                status=status, records=records or [], continuation=cursor
            )

        if not isinstance(payload, dict) or not isinstance(
            payload.get("customerHistoryRecords"), list
        ):
            return result("error", cursor=continuation)
        token = payload.get("encodedRequestToken")
        seen = continuation.seen if continuation else set()
        if token not in (None, "") and (not isinstance(token, str) or token in seen):
            return result("error")
        records = [
            await ns["AlexaAPI"]._normalize_history_record(login, raw)
            for raw in payload["customerHistoryRecords"]
        ]
        if token in (None, ""):
            return result("exhausted", records)
        return result(
            "success", records, SimpleNamespace(token=token, seen=seen | {token})
        )

    ns["AlexaAPI"].get_customer_history_page = AsyncMock(side_effect=public_page)

    def advance_clock(delay):
        """Model cooldown completion without an event-loop transport."""
        ns["time"].monotonic.return_value += delay

    ns["asyncio"].sleep.side_effect = advance_clock
    constants = ast.parse((SOURCE.parent / "const.py").read_text(encoding="utf-8"))
    for node in constants.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ns:
                    ns[target.id] = ast.literal_eval(node.value)
    # Compile only selected helpers from this repository, never external input.
    exec(
        compile(ast.Module(body=nodes, type_ignores=[]), str(SOURCE), "exec"), ns
    )  # nosec B102
    return SimpleNamespace(**ns)


def immediate_async(test):
    """Run mocked API coroutines without network or event-loop transports."""

    def run(self):
        coroutine = test(self)
        try:
            coroutine.send(None)
        except StopIteration:
            return
        finally:
            coroutine.close()
        self.fail("Test unexpectedly suspended on an external awaitable")

    return run


class LastCalledSelectionTests(unittest.TestCase):
    """Exercise startup, polling, correlation and competing history responses."""

    def setUp(self):
        """Set up one isolated account."""
        self.m = load_helpers()
        self.account = {}
        self.hass = SimpleNamespace(
            data={"alexa_media": {"accounts": {"test": self.account}}}
        )
        self.login = SimpleNamespace(
            close_requested=False,
            session=SimpleNamespace(closed=False),
            status={"login_successful": True},
            url="amazon.ca",
            # Dummy fixture, never used for authentication.
            csrf_token="token",  # nosec B106
            csrf_token_created_at=NOW // 1000,
            get_csrf_token=AsyncMock(return_value="fresh-token"),
        )

    def select(self, records, queue=None):
        """Run the shared selector."""
        return self.m._select_last_called_payload_from_records(
            records, queue or [], self.account, {"A", "B"}
        )

    @immediate_async
    async def test_startup_without_push_selects_spoken_history(self):
        """Startup works with no queued push and no worker."""
        self.m.AlexaAPI._static_request.return_value = {
            "customerHistoryRecords": [record()]
        }
        await self.m._async_update_last_called_global(self.hass, self.login, "test")
        self.assertEqual(self.account["last_called"]["serialNumber"], "A")
        self.m.AlexaAPI._static_request.assert_awaited_once()
        query = self.m.AlexaAPI._static_request.call_args.kwargs["query"]
        self.assertEqual(query["maxRecordSize"], 10)
        self.assertEqual(query["startTime"], NOW - 7 * 24 * 3600 * 1000)

    @immediate_async
    async def test_startup_with_worker_keeps_background_trigger(self):
        """The initialized worker still owns startup refresh."""
        trigger = self.account["last_called_probe_trigger"] = Mock()
        await self.m._async_update_last_called_global(self.hass, self.login, "test")
        trigger.assert_called_once_with("GLOBAL_REFRESH", None)
        self.m.AlexaAPI._static_request.assert_not_awaited()

    @immediate_async
    async def test_polling_fallback_ignores_unmatched_push(self):
        """Independent refresh can select a different device than queued push."""
        self.account["last_called_activity_queue"] = [
            {"serial": "B", "activity_ts": NOW}
        ]
        self.m.AlexaAPI._static_request.return_value = {
            "customerHistoryRecords": [record()]
        }
        payload = await self.m._async_select_last_called(self.hass, self.login, "test")
        self.assertEqual(payload["serialNumber"], "A")

    def test_mixed_routine_and_voice_history(self):
        """Selection and voice events apply the same eligibility filter."""
        records = [record(ts=NOW - 1)]
        for kind in (
            "ROUTINES_OR_TAP_TO_ALEXA",
            "ROUTINES_3P",
            "DEVICE_ARBITRATION",
            "ASR_TIMEOUT",
            "WAKE_WORD_ONLY",
            "FUTURE_UTTERANCE_TYPE",
            "",
            None,
        ):
            records.insert(0, record(ts=NOW, kind=kind))
        payload, _ = self.select(records)
        self.assertEqual(payload["timestamp"], NOW - 1)
        events = self.m._collect_new_voice_records(records, NOW - 2, NOW, {"A"})
        self.assertEqual([event["timestamp"] for event in events], [NOW - 1])

    @immediate_async
    async def test_unavailable_history_preserves_state(self):
        """Missing, invalid and empty responses do not clear the current target."""
        current = {"serialNumber": "B", "timestamp": NOW - 10, "summary": "hello"}
        self.account["last_called"] = current
        for response in (None, [], {}, "invalid"):
            self.m.AlexaAPI._static_request.return_value = response
            await self.m._async_update_last_called_global(self.hass, self.login, "test")
            self.assertIs(self.account["last_called"], current)

    def test_arbitration_loser_does_not_replace_responder(self):
        """The later arbitration record must not win over the spoken responder."""
        payload, keys = self.select(
            [record("B", NOW + 1, "DEVICE_ARBITRATION"), record()],
            [{"serial": "A", "customer_id": None, "activity_ts": NOW}],
        )
        self.assertEqual(payload["serialNumber"], "A")
        self.assertEqual(keys, {("A", None)})

    def test_push_correlation_still_requires_serial_and_freshness(self):
        """Queued selection cannot match unrelated or stale spoken records."""
        queue = [{"serial": "B", "activity_ts": NOW, "customer_id": None}]
        self.assertEqual(self.select([record()], queue), (None, set()))
        self.assertEqual(self.select([record("B", NOW - 5001)], queue), (None, set()))
        self.assertEqual(
            self.select([record("B", NOW - 5000)], queue)[1], {("B", None)}
        )

    def test_watermark_and_duplicate_push_are_rejected(self):
        """Already applied or pushed records are not replayed."""
        self.account["last_called_customer_history_ts"] = NOW
        self.assertIsNone(self.select([record()])[0])
        self.account["last_called_customer_history_ts"] = 0
        self.account["last_called_last_pushed_activity"] = {"A": NOW}
        self.assertIsNone(self.select([record()])[0])

    @immediate_async
    async def test_push_completes_while_poll_is_in_flight(self):
        """A delayed poll cannot replace a newer push-correlated target."""

        async def delayed_history(*args, **kwargs):
            self.m._store_and_dispatch_last_called(
                self.hass,
                "test",
                {"serialNumber": "B", "timestamp": NOW + 1, "summary": "new command"},
            )
            return {"customerHistoryRecords": [record()]}

        self.m.AlexaAPI._static_request.side_effect = delayed_history
        await self.m._async_update_last_called_global(self.hass, self.login, "test")
        self.assertEqual(self.account["last_called"]["serialNumber"], "B")

    def test_storage_rechecks_race_and_equal_timestamp(self):
        """Even a selected payload cannot regress state at commit time."""
        store = self.m._store_and_dispatch_last_called
        current = {"serialNumber": "B", "timestamp": NOW, "summary": "new command"}
        store(self.hass, "test", current)
        for ts in (NOW - 1, NOW):
            store(self.hass, "test", {"serialNumber": "A", "timestamp": ts}, force=True)
        self.assertEqual(self.account["last_called"], current)
        self.assertEqual(self.m.async_dispatcher_send.call_count, 1)

    def test_seconds_timestamp_and_attributes_preserved(self):
        """Storage keeps normalization and the existing consumer payload."""
        self.m._store_and_dispatch_last_called(
            self.hass,
            "test",
            {
                "serialNumber": "A",
                "timestamp": NOW // 1000,
                "summary": "hello",
                "response": "OK",
            },
        )
        self.assertEqual(
            self.account["last_called"],
            {
                "serialNumber": "A",
                "timestamp": NOW,
                "summary": "hello",
                "response": "OK",
            },
        )

    def test_malformed_and_unsorted_records(self):
        """Invalid records are skipped and timestamps determine the winner."""
        records = [
            record(ts=NOW - 1),
            None,
            record(ts="bad"),
            record(summary="?!"),
            record("UNKNOWN", NOW + 1),
            record(),
        ]
        records[3]["description"] = "bad"
        self.assertEqual(self.select(records)[0]["timestamp"], NOW)

    @immediate_async
    async def test_voice_beyond_ten_pages(self):
        """Ten excluded pages cannot hide GENERAL on page eleven."""
        pages = [
            {
                "customerHistoryRecords": [
                    record(
                        ts=NOW - page * 10 - i,
                        kind=(
                            "ROUTINES_OR_TAP_TO_ALEXA"
                            if page % 2
                            else "FUTURE_UTTERANCE_TYPE"
                        ),
                    )
                    for i in range(10)
                ],
                "encodedRequestToken": f"page-{page + 1}",
            }
            for page in range(10)
        ]
        pages.append(
            {
                "customerHistoryRecords": [record("B", NOW - 100)],
                "encodedRequestToken": "unused",
            }
        )
        request = self.m.AlexaAPI._static_request
        request.side_effect = pages
        result = await self.m._async_select_last_called(self.hass, self.login, "test")
        self.assertEqual(result["serialNumber"], "B")
        self.assertEqual(request.await_count, 11)
        self.assertEqual(
            [
                call.kwargs["data"]["previousRequestToken"]
                for call in request.call_args_list
            ],
            [None] + [f"page-{i}" for i in range(1, 11)],
        )

    @immediate_async
    async def test_poll_stops_after_first_eligible_page(self):
        """AMP sorts the whole page and ignores later continuation tokens."""
        self.m.AlexaAPI._static_request.return_value = {
            "customerHistoryRecords": [
                record(ts=NOW, kind="ROUTINES_OR_TAP_TO_ALEXA"),
                record("B", NOW - 3),
                record("A", NOW - 1),
            ],
            "encodedRequestToken": "do-not-fetch",
        }
        result = await self.m._async_select_last_called(self.hass, self.login, "test")
        self.assertEqual(result["timestamp"], NOW - 1)
        self.m.AlexaAPI._static_request.assert_awaited_once()

    @immediate_async
    async def test_poll_stops_at_known_timestamp(self):
        """Only excluded activity after the known interaction needs no deeper search."""
        self.account["last_called_customer_history_ts"] = NOW - 10
        self.m.AlexaAPI._static_request.side_effect = [
            {
                "customerHistoryRecords": [record(ts=NOW, kind="ROUTINES_3P")],
                "encodedRequestToken": "next",
            },
            {
                "customerHistoryRecords": [record(ts=NOW - 10)],
                "encodedRequestToken": "older",
            },
        ]
        result = await self.m._async_select_last_called(self.hass, self.login, "test")
        self.assertIsNone(result)
        self.assertEqual(self.m.AlexaAPI._static_request.await_count, 2)

    @immediate_async
    async def test_push_keeps_voice_event_overlap_across_pages(self):
        """A match does not truncate other-device and late voice-event records."""
        self.account["last_called_customer_history_ts"] = NOW - 100
        queue = [{"serial": "A", "activity_ts": NOW}]
        self.m.AlexaAPI._static_request.side_effect = [
            {"customerHistoryRecords": [record()], "encodedRequestToken": "two"},
            {
                "customerHistoryRecords": [record("B", NOW - 200)],
                "encodedRequestToken": "three",
            },
            {
                "customerHistoryRecords": [record("B", NOW - 5100)],
                "encodedRequestToken": "older",
            },
        ]
        result = await self.m._async_get_last_called_history(
            self.login,
            self.account,
            {"A", "B"},
            queue,
            start_time=NOW - 900_000,
            end_time=NOW + 900_000,
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(self.m.AlexaAPI._static_request.await_count, 3)
        for call in self.m.AlexaAPI._static_request.call_args_list:
            self.assertEqual(call.kwargs["query"]["startTime"], NOW - 900_000)
            self.assertEqual(call.kwargs["query"]["endTime"], NOW + 900_000)

    @immediate_async
    async def test_failed_later_page_discards_partial_push_history(self):
        """Unavailable pages do not turn partial correlation into complete history."""
        self.m.AlexaAPI._static_request.side_effect = [
            {"customerHistoryRecords": [record()], "encodedRequestToken": "next"},
            None,
        ]
        result = await self.m._async_get_last_called_history(
            self.login, self.account, {"A"}, [{"serial": "A", "activity_ts": NOW}]
        )
        self.assertIsNone(result)

    @immediate_async
    async def test_repeated_and_invalid_tokens_are_bounded(self):
        """Broken continuation chains neither loop nor select partial history."""
        for token in ("same", 123):
            self.m.AlexaAPI._static_request.reset_mock()
            self.m.AlexaAPI._static_request.side_effect = [
                {
                    "customerHistoryRecords": [record(kind="ROUTINES_3P")],
                    "encodedRequestToken": token,
                },
                {"customerHistoryRecords": [], "encodedRequestToken": token},
            ]
            self.assertIsNone(
                await self.m._async_select_last_called(self.hass, self.login, "test")
            )
            self.assertLessEqual(self.m.AlexaAPI._static_request.await_count, 2)

    @immediate_async
    async def test_csrf_refresh_and_window_bounds(self):
        """Transport keeps alexapy's token refresh and never searches beyond seven days."""
        self.login.csrf_token = None
        self.m.AlexaAPI._static_request.return_value = {"customerHistoryRecords": []}
        await self.m._async_get_last_called_history(
            self.login,
            self.account,
            {"A"},
            start_time=1,
        )
        self.login.get_csrf_token.assert_awaited_once()
        call = self.m.AlexaAPI._static_request.call_args
        self.assertEqual(
            call.kwargs["additional_headers"]["anti-csrftoken-a2z"], "fresh-token"
        )
        self.assertEqual(call.kwargs["query"]["startTime"], NOW - 7 * 24 * 3600 * 1000)
        self.assertEqual(call.kwargs["query"]["endTime"], NOW + 24 * 3600 * 1000)

    @immediate_async
    async def test_raw_records_are_normalized_before_eligibility(self):
        """Reuse alexapy normalization instead of interpreting transcripts in AMP."""
        raw = {
            "recordKey": "opaque",
            "timestamp": NOW,
            "voiceHistoryRecordItems": [{"recordItemType": "CUSTOMER_TRANSCRIPT"}],
        }
        self.m.AlexaAPI._static_request.return_value = {"customerHistoryRecords": [raw]}
        self.m.AlexaAPI._normalize_history_record.side_effect = None
        self.m.AlexaAPI._normalize_history_record.return_value = record()
        result = await self.m._async_select_last_called(self.hass, self.login, "test")
        self.assertEqual(result["summary"], "turn on lights")
        self.m.AlexaAPI._normalize_history_record.assert_awaited_once_with(
            self.login, raw
        )

    @immediate_async
    async def test_straddling_timestamp_page_does_not_truncate_push_history(self):
        """One older outlier in a page cannot hide a later-page voice burst."""
        self.account["last_called_customer_history_ts"] = NOW - 100
        self.m.AlexaAPI._static_request.side_effect = [
            {
                "customerHistoryRecords": [record(), record(ts=NOW - 6000)],
                "encodedRequestToken": "next",
            },
            {"customerHistoryRecords": [record("B", NOW - 200)]},
        ]
        result = await self.m._async_get_last_called_history(
            self.login, self.account, {"A", "B"}, [{"serial": "A", "activity_ts": NOW}]
        )
        self.assertEqual(len(result), 3)
        self.assertEqual(self.m.AlexaAPI._static_request.await_count, 2)

    @immediate_async
    async def test_transport_errors_and_cancellation_are_not_swallowed(self):
        """Existing caller backoff and cancellation still own transport failures."""
        for error in (RuntimeError("transport failure"), asyncio.CancelledError()):
            self.m.AlexaAPI._static_request.reset_mock()
            self.m.AlexaAPI._static_request.side_effect = error
            with self.assertRaises(type(error)):
                await self.m._async_select_last_called(self.hass, self.login, "test")
            self.m.AlexaAPI._static_request.assert_awaited_once()

    def test_cooldown_keeps_request_pending_without_another_trigger(self):
        """A single trigger waits and discovers history published during cooldown."""

        class Pause:
            """Represent an unresolved sleep without creating real transports."""

            def __await__(self):
                yield "cooldown"

        async def sleep(delay):
            self.assertEqual(delay, 10)
            await Pause()

        self.account["last_called_history_next_allowed"] = 10
        self.m.asyncio.sleep.side_effect = sleep
        coroutine = self.m._async_update_last_called_global(
            self.hass, self.login, "test", force=True
        )
        try:
            self.assertEqual(coroutine.send(None), "cooldown")
            self.m.AlexaAPI._static_request.assert_not_awaited()
            self.m.time.monotonic.return_value = 10
            self.m.AlexaAPI._static_request.return_value = {
                "customerHistoryRecords": [record()]
            }
            with self.assertRaises(StopIteration):
                coroutine.send(None)
            self.assertEqual(self.account["last_called"]["serialNumber"], "A")
            self.assertEqual(self.m.AlexaAPI._static_request.await_count, 1)
        finally:
            coroutine.close()

    @immediate_async
    async def test_push_recovers_during_cooldown(self):
        """Correlated history retrieval remains pending through the same cooldown."""
        self.account["last_called_history_next_allowed"] = 10
        self.m.AlexaAPI._static_request.return_value = {
            "customerHistoryRecords": [record()]
        }
        queue = [{"serial": "A", "customer_id": None, "activity_ts": NOW}]
        result = await self.m._async_get_last_called_history(
            self.login, self.account, {"A", "B"}, queue
        )
        payload, resolved = self.select(result, queue)
        self.assertEqual(payload["serialNumber"], "A")
        self.assertEqual(resolved, {("A", None)})
        self.m.asyncio.sleep.assert_awaited_once_with(10)

    @immediate_async
    async def test_cancellation_during_cooldown_makes_no_request(self):
        """Account unload can cancel the delay without starting more API traffic."""
        self.account["last_called_history_next_allowed"] = 10
        self.m.asyncio.sleep.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            await self.m._async_select_last_called(self.hass, self.login, "test")
        self.m.AlexaAPI._static_request.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
