"""Budget and publication regressions for the public history-page adapter."""

import ast
import asyncio
import random
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import Mock

from test_last_called_selection import NOW, immediate_async, load_helpers, record


class HistoryContinuationTests(TestCase):
    """Exercise resumed scans independently of Home Assistant setup."""

    def setUp(self):
        self.m = load_helpers()
        self.account = {}
        self.login = SimpleNamespace(
            session=SimpleNamespace(closed=False),
            url="amazon.ca",
            csrf_token="csrf",
            csrf_token_created_at=NOW // 1000,
        )
        self.request = self.m.AlexaAPI._static_request

    @immediate_async
    async def test_poll_does_not_follow_unrelated_push_to_older_page(self):
        self.account["last_called_activity_queue"] = [
            {"serial": "B", "activity_ts": NOW}
        ]
        self.request.side_effect = [
            {"customerHistoryRecords": [record("A")], "encodedRequestToken": "next"},
            {"customerHistoryRecords": [record("B", NOW - 100)]},
        ]
        records = await self.m._async_get_last_called_history(
            self.login, self.account, {"A", "B"}
        )
        self.assertEqual(records[0]["deviceSerialNumber"], "A")
        self.assertEqual(self.request.await_count, 1)

    @immediate_async
    async def test_persistently_rejected_cursor_is_eventually_discarded(self):
        queue = [{"serial": "A", "activity_ts": NOW}]
        self.request.return_value = {
            "customerHistoryRecords": [],
            "encodedRequestToken": "expired",
        }
        # Retain a checkpoint, then simulate Amazon rejecting every resumed token.
        self.request.side_effect = [self.request.return_value, None]
        await self.m._async_get_last_called_history(
            self.login, self.account, {"A"}, queue
        )
        for _ in range(2):
            self.request.side_effect = [self.request.return_value, None]
            await self.m._async_get_last_called_history(
                self.login, self.account, {"A"}, queue
            )
        self.assertNotIn("push", self.account["last_called_history_scans"])
        self.assertEqual(self.account["last_called_overlap_ts"], 0)

    @immediate_async
    async def test_deep_voice_after_budget_resumes_saved_cursor(self):
        """Fresh excluded heads cannot force the deep search back to page one."""
        self.request.side_effect = [
            {
                "customerHistoryRecords": [record(kind="ROUTINES_3P")],
                "encodedRequestToken": f"page-{i}",
            }
            for i in range(25)
        ] + [
            {
                "customerHistoryRecords": [record(kind="UNKNOWN")],
                "encodedRequestToken": "head",
            },
            {"customerHistoryRecords": [record("B", NOW - 100)]},
        ]
        result = await self.m._async_get_last_called_history(
            self.login, self.account, {"A", "B"}
        )
        self.assertEqual(result[0]["deviceSerialNumber"], "B")
        self.assertEqual(self.request.await_count, 27)
        self.assertEqual(
            self.request.call_args_list[-1].kwargs["data"]["previousRequestToken"],
            "page-24",
        )
        self.assertEqual(
            self.request.call_args_list[0].kwargs["query"],
            self.request.call_args_list[-1].kwargs["query"],
        )
        self.m.asyncio.sleep.assert_awaited_once_with(10)

    @immediate_async
    async def test_time_budget_checks_fresh_head(self):
        """New head voice wins without waiting for a deep scan to finish."""

        async def reply(*args, **kwargs):
            if self.request.await_count == 1:
                self.m.time.monotonic.return_value = 11
                return {
                    "customerHistoryRecords": [record(kind="UNKNOWN")],
                    "encodedRequestToken": "saved",
                }
            return {"customerHistoryRecords": [record()]}

        self.request.side_effect = reply
        result = await self.m._async_get_last_called_history(
            self.login, self.account, {"A"}
        )
        self.assertEqual(result[0]["utteranceType"], "GENERAL")
        self.assertEqual(self.request.await_count, 2)
        self.m.asyncio.sleep.assert_awaited_once_with(10)

    @immediate_async
    async def test_publish_push_before_overlap_then_resume_and_emit(self):
        """A voice result is committed before pausing; overlap has its own baseline."""
        self.account.update(last_called_customer_history_ts=NOW - 1000)
        queue = [
            {"serial": "A", "activity_ts": NOW},
            {"serial": "B", "activity_ts": NOW + 1},
        ]
        self.account["last_called_activity_queue"] = queue
        self.request.side_effect = [
            {
                "customerHistoryRecords": [
                    record(kind="GENERAL" if i == 0 else "ROUTINES_3P")
                ],
                "encodedRequestToken": f"page-{i}",
            }
            for i in range(25)
        ] + [
            {
                "customerHistoryRecords": [record("B", NOW + 1000)],
                "encodedRequestToken": "head",
            },
            {"customerHistoryRecords": [record("A", NOW - 200)]},
        ]

        async def publish(login, payload):
            self.account["last_called"] = payload
            self.account["last_called_customer_history_ts"] = payload["timestamp"]

        def pause(delay):
            self.assertEqual(self.account["last_called"]["serialNumber"], "A")
            self.m.time.monotonic.return_value += delay

        self.m.asyncio.sleep.side_effect = pause
        records = await self.m._async_get_last_called_history(
            self.login, self.account, {"A", "B"}, queue, on_payload=publish
        )
        self.assertEqual(self.account["last_called"]["timestamp"], NOW + 1000)
        self.assertEqual(
            self.account["last_called_history_result"]["serialNumber"], "A"
        )
        baseline = self.account["last_called_history_voice_account"]
        events = self.m._take_new_voice_records(baseline, records, NOW, NOW, {"A", "B"})
        self.assertEqual([r["timestamp"] for r in events], [NOW - 200, NOW])
        self.assertEqual(
            self.request.call_args_list[-1].kwargs["data"]["previousRequestToken"],
            "page-24",
        )
        self.assertTrue(self.account["last_called_history_recheck"])
        self.account["last_called_overlap_ts"] = NOW
        self.account.update(
            {k: v for k, v in baseline.items() if k.startswith("last_called_voice_")}
        )
        self.request.side_effect = None
        self.request.return_value = {
            "customerHistoryRecords": [record("B", NOW + 1000), record("A", NOW + 500)]
        }
        records = await self.m._async_get_last_called_history(
            self.login, self.account, {"A", "B"}, queue, on_payload=publish
        )
        events = self.m._take_new_voice_records(
            self.account["last_called_history_voice_account"],
            records,
            NOW + 1000,
            NOW,
            {"A", "B"},
        )
        self.assertEqual([r["timestamp"] for r in events], [NOW + 500, NOW + 1000])

    @immediate_async
    async def test_failure_after_publication_keeps_cursor_for_retry(self):
        """Failure does not roll back selected voice or discard overlap progress."""
        self.request.side_effect = [
            {"customerHistoryRecords": [record()], "encodedRequestToken": "saved"},
            None,
            {
                "customerHistoryRecords": [record(kind="UNKNOWN")],
                "encodedRequestToken": "head",
            },
            {"customerHistoryRecords": [record("B", NOW - 100)]},
        ]

        async def publish(login, payload):
            self.account["last_called_customer_history_ts"] = payload["timestamp"]

        queue = [{"serial": "A", "activity_ts": NOW}]
        self.assertIsNone(
            await self.m._async_get_last_called_history(
                self.login, self.account, {"A", "B"}, queue, on_payload=publish
            )
        )
        records = await self.m._async_get_last_called_history(
            self.login, self.account, {"A", "B"}, queue, on_payload=publish
        )
        self.assertEqual(len(records), 2)
        self.assertEqual(self.account["last_called_customer_history_ts"], NOW)
        self.assertEqual(
            self.request.call_args_list[-1].kwargs["data"]["previousRequestToken"],
            "saved",
        )
        self.assertEqual(
            self.account["last_called_history_voice_account"].get(
                "last_called_customer_history_ts", 0
            ),
            0,
        )

    @immediate_async
    async def test_session_replacement_discards_saved_cursor(self):
        """A cursor from a previous transport must not leak into the new session."""
        self.request.side_effect = [
            {
                "customerHistoryRecords": [record(kind="UNKNOWN")],
                "encodedRequestToken": "old",
            },
            None,
            {"customerHistoryRecords": [record()]},
        ]
        self.assertIsNone(
            await self.m._async_get_last_called_history(self.login, self.account, {"A"})
        )
        self.login.session = object()
        await self.m._async_get_last_called_history(self.login, self.account, {"A"})
        self.assertIsNone(
            self.request.call_args_list[-1].kwargs["data"]["previousRequestToken"]
        )

    @immediate_async
    async def test_invalid_cursor_restart_keeps_event_baseline_after_publication(self):
        """Selection must not become the overlap watermark after a cursor error."""
        self.request.side_effect = [
            {"customerHistoryRecords": [record()], "encodedRequestToken": "cycle"},
            {"customerHistoryRecords": [], "encodedRequestToken": "cycle"},
            {"customerHistoryRecords": [record(), record("B", NOW - 100)]},
        ]

        async def publish(login, payload):
            self.account["last_called_customer_history_ts"] = payload["timestamp"]

        queue = [{"serial": "A", "activity_ts": NOW}]
        self.assertIsNone(
            await self.m._async_get_last_called_history(
                self.login, self.account, {"A", "B"}, queue, on_payload=publish
            )
        )
        self.assertEqual(self.account["last_called_overlap_ts"], 0)
        records = await self.m._async_get_last_called_history(
            self.login, self.account, {"A", "B"}, queue, on_payload=publish
        )
        baseline = self.account["last_called_history_voice_account"]
        events = self.m._take_new_voice_records(baseline, records, NOW, NOW, {"A", "B"})
        self.assertEqual([r["timestamp"] for r in events], [NOW - 100, NOW])

    @immediate_async
    async def test_slow_head_cannot_starve_saved_continuation(self):
        """An expired head-check budget still reserves one cursor-progress request."""
        self.request.side_effect = [
            {
                "customerHistoryRecords": [record(kind="UNKNOWN")],
                "encodedRequestToken": f"page-{i}",
            }
            for i in range(25)
        ] + [
            {
                "customerHistoryRecords": [record(kind="UNKNOWN")],
                "encodedRequestToken": "head",
            },
            {"customerHistoryRecords": [record()]},
        ]
        original = self.request.side_effect

        # AsyncMock stores iterable side effects as iterators.
        async def reply(*args, **kwargs):
            if self.request.await_count == 26:
                self.m.time.monotonic.return_value += 11
            return next(original)

        self.request.side_effect = reply
        result = await self.m._async_get_last_called_history(
            self.login, self.account, {"A"}
        )
        self.assertEqual(result[0]["utteranceType"], "GENERAL")
        self.assertEqual(self.request.await_count, 27)

    async def _exercise_worker(self):
        """Execute the real worker body with mocked HA and scheduling transports."""
        from test_last_called_selection import SOURCE

        class Event:
            flag = True

            def is_set(self):
                return self.flag

            def set(self):
                self.flag = True

            def clear(self):
                self.flag = False

            async def wait(self):
                if not self.flag:
                    raise asyncio.CancelledError()

        class Lock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        async def wait_for(awaitable, timeout):
            try:
                return await awaitable
            except asyncio.CancelledError:
                if timeout < 15:
                    self.m.time.monotonic.return_value += timeout
                    raise asyncio.TimeoutError() from None
                raise

        self.login.close_requested = False
        self.login.status = {"login_successful": True}
        self.login.session.closed = False
        self.account.update(
            login_obj=self.login,
            last_called_probe_event=Event(),
            last_called_api_lock=Lock(),
            last_called_probe_trigger_cmd="PUSH_ACTIVITY",
            last_called_activity_queue=[{"serial": "A", "activity_ts": NOW}],
            last_called_last_pushed_activity={},
        )
        if self.request.side_effect is None:
            self.request.return_value = {"customerHistoryRecords": [record()]}
        hass = SimpleNamespace(
            data={"alexa_media": {"accounts": {"test": self.account}}},
            bus=SimpleNamespace(async_fire=Mock()),
        )
        ns = self.m._async_get_last_called_history.__globals__
        ns.update(hass=hass, email="test", debug=False, random=random)
        self.m.asyncio.wait_for = wait_for
        self.m.asyncio.TimeoutError = asyncio.TimeoutError
        for node in ast.parse(
            (SOURCE.parent / "const.py").read_text(encoding="utf-8")
        ).body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.startswith(
                        "LAST_CALLED"
                    ):
                        ns[target.id] = eval(
                            compile(ast.Expression(node.value), str(SOURCE), "eval"),
                            {"__builtins__": {}},
                            ns,
                        )

        async def update(login, payload):
            self.m._store_and_dispatch_last_called(hass, "test", payload)

        ns["update_last_called"] = update
        for name in (
            "AlexapyTooManyRequestsError",
            "AlexapyLoginError",
            "AlexapyConnectionError",
        ):
            ns[name] = type(name, (Exception,), {})
        worker = next(
            node
            for node in ast.walk(ast.parse(SOURCE.read_text(encoding="utf-8")))
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "_last_called_probe_worker"
        )
        exec(
            compile(ast.Module(body=[worker], type_ignores=[]), str(SOURCE), "exec"), ns
        )
        with self.assertRaises(asyncio.CancelledError):
            await ns["_last_called_probe_worker"]()
        self.assertEqual(self.account["last_called"]["serialNumber"], "A")
        expected_ts = getattr(self, "expected_ts", NOW)
        self.assertEqual(self.account["last_called"]["timestamp"], expected_ts)
        self.assertEqual(self.account["last_called_overlap_ts"], expected_ts)
        self.assertEqual(
            hass.bus.async_fire.call_count, getattr(self, "expected_events", 1)
        )
        self.assertEqual(self.account["last_called_activity_queue"], [])

    @immediate_async
    async def test_actual_worker_publishes_and_emits_after_overlap(self):
        """The real worker publishes once and emits the completed voice event."""
        await self._exercise_worker()

    @immediate_async
    async def test_actual_worker_budget_recheck_does_not_regress_or_lose_events(self):
        """Complete two real worker scans while voice selection leads event progress."""
        self.expected_ts = NOW + 1000
        self.expected_events = 4
        self.request.side_effect = [
            {
                "customerHistoryRecords": [
                    record(kind="GENERAL" if i == 0 else "ROUTINES_3P")
                ],
                "encodedRequestToken": f"page-{i}",
            }
            for i in range(25)
        ] + [
            {
                "customerHistoryRecords": [record("A", NOW + 1000)],
                "encodedRequestToken": "head",
            },
            {"customerHistoryRecords": [record("A", NOW - 200)]},
            {
                "customerHistoryRecords": [
                    record("A", NOW + 1000),
                    record("B", NOW + 500),
                ]
            },
        ]
        await self._exercise_worker()
        self.assertEqual(self.request.await_count, 28)
        self.assertEqual(self.m.async_dispatcher_send.call_count, 2)

    @immediate_async
    async def test_push_arriving_during_scan_survives_completion(self):
        self.expected_ts = NOW + 1000
        self.expected_events = 2

        async def reply(*args, **kwargs):
            if self.request.await_count == 1:
                self.account["last_called_probe_generation"] = 1
                self.account["last_called_activity_queue"] = [
                    {"serial": "A", "activity_ts": NOW + 1000}
                ]
                self.account["last_called_probe_event"].set()
                return {"customerHistoryRecords": [record()]}
            return {"customerHistoryRecords": [record(ts=NOW + 1000)]}

        self.request.side_effect = reply
        await self._exercise_worker()
        self.assertEqual(self.request.await_count, 2)
        self.assertEqual(self.m.async_dispatcher_send.call_count, 2)


