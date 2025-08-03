"""Trace Monitoring Utilities for Agent Actions"""

import json
import logging
from datetime import datetime
from typing import Any, Dict
from collections import defaultdict

logger = logging.getLogger(__name__)


class TraceMonitor:
    """Monitor and visualize agent traces"""

    def __init__(self):
        self.traces = []
        self.current_trace = None
        self.tool_stats = defaultdict(int)
        self.decision_history = []

    def start_trace(self, trace_name: str, metadata: Dict[str, Any] = None):
        """Start a new trace"""
        self.current_trace = {
            "trace_name": trace_name,
            "start_time": datetime.now().isoformat(),
            "metadata": metadata or {},
            "tool_calls": [],
            "decisions": [],
            "errors": [],
            "status": "running",
        }
        logger.info(f"🔍 Trace started: {trace_name}")

    def add_tool_call(self, tool_name: str, args: Dict[str, Any], result: Any):
        """Add a tool call to current trace"""
        if not self.current_trace:
            return

        tool_call = {
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "args": args,
            "result": (
                result
                if isinstance(result, (dict, list, str, int, float))
                else str(result)
            ),
            "duration_ms": None,  # Could calculate if we track start/end
        }

        self.current_trace["tool_calls"].append(tool_call)
        self.tool_stats[tool_name] += 1

        # Log tool usage
        logger.info(f"  🔧 Tool: {tool_name}")
        logger.debug(f"     Args: {json.dumps(args, indent=2)}")

    def add_decision(self, decision_type: str, details: Dict[str, Any]):
        """Add a decision point to trace"""
        if not self.current_trace:
            return

        decision = {
            "type": decision_type,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        }

        self.current_trace["decisions"].append(decision)
        self.decision_history.append(decision)

        logger.info(f"  ✅ Decision: {decision_type} - {details.get('action', 'N/A')}")

    def add_error(self, error: str, context: Dict[str, Any] = None):
        """Add an error to trace"""
        if not self.current_trace:
            return

        error_info = {
            "error": error,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
        }

        self.current_trace["errors"].append(error_info)
        logger.error(f"  ❌ Error in trace: {error}")

    def end_trace(self, status: str = "completed", summary: str = None):
        """End current trace"""
        if not self.current_trace:
            return

        self.current_trace["end_time"] = datetime.now().isoformat()
        self.current_trace["status"] = status
        self.current_trace["summary"] = summary

        # Calculate duration
        start = datetime.fromisoformat(self.current_trace["start_time"])
        end = datetime.fromisoformat(self.current_trace["end_time"])
        self.current_trace["duration_seconds"] = (end - start).total_seconds()

        # Store trace
        self.traces.append(self.current_trace)

        # Log summary
        logger.info(f"🏁 Trace completed: {self.current_trace['trace_name']}")
        logger.info(f"   Duration: {self.current_trace['duration_seconds']:.2f}s")
        logger.info(f"   Tools used: {len(self.current_trace['tool_calls'])}")
        logger.info(f"   Status: {status}")

        self.current_trace = None

    def get_trace_summary(self, trace_name: str = None) -> Dict[str, Any]:
        """Get summary of a specific trace or all traces"""
        if trace_name:
            trace = next(
                (t for t in self.traces if t["trace_name"] == trace_name), None
            )
            if trace:
                return self._summarize_trace(trace)
            return {"error": f"Trace '{trace_name}' not found"}

        # Summarize all traces
        return {
            "total_traces": len(self.traces),
            "tool_usage": dict(self.tool_stats),
            "recent_traces": [self._summarize_trace(t) for t in self.traces[-5:]],
            "decision_count": len(self.decision_history),
            "error_count": sum(len(t.get("errors", [])) for t in self.traces),
        }

    def _summarize_trace(self, trace: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary of a single trace"""
        tool_sequence = [tc["tool"] for tc in trace.get("tool_calls", [])]

        return {
            "name": trace["trace_name"],
            "status": trace["status"],
            "duration": trace.get("duration_seconds", 0),
            "tool_count": len(trace.get("tool_calls", [])),
            "tool_sequence": tool_sequence,
            "decisions": len(trace.get("decisions", [])),
            "errors": len(trace.get("errors", [])),
            "summary": trace.get("summary", "No summary"),
        }

    def visualize_trace(self, trace_name: str) -> str:
        """Create visual representation of trace"""
        trace = next((t for t in self.traces if t["trace_name"] == trace_name), None)
        if not trace:
            return f"Trace '{trace_name}' not found"

        output = [f"\n📊 TRACE: {trace_name}"]
        output.append(f"⏱️  Duration: {trace.get('duration_seconds', 0):.2f}s")
        output.append(f"📅 Started: {trace['start_time']}")
        output.append("\n🔄 Tool Call Sequence:")

        for i, tool_call in enumerate(trace.get("tool_calls", []), 1):
            output.append(f"\n{i}. {tool_call['tool']}")
            output.append(f"   Args: {json.dumps(tool_call['args'], indent=6)}")
            result_str = (
                json.dumps(tool_call["result"], indent=6)
                if isinstance(tool_call["result"], (dict, list))
                else str(tool_call["result"])
            )
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            output.append(f"   Result: {result_str}")

        if trace.get("decisions"):
            output.append("\n🎯 Decisions Made:")
            for decision in trace["decisions"]:
                output.append(f"   - {decision['type']}: {decision['details']}")

        if trace.get("errors"):
            output.append("\n⚠️  Errors:")
            for error in trace["errors"]:
                output.append(f"   - {error['error']}")

        output.append(f"\n📝 Summary: {trace.get('summary', 'No summary')}")

        return "\n".join(output)

    def get_tool_analytics(self) -> Dict[str, Any]:
        """Get analytics on tool usage"""
        total_calls = sum(self.tool_stats.values())

        analytics = {
            "total_tool_calls": total_calls,
            "unique_tools": len(self.tool_stats),
            "tool_frequency": dict(self.tool_stats),
            "most_used_tool": (
                max(self.tool_stats.items(), key=lambda x: x[1])
                if self.tool_stats
                else None
            ),
            "average_tools_per_trace": (
                total_calls / len(self.traces) if self.traces else 0
            ),
        }

        # Tool combinations
        tool_pairs = defaultdict(int)
        for trace in self.traces:
            tools = [tc["tool"] for tc in trace.get("tool_calls", [])]
            for i in range(len(tools) - 1):
                pair = f"{tools[i]} → {tools[i+1]}"
                tool_pairs[pair] += 1

        analytics["common_tool_sequences"] = dict(
            sorted(tool_pairs.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        return analytics

    def export_traces(self, filename: str = None) -> str:
        """Export traces to file"""
        if not filename:
            filename = f"traces_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        export_data = {
            "export_time": datetime.now().isoformat(),
            "traces": self.traces,
            "analytics": self.get_tool_analytics(),
        }

        with open(filename, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Traces exported to {filename}")
        return filename


# Global trace monitor instance
trace_monitor = TraceMonitor()


def with_trace_monitoring(trace_name: str):
    """Decorator to add trace monitoring to functions"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            trace_monitor.start_trace(
                trace_name, {"args": str(args), "kwargs": str(kwargs)}
            )
            try:
                result = await func(*args, **kwargs)
                trace_monitor.end_trace("completed", str(result)[:100])
                return result
            except Exception as e:
                trace_monitor.add_error(str(e))
                trace_monitor.end_trace("failed", f"Error: {str(e)}")
                raise

        return wrapper

    return decorator
