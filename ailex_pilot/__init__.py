"""AILEX Pilot v5.0.0 — public API."""
from .pipeline          import PilotPipeline
from .context           import ProjectReader, ProjectContext
from .executor          import CodeExecutor, ExecutionResult
from .conversation      import ConversationMemory, Session, Message
from .git_integration   import GitIntegration, GitStatus, CommitResult, PRResult
from .cost_control      import CostController, BudgetStatus
from .monitor           import Monitor
from .retry             import RetryManager, RetryConfig, retry
from .secrets           import SecretsManager
from .webhooks          import WebhookServer, WebhookEvent
from .evaluator         import Evaluator, BenchmarkSuite
from .cache             import SmartCache
from .multi_hypothesis  import MultiHypothesisEngine, MultiHypothesisResult, Hypothesis
from .feedback          import FeedbackLoop, FeedbackRecord
from .docs              import DocumentAnalyzer, DocumentContent
from .database          import DatabaseAssistant, QueryResult
from .auto_pr_reviewer  import AutoPRReviewer, PRReview
from .task_queue        import TaskQueue, QueueTask
from .planner           import LongHorizonPlanner, Plan, PlanStep
from .ast_analyzer      import ASTAnalyzer, ASTReport, CodeSymbol
from .code_search       import SemanticCodeSearch, SearchResult
from .security          import SecurityScanner, SecurityReport, SecurityFinding
from .self_improve      import SelfImprover, ABTestingEngine, ImprovementSuggestion
from .streaming         import StreamingOutput
from .tdd_loop          import TDDLoop, TDDResult, TDDIteration
from .memory_compress   import MemoryCompressor
from .plugins           import PluginManager, Plugin, PluginAgent
from .proactive         import ProactiveMonitor, ProactiveSuggestion
from .notify            import Notifier
from .code_quality      import CodeQualityGate, QualityResult
from .knowledge_base    import KnowledgeBase, KBEntry
from .telemetry         import AILEXTelemetry
from .finetune_export   import FineTuneExporter, FineTuneDataset
from .graph_workflow    import WorkflowGraph, GraphState, GraphNode, build_ailex_workflow
from .human_loop        import HumanInTheLoop, CheckpointDecision, GuardedPipeline
from .context_directives import DirectiveProcessor
from .config_schema     import ConfigLoader, AILEXConfig
from .role_handoff      import RoleHandoffManager, HandoffContract, HandoffResult
from .action_blocks     import (ActionBlock, BlockWorkflow, ReadFileBlock, WriteFileBlock,
                                 FetchURLBlock, AskAILEXBlock, GenerateCodeBlock,
                                 RunCodeBlock, GitCommitBlock, SecurityScanBlock)
from .prompt_templates  import PromptLibrary, PromptTemplate
from .file_watcher      import FileWatcher, FileEvent, AILEXFileWatcher
from .complexity        import ComplexityAnalyzer, ProjectMetrics, FileMetrics, FunctionMetrics
from .provider_registry import ProviderRegistry, Provider
from .interactive_shell import AILEXShell
from .tui               import run_tui
from .scheduler         import JobScheduler, ScheduledJob, build_ailex_scheduler
from .fuzzy_search      import FuzzyMatcher, AILEXFuzzySearch, FuzzyMatch
from .dependency_graph  import DependencyAnalyzer, DependencyReport, Module

__version__ = "5.0.0"
__all__ = [
    "PilotPipeline", "ProjectReader", "ProjectContext",
    "CodeExecutor", "ExecutionResult",
    "ConversationMemory", "Session", "Message",
    "GitIntegration", "GitStatus", "CommitResult", "PRResult",
    "CostController", "BudgetStatus", "Monitor",
    "RetryManager", "RetryConfig", "retry",
    "SecretsManager", "WebhookServer", "WebhookEvent",
    "Evaluator", "BenchmarkSuite", "SmartCache",
    "MultiHypothesisEngine", "MultiHypothesisResult", "Hypothesis",
    "FeedbackLoop", "FeedbackRecord",
    "DocumentAnalyzer", "DocumentContent",
    "DatabaseAssistant", "QueryResult",
    "AutoPRReviewer", "PRReview",
    "TaskQueue", "QueueTask",
    "LongHorizonPlanner", "Plan", "PlanStep",
    "ASTAnalyzer", "ASTReport", "CodeSymbol",
    "SemanticCodeSearch", "SearchResult",
    "SecurityScanner", "SecurityReport", "SecurityFinding",
    "SelfImprover", "ABTestingEngine", "ImprovementSuggestion",
    "StreamingOutput", "TDDLoop", "TDDResult", "TDDIteration",
    "MemoryCompressor", "PluginManager", "Plugin", "PluginAgent",
    "ProactiveMonitor", "ProactiveSuggestion", "Notifier",
    "CodeQualityGate", "QualityResult",
    "KnowledgeBase", "KBEntry",
    "AILEXTelemetry", "FineTuneExporter", "FineTuneDataset",
    "WorkflowGraph", "GraphState", "GraphNode", "build_ailex_workflow",
    "HumanInTheLoop", "CheckpointDecision", "GuardedPipeline",
    "DirectiveProcessor",
    "ConfigLoader", "AILEXConfig",
    "RoleHandoffManager", "HandoffContract", "HandoffResult",
    "ActionBlock", "BlockWorkflow", "ReadFileBlock", "WriteFileBlock",
    "FetchURLBlock", "AskAILEXBlock", "GenerateCodeBlock",
    "RunCodeBlock", "GitCommitBlock", "SecurityScanBlock",
    "PromptLibrary", "PromptTemplate",
    "FileWatcher", "FileEvent", "AILEXFileWatcher",
    "ComplexityAnalyzer", "ProjectMetrics", "FileMetrics", "FunctionMetrics",
    "ProviderRegistry", "Provider",
    "AILEXShell", "run_tui",
    "JobScheduler", "ScheduledJob", "build_ailex_scheduler",
    "FuzzyMatcher", "AILEXFuzzySearch", "FuzzyMatch",
    "DependencyAnalyzer", "DependencyReport", "Module",
]

