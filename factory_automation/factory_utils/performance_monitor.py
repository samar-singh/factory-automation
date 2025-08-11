"""Performance monitoring for Factory Automation System"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance measurement"""

    operation: str
    duration: float
    timestamp: datetime
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class PerformanceMonitor:
    """Monitor and track system performance metrics"""

    def __init__(self, window_size: int = 1000):
        """Initialize performance monitor

        Args:
            window_size: Number of recent metrics to keep in memory
        """
        self.window_size = window_size
        self.metrics: List[PerformanceMetric] = []
        self.operation_stats: Dict[str, List[float]] = defaultdict(list)
        self.start_times: Dict[str, float] = {}

        # Thresholds for performance alerts
        self.thresholds = {
            "search": 2.0,  # seconds
            "ingestion": 5.0,
            "image_processing": 3.0,
            "embedding_generation": 1.0,
            "reranking": 0.5,
            "database_query": 0.5,
        }

        logger.info("Performance monitor initialized")

    def start_operation(self, operation: str, metadata: Optional[Dict] = None) -> str:
        """Start timing an operation

        Args:
            operation: Name of the operation
            metadata: Optional metadata about the operation

        Returns:
            Operation ID for tracking
        """
        op_id = f"{operation}_{time.time()}"
        self.start_times[op_id] = time.time()

        if metadata:
            logger.debug(f"Started {operation}: {metadata}")

        return op_id

    def end_operation(
        self, op_id: str, success: bool = True, metadata: Optional[Dict] = None
    ) -> float:
        """End timing an operation

        Args:
            op_id: Operation ID from start_operation
            success: Whether operation succeeded
            metadata: Optional additional metadata

        Returns:
            Duration in seconds
        """
        if op_id not in self.start_times:
            logger.warning(f"Unknown operation ID: {op_id}")
            return 0.0

        duration = time.time() - self.start_times[op_id]
        operation = op_id.rsplit("_", 1)[0]

        # Create metric
        metric = PerformanceMetric(
            operation=operation,
            duration=duration,
            timestamp=datetime.now(),
            success=success,
            metadata=metadata or {},
        )

        # Add to metrics
        self.metrics.append(metric)
        if len(self.metrics) > self.window_size:
            self.metrics.pop(0)

        # Update operation stats
        if success:
            self.operation_stats[operation].append(duration)
            if len(self.operation_stats[operation]) > self.window_size:
                self.operation_stats[operation].pop(0)

        # Check threshold
        threshold = self.thresholds.get(operation)
        if threshold and duration > threshold:
            logger.warning(
                f"Performance alert: {operation} took {duration:.2f}s "
                f"(threshold: {threshold}s)"
            )

        # Clean up
        del self.start_times[op_id]

        logger.debug(f"Completed {operation} in {duration:.3f}s")
        return duration

    def measure(self, operation: str):
        """Context manager for measuring operation duration

        Usage:
            with monitor.measure("search"):
                # perform search
        """

        class MeasureContext:
            def __init__(self, monitor, operation):
                self.monitor = monitor
                self.operation = operation
                self.op_id = None

            def __enter__(self):
                self.op_id = self.monitor.start_operation(self.operation)
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                success = exc_type is None
                self.monitor.end_operation(self.op_id, success=success)

        return MeasureContext(self, operation)

    def get_statistics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics

        Args:
            operation: Specific operation to get stats for, or None for all

        Returns:
            Dictionary of statistics
        """
        if operation:
            durations = self.operation_stats.get(operation, [])
            if not durations:
                return {"error": f"No data for operation: {operation}"}

            return self._calculate_stats(operation, durations)

        # Get stats for all operations
        all_stats = {}
        for op, durations in self.operation_stats.items():
            if durations:
                all_stats[op] = self._calculate_stats(op, durations)

        # Add overall system stats
        all_durations = [m.duration for m in self.metrics if m.success]
        if all_durations:
            all_stats["overall"] = self._calculate_stats("overall", all_durations)

        # Add success rate
        total = len(self.metrics)
        successful = sum(1 for m in self.metrics if m.success)
        all_stats["success_rate"] = (successful / total * 100) if total > 0 else 100

        return all_stats

    def _calculate_stats(self, name: str, durations: List[float]) -> Dict[str, Any]:
        """Calculate statistics for a list of durations"""
        arr = np.array(durations)

        return {
            "name": name,
            "count": len(durations),
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "recent_10_avg": (
                float(np.mean(arr[-10:])) if len(arr) >= 10 else float(np.mean(arr))
            ),
        }

    def get_recent_metrics(
        self, minutes: int = 5, operation: Optional[str] = None
    ) -> List[PerformanceMetric]:
        """Get recent metrics within time window

        Args:
            minutes: Time window in minutes
            operation: Filter by operation name

        Returns:
            List of recent metrics
        """
        cutoff = datetime.now() - timedelta(minutes=minutes)

        metrics = [m for m in self.metrics if m.timestamp >= cutoff]

        if operation:
            metrics = [m for m in metrics if m.operation == operation]

        return metrics

    def get_slow_operations(self, top_n: int = 10) -> List[PerformanceMetric]:
        """Get slowest operations

        Args:
            top_n: Number of operations to return

        Returns:
            List of slowest operations
        """
        sorted_metrics = sorted(self.metrics, key=lambda m: m.duration, reverse=True)

        return sorted_metrics[:top_n]

    def get_performance_report(self) -> str:
        """Generate a performance report

        Returns:
            Formatted performance report string
        """
        stats = self.get_statistics()

        report = []
        report.append("=" * 60)
        report.append("PERFORMANCE REPORT")
        report.append("=" * 60)

        # Overall stats
        if "overall" in stats:
            overall = stats["overall"]
            report.append("\nOverall Performance:")
            report.append(f"  Operations: {overall['count']}")
            report.append(f"  Avg Duration: {overall['mean']:.3f}s")
            report.append(f"  Median: {overall['median']:.3f}s")
            report.append(f"  95th Percentile: {overall['p95']:.3f}s")
            report.append(f"  Success Rate: {stats.get('success_rate', 100):.1f}%")

        # Per-operation stats
        report.append("\nOperation Breakdown:")
        for op_name, op_stats in stats.items():
            if op_name in ["overall", "success_rate"]:
                continue

            threshold = self.thresholds.get(op_name)
            status = "🟢" if not threshold or op_stats["mean"] <= threshold else "🔴"

            report.append(f"\n  {status} {op_name}:")
            report.append(f"    Count: {op_stats['count']}")
            report.append(f"    Avg: {op_stats['mean']:.3f}s")
            report.append(f"    Median: {op_stats['median']:.3f}s")
            report.append(f"    Range: {op_stats['min']:.3f}s - {op_stats['max']:.3f}s")

            if threshold:
                report.append(f"    Threshold: {threshold}s")
                over_threshold = sum(
                    1 for d in self.operation_stats[op_name] if d > threshold
                )
                if over_threshold:
                    pct = over_threshold / len(self.operation_stats[op_name]) * 100
                    report.append(f"    Over threshold: {over_threshold} ({pct:.1f}%)")

        # Slow operations
        slow_ops = self.get_slow_operations(5)
        if slow_ops:
            report.append("\nSlowest Recent Operations:")
            for op in slow_ops:
                report.append(
                    f"  - {op.operation}: {op.duration:.3f}s "
                    f"({op.timestamp.strftime('%H:%M:%S')})"
                )

        # Recent trend
        recent = self.get_recent_metrics(minutes=5)
        if recent:
            recent_avg = np.mean([m.duration for m in recent])
            report.append("\nLast 5 minutes:")
            report.append(f"  Operations: {len(recent)}")
            report.append(f"  Avg Duration: {recent_avg:.3f}s")

        report.append("\n" + "=" * 60)

        return "\n".join(report)

    def reset(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.operation_stats.clear()
        self.start_times.clear()
        logger.info("Performance monitor reset")


# Global singleton instance
_monitor = None


def get_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def measure_performance(operation: str):
    """Decorator for measuring function performance

    Usage:
        @measure_performance("database_query")
        def query_database():
            # perform query
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            monitor = get_monitor()
            op_id = monitor.start_operation(operation)
            try:
                result = func(*args, **kwargs)
                monitor.end_operation(op_id, success=True)
                return result
            except Exception:
                monitor.end_operation(op_id, success=False)
                raise

        return wrapper

    return decorator
