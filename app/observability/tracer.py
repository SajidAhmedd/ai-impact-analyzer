"""
Execution tracing for workflow observability.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
import structlog

logger = structlog.get_logger()


@dataclass
class TraceStep:
    """A single step in the execution trace."""
    node: str
    timestamp: str
    latency_ms: float
    model: Optional[str] = None
    prompt_version: str = "v1"
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    token_estimate: Optional[int] = None
    success: bool = True
    error: Optional[str] = None


@dataclass
class ExecutionTrace:
    """Complete execution trace for an analysis run."""
    trace_id: str
    change_request: str
    started_at: str
    completed_at: Optional[str] = None
    steps: List[TraceStep] = field(default_factory=list)
    retrieved_docs_count: int = 0
    total_latency_ms: float = 0
    success: bool = True
    error: Optional[str] = None

    def add_step(self, step: TraceStep) -> None:
        self.steps.append(step)
        self.total_latency_ms += step.latency_ms

    def complete(self, success: bool = True, error: str = None) -> None:
        self.completed_at = datetime.utcnow().isoformat()
        self.success = success
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class ExecutionTracer:
    """Manages execution traces for analysis runs."""

    def __init__(self, persist_dir: str = "logs/traces"):
        self.traces: Dict[str, ExecutionTrace] = {}
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

    def start_trace(self, change_request: str) -> ExecutionTrace:
        trace_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")

        trace = ExecutionTrace(
            trace_id=trace_id,
            change_request=change_request[:200],
            started_at=datetime.utcnow().isoformat(),
        )

        self.traces[trace_id] = trace
        logger.info("Trace started", trace_id=trace_id)

        return trace

    def trace_step(
        self,
        trace_id: str,
        node: str,
        latency_ms: float,
        model: str = None,
        prompt_version: str = "v1",
        input_summary: str = None,
        output_summary: str = None,
        token_estimate: int = None,
        success: bool = True,
        error: str = None,
    ) -> None:
        if trace_id not in self.traces:
            logger.warning("Trace not found", trace_id=trace_id)
            return

        step = TraceStep(
            node=node,
            timestamp=datetime.utcnow().isoformat(),
            latency_ms=latency_ms,
            model=model,
            prompt_version=prompt_version,
            input_summary=input_summary[:100] if input_summary else None,
            output_summary=output_summary[:100] if output_summary else None,
            token_estimate=token_estimate,
            success=success,
            error=error,
        )

        self.traces[trace_id].add_step(step)
        logger.info("Trace step recorded", trace_id=trace_id, node=node)

    def complete_trace(
        self,
        trace_id: str,
        success: bool = True,
        error: str = None,
        docs_count: int = 0
    ) -> Optional[ExecutionTrace]:
        if trace_id not in self.traces:
            return None

        trace = self.traces[trace_id]
        trace.retrieved_docs_count = docs_count
        trace.complete(success=success, error=error)

        logger.info("Trace completed", trace_id=trace_id, total_latency_ms=trace.total_latency_ms)

        return trace

    def save_trace(self, trace_id: str) -> Optional[Path]:
        if trace_id not in self.traces:
            return None

        trace = self.traces[trace_id]
        file_path = self.persist_dir / f"{trace_id}.json"
        file_path.write_text(trace.to_json(), encoding="utf-8")

        return file_path

    def get_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        return self.traces.get(trace_id)

    def list_traces(self, limit: int = 10) -> List[Dict]:
        traces = sorted(
            self.traces.values(),
            key=lambda t: t.started_at,
            reverse=True
        )[:limit]

        return [
            {
                "trace_id": t.trace_id,
                "started_at": t.started_at,
                "total_latency_ms": t.total_latency_ms,
                "success": t.success,
                "steps": len(t.steps),
            }
            for t in traces
        ]


# Global tracer instance
_tracer: Optional[ExecutionTracer] = None


def get_tracer() -> ExecutionTracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = ExecutionTracer()
    return _tracer