from .bmad_integration  import (BMADIntegration, BMADArtifact, BMADSprintStory,
                                  BMADProject, BMAD_PHASES, BMAD_AGENT_PERSONAS,
                                  get_bmad, bmad_run, bmad_artifact, bmad_stories)
from .gsd2_integration   import GSD2Integration, GSD2Spec, GSD2Task, ContextRotDetector, StuckLoopDetector, GSD2_AGENT_PERSONAS, GSD2_PROVIDER_CONFIGS
from .unified_pipeline   import UnifiedPipeline, UnifiedResult

from .autonomous_loop        import AutonomousLoop, AutonomousAction
from .swarm                  import SwarmIntelligence, SwarmResult, SwarmAgent
from .predictive_intelligence import PredictiveIntelligence, Prediction
from .recursive_improvement  import RecursiveImprovement, ImprovementHypothesis, RecursiveImprovementCycle
from .universal_validator    import UniversalValidator, ValidationReport, ValidationCheck
from .knowledge_synthesis    import KnowledgeSynthesis, SynthesisedPattern
from .x100_modules           import (APIAutoDiscovery, APIIntegration, VisualRegressionTester,
                                      VisualDiff, PerformanceLoop, PerformanceProfile)

# ── AILEX v6 Improvements (P1-P8) ─────────────────────────────────────────────
from .structured_output      import (StructuredAgentCall, AgentOutput, SynthesisOutput,
                                      AGENT_TOOL_SCHEMA, ORION_TOOL_SCHEMA)
from .agent_quality_gate     import (AgentQualityGate, QualityReport, QualityGuardedCall)
from .smart_cache_v2         import (SmartCacheV2, get_cache, cached as cache_result, TTL)
from .ailex_logger           import (get_logger, new_trace, Trace, tail_logs, AILEXLogger)
from .context_compressor     import (ContextCompressor, CompressionResult, CompressedSummary)
from .multi_provider         import (MultiProvider, RateLimitTracker, PROVIDER_MODELS)
from .web_researcher         import (WebResearcher, ResearchResult, get_researcher, quick_research)
from .knowledge_updater      import (KnowledgeUpdater, UpdateReport, auto_update_on_activation,
                                      get_updater, RESEARCH_AGENDA)
from .research_scheduler     import (ResearchScheduler, get_scheduler, activate_research,
                                      research as web_search, inject_context)
from .github_researcher      import (GitHubResearcher, GitHubRepo, TechPattern,
                                      get_gh, github_search, github_trending)
from .auto_improve           import (AutoImprover, ImprovementReport, Improvement,
                                      get_improver, auto_improve_on_activation)
from .observability          import (observe, tracer, metrics, health, Tracer,
                                      MetricsStore, HealthCheck, EventBus, Span)
from .pipeline_v2            import (InstrumentedPipeline, PipelineResult,
                                      get_pipeline, activate_instrumentation)
from .metrics_dashboard      import render_dashboard
from .provider_health        import (ProviderHealth, ProviderStatus, HealthReport,
                                      FailoverResult)
from .backend_generator      import (BackendGenerator, BackendProject, ProjectFile,
                                      bastian_generate, get_backend_generator)
from .wave_orchestrator      import (WaveOrchestrator, Wave, WaveResult,
                                      OrchestrationResult, DOMAIN_WAVES,
                                      get_orchestrator, wave_run, wave_context)
from .multiwave_performer    import (MultiWavePerformer, AgentSpec, PerformerResult,
                                      PerformerWave, AGENT_REGISTRY, REGISTRY_INDEX,
                                      get_mwp, mwp_run)
from .mary_2026              import (Mary2026, MaryResearchResult, LLM_LANDSCAPE_2026,
                                      AI_TECHNIQUES_2026, MARY_2026_RESEARCH_AGENDA,
                                      get_mary, enrich_mary, mary_research,
                                      mary_compare_models)
from .aiox_maximizer         import (AIoXMaximizer, MaximizerResult,
                                      get_maximizer, aiox_run, aiox_status)