class HistoryAsyncLifecycleTests(IsolatedAsyncioTestCase):
    """Check real task cancellation and history-lock release across a pause."""

    async def test_cancelled_pause_retains_cursor_and_releases_history_lock(self):
        m = load_helpers()
        ns = m._async_get_last_called_history.__globals__
        paused = asyncio.Event()

        async def pause(delay):
            paused.set()
            await asyncio.Event().wait()

        ns["asyncio"] = SimpleNamespace(
            CancelledError=asyncio.CancelledError, sleep=pause
        )
        ns["LAST_CALLED_HISTORY_MAX_PAGES"] = 2
        account = {}
        login = SimpleNamespace(
            session=object(),
            url="amazon.ca",
            csrf_token="csrf",
            csrf_token_created_at=NOW // 1000,
        )
        request = m.AlexaAPI._static_request
        request.side_effect = [
            {
                "customerHistoryRecords": [record(kind="UNKNOWN")],
                "encodedRequestToken": "one",
            },
            {
                "customerHistoryRecords": [record(kind="UNKNOWN")],
                "encodedRequestToken": "two",
            },
        ]
        lock = asyncio.Lock()

        async def scan():
            async with lock:
                return await m._async_get_last_called_history(login, account, {"A"})

        task = asyncio.create_task(scan())
        await asyncio.wait_for(paused.wait(), 2)
        self.assertTrue(lock.locked())
        waiter = asyncio.create_task(lock.acquire())
        await asyncio.sleep(0)
        self.assertFalse(waiter.done())
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        await asyncio.wait_for(waiter, 2)
        lock.release()
        self.assertEqual(
            account["last_called_history_scans"]["poll"]["cursor"].token, "two"
        )
        ns["asyncio"] = asyncio
        account["last_called_history_next_allowed"] = 0
        request.side_effect = [
            {"customerHistoryRecords": [record(kind="UNKNOWN")]},
            {"customerHistoryRecords": [record()]},
        ]
        records = await scan()
        self.assertEqual(records[0]["deviceSerialNumber"], "A")
        self.assertEqual(
            request.await_args.kwargs["data"]["previousRequestToken"], "two"
        )

    async def test_restart_uses_fresh_head_and_no_old_checkpoint(self):
        m = load_helpers()
        m._async_get_last_called_history.__globals__["asyncio"] = asyncio
        login = SimpleNamespace(
            session=object(),
            url="amazon.ca",
            csrf_token="csrf",
            csrf_token_created_at=NOW // 1000,
        )
        account = {}
        m.AlexaAPI._static_request.return_value = {"customerHistoryRecords": [record()]}
        records = await m._async_get_last_called_history(login, account, {"A"})
        self.assertEqual(records[0]["deviceSerialNumber"], "A")
        self.assertIsNone(
            m.AlexaAPI._static_request.await_args.kwargs["data"]["previousRequestToken"]
        )
        self.assertFalse(account["last_called_history_scans"])
