from __future__ import annotations

import time

import pytest

from workflows.distributed import WorkerPool, WorkerRegistration, TaskScheduler
from workflows.distributed.protocol import (
    Heartbeat,
    TaskAssignment,
    TaskResult,
    WorkerStatus,
)
from workflows.distributed.scheduler import _WorkerState


class TestProtocolMessages:
    def test_worker_registration_roundtrip(self) -> None:
        original = WorkerRegistration(worker_id="w1", capabilities=["cpu", "gpu"], version="2.0")
        data = original.to_json()
        restored = WorkerRegistration.from_json(data)
        assert restored.worker_id == "w1"
        assert restored.capabilities == ["cpu", "gpu"]
        assert restored.version == "2.0"

    def test_task_assignment_roundtrip(self) -> None:
        original = TaskAssignment(task_id="t1", task_type="compute", payload={"x": 1}, priority=5)
        data = original.to_json()
        restored = TaskAssignment.from_json(data)
        assert restored.task_id == "t1"
        assert restored.task_type == "compute"
        assert restored.payload == {"x": 1}
        assert restored.priority == 5

    def test_task_result_roundtrip(self) -> None:
        original = TaskResult(task_id="t1", success=True, data=42, error=None)
        data = original.to_json()
        restored = TaskResult.from_json(data)
        assert restored.task_id == "t1"
        assert restored.success is True
        assert restored.data == 42

    def test_heartbeat_roundtrip(self) -> None:
        original = Heartbeat(worker_id="w1", status=WorkerStatus.BUSY, timestamp=12345.0)
        data = original.to_json()
        restored = Heartbeat.from_json(data)
        assert restored.worker_id == "w1"
        assert restored.status == WorkerStatus.BUSY
        assert restored.timestamp == 12345.0


class TestTaskScheduler:
    def test_register_worker(self) -> None:
        sched = TaskScheduler()
        reg = WorkerRegistration(worker_id="w1", capabilities=["cpu"])
        sched.register_worker(reg)
        assert sched.worker_count == 1

    def test_heartbeat_updates_status(self) -> None:
        sched = TaskScheduler()
        sched.register_worker(WorkerRegistration(worker_id="w1"))
        sched.heartbeat("w1", WorkerStatus.BUSY)
        assert sched._workers["w1"].status == WorkerStatus.BUSY

    def test_submit_and_assign_task(self) -> None:
        sched = TaskScheduler()
        sched.register_worker(WorkerRegistration(worker_id="w1", capabilities=["cpu"]))
        sched.submit_task(TaskAssignment(task_id="t1", task_type="cpu"))
        assignment = sched.next_assignment("w1")
        assert assignment is not None
        assert assignment.task_id == "t1"
        assert sched.pending_count == 0

    def test_no_assignment_for_busy_worker(self) -> None:
        sched = TaskScheduler()
        sched.register_worker(WorkerRegistration(worker_id="w1"))
        sched.heartbeat("w1", WorkerStatus.BUSY)
        sched.submit_task(TaskAssignment(task_id="t1", task_type="cpu"))
        assert sched.next_assignment("w1") is None

    def test_task_retry_on_failure(self) -> None:
        sched = TaskScheduler()
        sched.register_worker(WorkerRegistration(worker_id="w1", capabilities=["cpu"]))
        sched.submit_task(TaskAssignment(task_id="t1", task_type="cpu"))
        assignment = sched.next_assignment("w1")
        assert assignment is not None
        sched.complete_task("w1", "t1", success=False)
        assert sched.pending_count == 1  # Retried

    def test_prune_unhealthy_workers(self) -> None:
        sched = TaskScheduler(heartbeat_timeout=0.1)
        sched.register_worker(WorkerRegistration(worker_id="w1"))
        time.sleep(0.15)
        removed = sched.prune_unhealthy_workers()
        assert "w1" in removed
        assert sched.worker_count == 0

    def test_capability_based_routing(self) -> None:
        sched = TaskScheduler()
        sched.register_worker(WorkerRegistration(worker_id="w1", capabilities=["cpu"]))
        sched.register_worker(WorkerRegistration(worker_id="w2", capabilities=["gpu"]))
        sched.submit_task(TaskAssignment(task_id="t1", task_type="gpu"))
        assignment = sched.next_assignment("w1")
        assert assignment is None  # w1 can't handle gpu
        assignment = sched.next_assignment("w2")
        assert assignment is not None
        assert assignment.task_id == "t1"


class TestWorkerPool:
    def test_pool_start_stop(self) -> None:
        pool = WorkerPool(max_workers=2)
        pool.start()
        assert pool._executor is not None
        pool.stop()
        assert pool._executor is None

    def test_pool_context_manager(self) -> None:
        with WorkerPool(max_workers=2) as pool:
            assert pool._executor is not None

    def test_pool_submit_default_handler(self) -> None:
        with WorkerPool(max_workers=2, use_threads=True) as pool:
            result = pool.submit(TaskAssignment(task_id="t1", task_type="echo", payload={"msg": "hi"}))
            assert result.success is True
            assert result.data is not None

    def test_pool_submit_custom_handler(self) -> None:
        with WorkerPool(max_workers=2, use_threads=True) as pool:
            pool.register_handler("double", lambda p: p["x"] * 2)
            result = pool.submit(TaskAssignment(task_id="t1", task_type="double", payload={"x": 5}))
            assert result.success is True
            assert result.data == 10

    def test_pool_submit_error(self) -> None:
        with WorkerPool(max_workers=2, use_threads=True) as pool:
            pool.register_handler("fail", lambda p: 1 / 0)
            result = pool.submit(TaskAssignment(task_id="t1", task_type="fail", payload={}))
            assert result.success is False
            assert "division by zero" in result.error or "divide by zero" in result.error
