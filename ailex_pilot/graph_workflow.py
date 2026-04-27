"""
AILEX Pilot — graph_workflow.py
Directed graph state machine for pipeline execution.
Inspired by LangGraph's pattern: explicit nodes, edges, resumable state.
100% original AILEX implementation.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class GraphNode:
    id:       str
    name:     str
    fn:       Callable           # async or sync handler
    edges:    List[str]          # next node IDs (or conditional)
    retries:  int = 2


@dataclass
class GraphState:
    run_id:     str
    graph_id:   str
    current:    str              # current node id
    visited:    List[str]
    data:       Dict             # shared mutable state across nodes
    status:     str = "running"  # running | paused | done | failed
    checkpoint: Optional[str] = None
    ts:         float = field(default_factory=time.time)


class WorkflowGraph:
    """
    Directed graph workflow for AILEX pipelines.
    Each node = one step. Edges = transitions. State is checkpointed after each node.

    Pattern from LangGraph: explicit state representation → debuggable,
    resumable, inspectable. AILEX original implementation.
    """

    CHECKPOINT_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".ailex_graph_checkpoints"
    )

    def __init__(self, graph_id: str = "default"):
        self.graph_id  = graph_id
        self.nodes:    Dict[str, GraphNode] = {}
        self.entry:    Optional[str]        = None
        self._cond_edges: Dict[str, Callable] = {}
        os.makedirs(self.CHECKPOINT_DIR, exist_ok=True)

    # ── Builder API ───────────────────────────────────────────────────────────

    def node(self, name: str, fn: Callable, retries: int = 2) -> "WorkflowGraph":
        """Register a node."""
        nid = name.lower().replace(" ", "_")
        self.nodes[nid] = GraphNode(id=nid, name=name, fn=fn, edges=[], retries=retries)
        if self.entry is None:
            self.entry = nid
        return self

    def edge(self, from_id: str, to_id: str) -> "WorkflowGraph":
        """Add a directed edge."""
        if from_id in self.nodes:
            self.nodes[from_id].edges.append(to_id)
        return self

    def conditional_edge(self, from_id: str, condition: Callable) -> "WorkflowGraph":
        """Add a conditional edge: condition(state) → next_node_id."""
        self._cond_edges[from_id] = condition
        return self

    def set_entry(self, node_id: str) -> "WorkflowGraph":
        self.entry = node_id
        return self

    # ── Execution ─────────────────────────────────────────────────────────────

    def run(self, initial_data: Dict, run_id: Optional[str] = None) -> GraphState:
        """Execute graph from entry node, return final state."""
        run_id = run_id or str(uuid.uuid4())[:8]
        state  = GraphState(
            run_id=run_id, graph_id=self.graph_id,
            current=self.entry or "", visited=[],
            data=dict(initial_data),
        )
        return self._execute(state)

    def resume(self, run_id: str) -> Optional[GraphState]:
        """Resume a paused/checkpointed run."""
        state = self._load_checkpoint(run_id)
        if state and state.status == "paused":
            state.status = "running"
            return self._execute(state)
        return state

    def _execute(self, state: GraphState) -> GraphState:
        max_steps = len(self.nodes) * 3  # cycle protection
        step      = 0

        while state.current and state.status == "running" and step < max_steps:
            node = self.nodes.get(state.current)
            if not node:
                state.status = "failed"
                state.data["error"] = f"Node not found: {state.current}"
                break

            # Execute node with retries
            success = False
            for attempt in range(node.retries + 1):
                try:
                    result = node.fn(state.data)
                    if hasattr(result, "__await__"):
                        import asyncio
                        result = asyncio.run(result) if not asyncio.get_event_loop().is_running() else result
                    if isinstance(result, dict):
                        state.data.update(result)
                    success = True
                    break
                except Exception as e:
                    state.data[f"_error_{node.id}_attempt_{attempt}"] = str(e)
                    if attempt == node.retries:
                        state.status = "failed"
                        state.data["error"] = str(e)

            if not success:
                break

            state.visited.append(state.current)
            self._save_checkpoint(state)

            # Check if paused by node (human-in-the-loop signal)
            if state.data.get("_pause"):
                state.status = "paused"
                state.data.pop("_pause", None)
                break

            # Determine next node
            next_node = self._next(state)
            state.current = next_node or ""
            step += 1

        if state.current == "" and state.status == "running":
            state.status = "done"

        self._save_checkpoint(state)
        return state

    def _next(self, state: GraphState) -> Optional[str]:
        """Resolve next node: conditional or first edge."""
        nid = state.current
        if nid in self._cond_edges:
            return self._cond_edges[nid](state.data)
        node = self.nodes.get(nid)
        return node.edges[0] if node and node.edges else None

    # ── Checkpointing ─────────────────────────────────────────────────────────

    def _save_checkpoint(self, state: GraphState) -> None:
        path = os.path.join(self.CHECKPOINT_DIR, f"{state.run_id}.json")
        with open(path, "w") as f:
            json.dump({
                "run_id":   state.run_id,
                "graph_id": state.graph_id,
                "current":  state.current,
                "visited":  state.visited,
                "data":     {k: str(v)[:500] for k, v in state.data.items()},
                "status":   state.status,
                "ts":       state.ts,
            }, f, indent=2)

    def _load_checkpoint(self, run_id: str) -> Optional[GraphState]:
        path = os.path.join(self.CHECKPOINT_DIR, f"{run_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            d = json.load(f)
        return GraphState(**d)

    def list_runs(self) -> List[Dict]:
        runs = []
        for f in os.listdir(self.CHECKPOINT_DIR):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.CHECKPOINT_DIR, f)) as fp:
                        runs.append(json.load(fp))
                except Exception:
                    pass
        return sorted(runs, key=lambda x: x.get("ts", 0), reverse=True)

    def visualize(self) -> str:
        """ASCII representation of the graph."""
        lines = [f"Graph: {self.graph_id}", f"Entry: {self.entry}", ""]
        for nid, node in self.nodes.items():
            prefix = "→ " if nid == self.entry else "  "
            cond   = " [conditional]" if nid in self._cond_edges else ""
            lines.append(f"{prefix}[{nid}] {node.name}{cond}")
            for edge in node.edges:
                lines.append(f"    └─► {edge}")
        return "\n".join(lines)


# ── Pre-built AILEX workflow ──────────────────────────────────────────────────

def build_ailex_workflow(pipeline: Any) -> WorkflowGraph:
    """Standard AILEX pipeline as a resumable graph."""
    g = WorkflowGraph("ailex_standard")

    def load_context(data: Dict) -> Dict:
        if hasattr(pipeline, "_project_ctx") and pipeline._project_ctx is None:
            pipeline.load_project()
        return {"context_loaded": True}

    def run_agents(data: Dict) -> Dict:
        request = data.get("request", "")
        domain  = data.get("domain")
        p, h, coda = pipeline._ailex.process(
            request, override_domain=domain, output_format="full"
        ) if pipeline._ailex else (None, None, None)
        return {
            "report":     pipeline._ailex.report(p, h, coda) if coda else "demo",
            "domain":     coda.domain if coda else domain,
            "confidence": coda.final_confidence if coda else 0.0,
            "loops":      coda.loops_run if coda else 0,
        }

    def human_review(data: Dict) -> Dict:
        # Signal pause if confidence < threshold
        if data.get("confidence", 1.0) < 0.85:
            data["_pause"] = True
            data["pause_reason"] = f"Low confidence: {data.get('confidence', 0):.0%}"
        return data

    def execute_code(data: Dict) -> Dict:
        report = data.get("report", "")
        if report and pipeline.executor:
            results = pipeline.executor.extract_and_run(report)
            return {"exec_results": [pipeline.executor.format_result(r) for r in results]}
        return {}

    def commit(data: Dict) -> Dict:
        if data.get("auto_commit") and pipeline.git.is_git_repo():
            r = pipeline.git.commit_ailex(f"AILEX: {data.get('request','')[:60]}")
            return {"committed": r.success, "sha": r.sha}
        return {}

    (g.node("load_context", load_context)
      .node("run_agents",   run_agents)
      .node("human_review", human_review)
      .node("execute_code", execute_code)
      .node("commit",       commit)
      .edge("load_context", "run_agents")
      .edge("run_agents",   "human_review")
      .conditional_edge("human_review",
                        lambda d: "execute_code" if not d.get("_pause") else None)
      .edge("execute_code", "commit"))

    return g
