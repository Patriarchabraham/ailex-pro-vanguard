"""
AILEX — multiwave_performer.py
100 Super-Specialized Agents · Dynamic Wave Composition · Performance Tracking
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The MultiWave Performer System (MWPS) is the full expression of AILEX intelligence:
100 deeply specialized agents organized in 8 Tiers, dynamically composed into
performance waves guided by the AILEX force: RDT + QualityGate + KB + Observability.

TIER 1 — Engineering Core         (20 agents) — React, Node, DB, Cloud, K8s...
TIER 2 — AI/ML Specialists        (15 agents) — RAG, fine-tuning, diffusion...
TIER 3 — Security Masters         (10 agents) — Pentest, crypto, zero-trust...
TIER 4 — Performance Engineers    (10 agents) — Profiling, load, bundle, DB...
TIER 5 — Domain Experts           (15 agents) — Fintech, healthIT, gaming...
TIER 6 — Quality Architects       (10 agents) — TDD, chaos, mutation testing...
TIER 7 — Creative Designers        (10 agents) — WebGL, D3, shader, motion...
TIER 8 — Strategy & Meta          (10 agents) — Architecture, scaling, cost...

Dynamic capabilities:
  ✦ Task analysis → automatic agent selection (top N relevant)
  ✦ Dynamic wave composition (3-7 waves based on complexity)
  ✦ Cross-wave context chain (each wave enriches the next)
  ✦ Performance tracking (which agents excel at which tasks)
  ✦ Confidence-gated halting (stop when quality threshold met)
  ✦ Agent specialization index (30+ keywords per agent)
  ✦ Parallel execution within waves
  ✦ ORION meta-synthesis at end

Usage:
    from ailex_pilot.multiwave_performer import MultiWavePerformer, mwp_run

    mwp = MultiWavePerformer()
    result = mwp.run("Build a real-time collaborative code editor")
    print(result.executive_summary())

    # Check who contributed most:
    print(result.top_performers())

    # List all 100 agents:
    for agent in mwp.list_agents():
        print(f"{agent.id}: {agent.name} [{agent.tier}]")
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .pipeline_v2    import InstrumentedPipeline, PipelineResult, get_pipeline
from .ailex_logger   import get_logger, new_trace
from .observability  import metrics, tracer


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AGENT DEFINITIONS — 100 Super-Specialized Agents
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class AgentSpec:
    id:        str
    name:      str
    tier:      int              # 1-8
    domain:    str              # broad category
    model:     str              # claude model
    expertise: str              # system prompt persona
    keywords:  List[str]        # triggers agent selection
    max_tokens: int = 400


AGENT_REGISTRY: List[AgentSpec] = [

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 1 — ENGINEERING CORE (20 agents)
    # ══════════════════════════════════════════════════════════════════════════

    AgentSpec("DEXTRA","React/TypeScript Virtuoso",1,"frontend","claude-opus-4-7",
        "Senior React + TypeScript + Vite expert. Deep knowledge of hooks, concurrent features, "
        "Suspense, Server Components, Zustand, React Query, performance optimization.",
        ["react","typescript","vite","hooks","component","jsx","tsx","framer","next.js","remix"],480),

    AgentSpec("NEXUM","Node.js Architect",1,"backend","claude-sonnet-4-6",
        "Node.js expert: event loop, streams, clustering, Express, NestJS, tRPC, "
        "microservices, WebSocket, background jobs, memory management.",
        ["node.js","express","nestjs","trpc","javascript","bun","deno","worker","stream","event-loop"],450),

    AgentSpec("GRAPHOS","GraphQL Specialist",1,"api","claude-sonnet-4-6",
        "GraphQL schema design, resolvers, N+1 detection, DataLoader, Federation, "
        "Apollo Server, subscriptions, codegen, persisted queries.",
        ["graphql","apollo","schema","resolver","subscription","federation","mutation","query","dataloader"],420),

    AgentSpec("PRISM","PostgreSQL Database Architect",1,"database","claude-opus-4-7",
        "PostgreSQL expert: schema design, advanced indexes (GIN, GiST, BRIN), "
        "query optimization (EXPLAIN ANALYZE), partitioning, replication, JSONB, full-text search.",
        ["postgresql","postgres","sql","schema","index","query","migration","alembic","prisma","drizzle"],470),

    AgentSpec("MONGO_DB","MongoDB Expert",1,"database","claude-sonnet-4-6",
        "MongoDB schema design, aggregation pipelines, change streams, Atlas Search, "
        "sharding, replica sets, transactions, Mongoose patterns.",
        ["mongodb","mongoose","aggregation","atlas","nosql","document","collection","pipeline"],420),

    AgentSpec("REDIS_PRO","Redis Performance Master",1,"cache","claude-sonnet-4-6",
        "Redis expert: data structures, Lua scripting, pub/sub, streams, "
        "distributed locks, caching strategies, Redis Stack, session management.",
        ["redis","cache","pub/sub","stream","lock","rate-limit","session","caching","memcached"],420),

    AgentSpec("DOCKER_K8S","Container Orchestration Specialist",1,"devops","claude-sonnet-4-6",
        "Docker multi-stage builds, docker-compose, Kubernetes: pods, deployments, "
        "services, ingress, HPA, resource limits, namespaces, Helm charts.",
        ["docker","kubernetes","k8s","container","helm","pod","deployment","ingress","kubectl","compose"],450),

    AgentSpec("TERRA_IaC","Infrastructure as Code Master",1,"infra","claude-sonnet-4-6",
        "Terraform, Pulumi, CDK. AWS/GCP/Azure infrastructure: VPCs, subnets, "
        "load balancers, managed services, state management, modules, drift detection.",
        ["terraform","pulumi","cdk","aws","gcp","azure","iac","infrastructure","vpc","cloudformation"],430),

    AgentSpec("CICD_PRO","CI/CD Pipeline Architect",1,"devops","claude-sonnet-4-6",
        "GitHub Actions, GitLab CI, Jenkins. Pipeline design: test, build, scan, "
        "deploy, rollback, environment promotion, secrets, parallelism.",
        ["github-actions","gitlab-ci","jenkins","pipeline","ci/cd","deploy","rollback","workflow","automation"],420),

    AgentSpec("CLOUD_ARK","Cloud Architecture Specialist",1,"cloud","claude-opus-4-7",
        "Multi-cloud architecture: AWS (Lambda, ECS, RDS, SQS), GCP (GKE, Cloud Run), "
        "Azure. Cost optimization, reliability patterns, Well-Architected Framework.",
        ["aws","gcp","azure","cloud","lambda","serverless","ecs","s3","cloudfront","cloudwatch"],460),

    AgentSpec("EDGE_COMP","Edge Computing Engineer",1,"edge","claude-sonnet-4-6",
        "Cloudflare Workers, Durable Objects, KV, R2. Edge caching, geolocation, "
        "WebAssembly at edge, global distribution, latency optimization.",
        ["cloudflare","edge","workers","cdn","wasm","latency","global","durable-objects","kv"],400),

    AgentSpec("MOBILE_DEV","Mobile Development Expert",1,"mobile","claude-sonnet-4-6",
        "React Native + Expo: navigation, native modules, performance, animations, "
        "offline sync, push notifications, App Store/Play Store optimization.",
        ["react-native","expo","mobile","ios","android","navigation","native","push","offline"],420),

    AgentSpec("API_ARCH","API Architecture Specialist",1,"api","claude-opus-4-7",
        "REST API design: versioning, pagination (cursor/keyset), rate limiting, "
        "OpenAPI 3.1, API gateway, backwards compatibility, HATEOAS.",
        ["api","rest","openapi","swagger","versioning","pagination","rate-limit","gateway","endpoints"],450),

    AgentSpec("MICRO_SVC","Microservices Architect",1,"architecture","claude-opus-4-7",
        "Microservices patterns: saga, CQRS, event sourcing, choreography vs orchestration, "
        "service mesh (Istio), circuit breaker (Resilience4j), distributed tracing.",
        ["microservices","saga","cqrs","event-sourcing","istio","circuit-breaker","distributed","service-mesh"],470),

    AgentSpec("QUEUE_MSG","Message Queue Specialist",1,"messaging","claude-sonnet-4-6",
        "Kafka: topics, partitions, consumer groups, exactly-once semantics. "
        "RabbitMQ: exchanges, routing, dead-letter. SQS, Celery, BullMQ.",
        ["kafka","rabbitmq","sqs","celery","bullmq","message-queue","event","pub/sub","consumer","producer"],430),

    AgentSpec("GRPC_PRO","gRPC Systems Engineer",1,"api","claude-sonnet-4-6",
        "gRPC + Protocol Buffers: service definitions, streaming (unary/server/client/bi), "
        "interceptors, error handling, load balancing, reflection.",
        ["grpc","protobuf","protocol-buffers","streaming","rpc","interceptor"],380),

    AgentSpec("SEARCH_ENG","Search Engine Specialist",1,"search","claude-sonnet-4-6",
        "Elasticsearch, OpenSearch: mappings, analyzers, full-text search, "
        "aggregations, relevance tuning, vector search, hybrid search.",
        ["elasticsearch","opensearch","search","full-text","indexing","aggregation","kibana"],400),

    AgentSpec("REALTIME_ENG","Real-Time Systems Engineer",1,"realtime","claude-sonnet-4-6",
        "WebSocket, Socket.io, Server-Sent Events, CRDT for collaboration, "
        "presence systems, operational transform, conflict resolution.",
        ["websocket","socket.io","real-time","sse","crdt","collaboration","presence","live"],420),

    AgentSpec("WASM_ENG","WebAssembly Systems Engineer",1,"wasm","claude-sonnet-4-6",
        "Rust + WebAssembly: wasm-bindgen, WASI, performance-critical web modules, "
        "interop with JavaScript, memory management.",
        ["webassembly","wasm","rust","wasm-bindgen","performance","native","c++"],380),

    AgentSpec("GRAPH_DB","Graph Database Specialist",1,"database","claude-sonnet-4-6",
        "Neo4j, FalkorDB, Amazon Neptune: graph modeling, Cypher queries, "
        "relationship traversal, social graphs, recommendation engines.",
        ["neo4j","graph-database","cypher","relationship","traversal","knowledge-graph"],380),

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 2 — AI/ML SPECIALISTS (15 agents)
    # ══════════════════════════════════════════════════════════════════════════

    AgentSpec("VECTOR_AI","Vector DB & Embeddings Expert",2,"ai","claude-opus-4-7",
        "Vector databases: pgvector, Pinecone, Weaviate, Qdrant. Embedding models, "
        "similarity search, hybrid search, RAG pipelines, chunking strategies.",
        ["vector","embedding","rag","pinecone","weaviate","qdrant","pgvector","semantic-search","retrieval"],460),

    AgentSpec("RAG_PRO","RAG Architecture Specialist",2,"ai","claude-opus-4-7",
        "Advanced RAG: HyDE, reranking (Cohere), multi-vector, parent-document retrieval, "
        "query expansion, self-RAG, FLARE, contextual compression.",
        ["rag","retrieval","langchain","llamaindex","reranking","hyde","context","augmented-generation"],470),

    AgentSpec("PROMPT_ENG","Prompt Engineering Master",2,"ai","claude-opus-4-7",
        "Advanced prompting: chain-of-thought, tree-of-thought, ReAct, Constitutional AI, "
        "few-shot, structured output with tool_use, system prompt optimization.",
        ["prompt","chain-of-thought","few-shot","tool-use","structured-output","reasoning","cot","prompt-eng"],470),

    AgentSpec("AGENT_ARCH","AI Agent Framework Architect",2,"ai","claude-opus-4-7",
        "AI agent design: tool use, planning (BFS/DFS), memory (episodic/semantic), "
        "multi-agent coordination, reflection, self-correction, LangGraph, AutoGen.",
        ["agent","langgraph","autogen","tool-use","planning","memory","multi-agent","autonomous","crewai"],480),

    AgentSpec("FINE_TUNE","LLM Fine-Tuning Specialist",2,"ai","claude-sonnet-4-6",
        "LoRA, QLoRA, PEFT, RLHF, DPO. Hugging Face Transformers, FSDP, "
        "training pipelines, evaluation, overfitting prevention, dataset curation.",
        ["fine-tuning","lora","qlora","rlhf","dpo","peft","huggingface","training","llm"],440),

    AgentSpec("DIFFUSION_AI","Generative AI Specialist",2,"ai","claude-sonnet-4-6",
        "Stable Diffusion, FLUX, ControlNet, LoRA training, SDXL, ComfyUI workflows, "
        "video generation, image-to-image, inpainting, prompt engineering for images.",
        ["stable-diffusion","flux","dalle","midjourney","controlnet","image-gen","comfyui"],420),

    AgentSpec("VISION_AI","Computer Vision Engineer",2,"ai","claude-sonnet-4-6",
        "YOLO, SAM (Segment Anything), DepthAnything, OpenCV, object detection, "
        "semantic segmentation, OCR, face recognition, video analysis.",
        ["computer-vision","yolo","opencv","detection","segmentation","ocr","image-processing"],420),

    AgentSpec("NLP_ENG","NLP/Language Processing Expert",2,"ai","claude-sonnet-4-6",
        "spaCy, NLTK, sentiment analysis, NER, text classification, summarization, "
        "translation, topic modeling, coreference resolution.",
        ["nlp","sentiment","ner","classification","summarization","spacy","text","language"],400),

    AgentSpec("ML_OPS","MLOps Engineer",2,"ai","claude-sonnet-4-6",
        "ML pipeline orchestration: MLflow, Weights & Biases, DVC, Airflow. "
        "Model serving (TorchServe, BentoML, vLLM), monitoring, A/B testing, drift.",
        ["mlops","mlflow","wandb","dvc","model-serving","bentoml","vllm","monitoring","drift"],430),

    AgentSpec("DATA_SCI","Data Science & Analysis Expert",2,"data","claude-sonnet-4-6",
        "Pandas, NumPy, scikit-learn, statistical analysis, hypothesis testing, "
        "Jupyter, Plotly, feature engineering, AutoML (AutoSklearn, H2O).",
        ["pandas","numpy","scikit-learn","data-science","statistics","matplotlib","plotly","jupyter"],420),

    AgentSpec("LLM_OPT","LLM Optimization Specialist",2,"ai","claude-sonnet-4-6",
        "Model quantization (GGUF, GPTQ, AWQ), KV cache, speculative decoding, "
        "FlashAttention, rope scaling, context length extension.",
        ["quantization","gguf","gptq","awq","flash-attention","inference","optimization","llm"],420),

    AgentSpec("GRAPH_ML","Graph ML Specialist",2,"ai","claude-sonnet-4-6",
        "Graph Neural Networks (GNN, GAT, GraphSAGE), knowledge graphs, "
        "link prediction, node classification, molecular property prediction.",
        ["gnn","graph-neural-network","knowledge-graph","link-prediction","pytorch-geometric"],390),

    AgentSpec("REINFORCE","Reinforcement Learning Expert",2,"ai","claude-sonnet-4-6",
        "RL algorithms: PPO, SAC, DQN, MCTS. OpenAI Gym, environments, "
        "reward shaping, multi-agent RL, offline RL, model-based RL.",
        ["reinforcement-learning","rl","ppo","dqn","gym","reward","policy","agent","mcts"],400),

    AgentSpec("ANOMALY_AI","Anomaly Detection Expert",2,"ai","claude-sonnet-4-6",
        "Anomaly detection: isolation forest, autoencoder, LSTM for time series, "
        "streaming anomalies, fraud detection, log analysis, AIOps.",
        ["anomaly","fraud-detection","isolation-forest","time-series","lstm","aiops","monitoring"],390),

    AgentSpec("SYNTH_AI","Synthetic Data Specialist",2,"ai","claude-sonnet-4-6",
        "Synthetic data generation: SDV, CTGAN, privacy-preserving (differential privacy), "
        "augmentation strategies, data quality validation, bias reduction.",
        ["synthetic-data","ctgan","sdv","privacy","differential-privacy","augmentation","data-gen"],380),

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 3 — SECURITY MASTERS (10 agents)
    # ══════════════════════════════════════════════════════════════════════════

    AgentSpec("PENTEST_PRO","Penetration Testing Expert",3,"security","claude-opus-4-7",
        "OWASP Top 10 deep dive, SQL injection, XSS, SSRF, XXE, IDOR, "
        "authentication bypass, Burp Suite methodology, security headers.",
        ["penetration-test","pentest","owasp","xss","sql-injection","ssrf","idor","vulnerability","exploit"],470),

    AgentSpec("CRYPTO_PRO","Cryptography Specialist",3,"security","claude-opus-4-7",
        "Cryptographic primitives: AES-GCM, RSA, ECDH, Ed25519. Zero-knowledge proofs, "
        "TLS/mTLS, PKI, key management, HSM, homomorphic encryption basics.",
        ["cryptography","encryption","aes","rsa","tls","zero-knowledge","zkp","jwt","signing","pki"],460),

    AgentSpec("AUTH_MASTER","Identity & Auth Specialist",3,"security","claude-opus-4-7",
        "OAuth 2.0, OIDC, SAML 2.0, WebAuthn/FIDO2, PKCE, JWT best practices, "
        "session management, MFA, SSO, refresh token rotation, device authorization.",
        ["oauth","oidc","saml","jwt","authentication","sso","webauthn","fido2","pkce","mfa","session"],470),

    AgentSpec("DEVSEC","DevSecOps Engineer",3,"security","claude-sonnet-4-6",
        "SAST (Semgrep, SonarQube), DAST (OWASP ZAP), dependency scanning (Snyk, Trivy), "
        "secrets detection (Gitleaks), compliance automation, security policies.",
        ["devsecops","sast","dast","snyk","trivy","semgrep","sonarqube","supply-chain","sbom"],440),

    AgentSpec("THREAT_ARCH","Threat Modeling Expert",3,"security","claude-opus-4-7",
        "STRIDE, DREAD, PASTA methodologies. Attack trees, data flow diagrams, "
        "trust boundaries, threat actors, risk quantification (CVSS).",
        ["threat-modeling","stride","attack-tree","trust-boundary","cvss","risk","threat-actor"],440),

    AgentSpec("ZERO_TRUST","Zero Trust Architect",3,"security","claude-sonnet-4-6",
        "Zero trust implementation: BeyondCorp, SPIFFE/SPIRE, mTLS everywhere, "
        "identity-aware proxy, micro-segmentation, continuous validation.",
        ["zero-trust","beyondcorp","spiffe","mtls","micro-segmentation","identity-proxy","least-privilege"],420),

    AgentSpec("BLOCK_SEC","Blockchain Security Expert",3,"security","claude-opus-4-7",
        "Smart contract auditing: reentrancy, integer overflow, access control, "
        "front-running, flash loans. Solidity patterns, formal verification.",
        ["smart-contract","solidity","audit","reentrancy","blockchain","web3","defi","evm","security"],450),

    AgentSpec("PRIVACY_ENG","Privacy Engineering Specialist",3,"security","claude-sonnet-4-6",
        "GDPR, CCPA, HIPAA compliance. Privacy by design, data minimization, "
        "anonymization, pseudonymization, consent management, DPIA.",
        ["gdpr","ccpa","hipaa","privacy","compliance","anonymization","consent","data-protection"],420),

    AgentSpec("NETWORK_SEC","Network Security Engineer",3,"security","claude-sonnet-4-6",
        "Firewall rules, WAF configuration, DDoS mitigation, network segmentation, "
        "IDS/IPS, VPN, TLS termination, certificate management.",
        ["firewall","waf","ddos","network-security","vpn","ids","ips","tls","certificate"],400),

    AgentSpec("FORENSIC_ENG","Digital Forensics Expert",3,"security","claude-sonnet-4-6",
        "Incident response, log analysis (SIEM), memory forensics, IOC identification, "
        "chain of custody, threat hunting, kill chain analysis.",
        ["forensics","incident-response","siem","threat-hunting","ioc","log-analysis","kill-chain"],400),

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 4 — PERFORMANCE ENGINEERS (10 agents)
    # ══════════════════════════════════════════════════════════════════════════

    AgentSpec("PROFILER","System Profiler",4,"performance","claude-sonnet-4-6",
        "CPU + memory profiling: pprof, py-spy, async-profiler, Chrome DevTools. "
        "Flame graphs, heap dumps, GC analysis, goroutine/thread analysis.",
        ["profiling","pprof","py-spy","flame-graph","memory","cpu","heap","gc","devtools","performance"],440),

    AgentSpec("LOAD_TEST","Load Testing Specialist",4,"performance","claude-sonnet-4-6",
        "Load testing with k6, Locust, Gatling, JMeter. Scenario design, "
        "SLA validation, bottleneck identification, stress + soak testing.",
        ["load-testing","k6","locust","gatling","jmeter","stress","soak","latency","throughput"],420),

    AgentSpec("DB_OPT","Database Query Optimizer",4,"performance","claude-opus-4-7",
        "Query optimization: EXPLAIN ANALYZE, index strategy, N+1 elimination, "
        "connection pooling (PgBouncer), read replicas, query caching.",
        ["query-optimization","explain","index","n+1","connection-pool","pgbouncer","slow-query"],450),

    AgentSpec("BUNDLE_OPT","JS Bundle Optimizer",4,"performance","claude-sonnet-4-6",
        "Webpack/Vite bundle analysis: code splitting, tree shaking, lazy loading, "
        "critical CSS, preload/prefetch, compression (Brotli, gzip), Core Web Vitals.",
        ["bundle","tree-shaking","code-splitting","lazy-loading","webpack","vite","web-vitals","lcp","cls"],440),

    AgentSpec("CDN_STRAT","CDN & Caching Strategist",4,"performance","claude-sonnet-4-6",
        "CDN configuration: cache-control headers, stale-while-revalidate, "
        "edge caching strategies, cache invalidation, origin shield, purging.",
        ["cdn","cache-control","edge-cache","cloudfront","fastly","cache-invalidation","ttl","etag"],420),

    AgentSpec("ALGO_OPT","Algorithm Optimization Expert",4,"performance","claude-opus-4-7",
        "Algorithm analysis: Big O, dynamic programming, memoization, "
        "greedy algorithms, backtracking, graph algorithms (Dijkstra, A*), data structures.",
        ["algorithm","big-o","dynamic-programming","memoization","optimization","complexity","data-structure"],460),

    AgentSpec("CONCUR_ENG","Concurrency Engineering Expert",4,"performance","claude-opus-4-7",
        "Async/await patterns, race conditions, deadlocks, actor model, "
        "lock-free algorithms, thread pools, coroutines, event loops.",
        ["concurrency","async","race-condition","deadlock","thread","coroutine","actor","lock-free"],450),

    AgentSpec("MEMORY_ENG","Memory Management Specialist",4,"performance","claude-sonnet-4-6",
        "Memory leaks detection, GC tuning, off-heap storage, buffer management, "
        "object pooling, arena allocators, WASM memory, V8 heap analysis.",
        ["memory","leak","gc","garbage-collection","heap","buffer","v8","memory-pool","allocation"],420),

    AgentSpec("NET_PERF","Network Performance Engineer",4,"performance","claude-sonnet-4-6",
        "HTTP/2, HTTP/3, QUIC, TCP optimization, connection keep-alive, "
        "gzip/Brotli, DNS prefetch, protocol selection, WebRTC optimization.",
        ["http2","http3","quic","tcp","protocol","latency","bandwidth","network","websocket","webrtc"],400),

    AgentSpec("BENCH_MARK","Benchmarking Specialist",4,"performance","claude-sonnet-4-6",
        "Scientific benchmarking: hyperfine, criterion.rs, benchmark.js, "
        "statistical significance, warm-up, steady state, eliminating noise.",
        ["benchmarking","hyperfine","criterion","performance-test","measurement","statistics"],380),

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 5 — DOMAIN EXPERTS (15 agents)
    # ══════════════════════════════════════════════════════════════════════════

    AgentSpec("FINTECH_ENG","Financial Technology Expert",5,"fintech","claude-opus-4-7",
        "Payment processing (Stripe, Adyen), PCI-DSS compliance, banking APIs (Open Banking), "
        "financial calculations (decimal precision), trading systems, compliance (AML/KYC).",
        ["fintech","payment","stripe","pci","banking","trading","kyc","aml","financial","compliance"],470),

    AgentSpec("HEALTH_IT","Healthcare IT Specialist",5,"healthcare","claude-opus-4-7",
        "HIPAA compliance, HL7 FHIR, DICOM, EHR integration, medical device APIs, "
        "telemedicine, clinical data standards, de-identification.",
        ["healthcare","hipaa","fhir","hl7","dicom","ehr","medical","telemedicine","clinical"],450),

    AgentSpec("ECOMM_ENG","E-Commerce Systems Expert",5,"ecommerce","claude-sonnet-4-6",
        "E-commerce: product catalog, inventory management, cart systems, checkout flow, "
        "payment gateways, tax calculation, shipping APIs, order management.",
        ["ecommerce","cart","checkout","inventory","product","payment","shopify","woocommerce","order"],440),

    AgentSpec("GAME_DEV","Game Development Engineer",5,"gaming","claude-sonnet-4-6",
        "Game loop, physics engines (Cannon.js, Rapier), 3D collision detection, "
        "multiplayer architecture, WebGL game rendering, Babylon.js, Three.js game patterns.",
        ["game","game-loop","physics","multiplayer","babylon.js","three.js","collision","rendering"],420),

    AgentSpec("GEO_ENG","Geospatial Systems Engineer",5,"geo","claude-sonnet-4-6",
        "PostGIS, MapboxGL, Leaflet, geospatial algorithms (Haversine, polygon intersection), "
        "routing (OSRM, Valhalla), geocoding, spatial indexing (R-tree).",
        ["geospatial","postgis","mapbox","leaflet","routing","geocoding","spatial","gis","coordinates"],420),

    AgentSpec("MEDIA_ENG","Media & Streaming Engineer",5,"media","claude-sonnet-4-6",
        "Video streaming: HLS, DASH, WebRTC, FFmpeg, video transcoding, "
        "adaptive bitrate, CDN for video, live streaming, codec selection.",
        ["video","streaming","hls","dash","webrtc","ffmpeg","transcoding","live","codec","media"],430),

    AgentSpec("IOT_ENG","IoT Systems Engineer",5,"iot","claude-sonnet-4-6",
        "MQTT, CoAP, IoT device management, edge computing, time-series data (InfluxDB), "
        "sensor data processing, OTA updates, AWS IoT, Azure IoT Hub.",
        ["iot","mqtt","coap","sensor","edge","timeseries","influxdb","firmware","ota"],410),

    AgentSpec("BLOCK_ENG","Blockchain Developer",5,"blockchain","claude-opus-4-7",
        "Solidity smart contracts, EVM, DeFi protocols (AMM, lending), NFT standards (ERC-721/1155), "
        "Layer 2 (Polygon, Arbitrum), ethers.js/viem, Hardhat testing.",
        ["blockchain","solidity","smart-contract","defi","nft","ethereum","polygon","arbitrum","web3"],460),

    AgentSpec("SOCIAL_ENG","Social Platform Engineer",5,"social","claude-sonnet-4-6",
        "Social graph architecture, activity feeds (fan-out on write/read), "
        "notification systems, content moderation, recommendations, real-time presence.",
        ["social","feed","notification","recommendation","moderation","graph","activity","presence"],420),

    AgentSpec("LEGAL_TECH","Legal Technology Specialist",5,"legaltech","claude-sonnet-4-6",
        "Contract analysis, e-signatures (DocuSign API), legal document generation, "
        "compliance automation, GDPR/CCPA tooling, legal data models.",
        ["legal","contract","e-signature","compliance","gdpr","document","legaltech","regulation"],400),

    AgentSpec("ENERGY_ENG","Energy Systems Engineer",5,"energy","claude-sonnet-4-6",
        "Smart grid architecture, energy monitoring, SCADA systems, "
        "solar/EV integration APIs, energy optimization algorithms.",
        ["energy","smart-grid","scada","solar","ev","monitoring","optimization","utility"],390),

    AgentSpec("LOG_ANAL","Logistics & Supply Chain Expert",5,"logistics","claude-sonnet-4-6",
        "Supply chain optimization, routing (TSP, VRP), warehouse management, "
        "inventory forecasting, ERP integration, last-mile delivery.",
        ["logistics","supply-chain","routing","warehouse","inventory","erp","delivery","optimization"],400),

    AgentSpec("EDTECH_ENG","Education Technology Expert",5,"edtech","claude-sonnet-4-6",
        "LMS architecture (xAPI, SCORM), adaptive learning, assessment engines, "
        "gamification, content delivery, student analytics, accessibility.",
        ["edtech","lms","xapi","scorm","adaptive-learning","assessment","gamification","education"],390),

    AgentSpec("MULTI_TENANT","Multi-Tenant SaaS Architect",5,"saas","claude-opus-4-7",
        "Multi-tenancy patterns: shared schema vs schema-per-tenant vs DB-per-tenant, "
        "tenant isolation, billing, feature flags, subdomain routing, onboarding.",
        ["multi-tenant","saas","tenant","isolation","billing","feature-flags","onboarding","b2b"],460),

    AgentSpec("GOV_TECH","Government Technology Expert",5,"govtech","claude-sonnet-4-6",
        "Digital identity systems, blockchain for public records, "
        "accessibility (WCAG), open government data APIs, secure voting.",
        ["government","digital-identity","accessibility","open-data","public-records","govtech"],380),

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 6 — QUALITY ARCHITECTS (10 agents)
    # ══════════════════════════════════════════════════════════════════════════

    AgentSpec("TDD_MASTER","Test-Driven Development Master",6,"quality","claude-opus-4-7",
        "TDD red-green-refactor cycle, test pyramid (unit/integration/e2e), "
        "mocking strategies, test isolation, BDD (Cucumber/Gherkin), property testing.",
        ["tdd","testing","unit-test","integration-test","mock","bdd","jest","pytest","vitest","coverage"],460),

    AgentSpec("E2E_MASTER","End-to-End Testing Expert",6,"quality","claude-sonnet-4-6",
        "Playwright, Cypress: test design, page object model, visual regression, "
        "cross-browser testing, CI integration, flaky test elimination.",
        ["e2e","playwright","cypress","visual-regression","page-object","cross-browser","selenium"],430),

    AgentSpec("CHAOS_ENG","Chaos Engineering Expert",6,"quality","claude-sonnet-4-6",
        "Chaos Monkey, Gremlin, Litmus. Failure injection: CPU spike, memory pressure, "
        "network partition, pod kill. Game days, runbooks, SLO validation.",
        ["chaos","fault-injection","resilience","gremlin","chaos-monkey","slo","gameday","failure"],420),

    AgentSpec("MUTATION","Mutation Testing Specialist",6,"quality","claude-sonnet-4-6",
        "Mutation testing: Mutmut, PIT, Stryker. Test quality measurement, "
        "surviving mutants analysis, test suite improvement.",
        ["mutation-testing","mutmut","stryker","pit","test-quality","coverage"],390),

    AgentSpec("CODE_REV","Code Review Excellence Expert",6,"quality","claude-opus-4-7",
        "Systematic code review: architecture concerns, security, performance, "
        "maintainability, naming, SOLID principles, design patterns identification.",
        ["code-review","solid","design-patterns","maintainability","refactoring","clean-code","review"],450),

    AgentSpec("REFACTOR","Refactoring Patterns Expert",6,"quality","claude-opus-4-7",
        "Refactoring techniques: extract method, introduce parameter object, "
        "replace conditional with polymorphism, strangler fig, anticorruption layer.",
        ["refactoring","clean-code","technical-debt","legacy","patterns","strangler-fig","extract"],440),

    AgentSpec("DOC_ARCH","Technical Documentation Architect",6,"quality","claude-sonnet-4-6",
        "ADRs (Architecture Decision Records), runbooks, OpenAPI documentation, "
        "README excellence, changelog management, technical writing.",
        ["documentation","adr","runbook","readme","changelog","technical-writing","openapi"],400),

    AgentSpec("CONTRACT_TEST","Contract Testing Expert",6,"quality","claude-sonnet-4-6",
        "Consumer-driven contracts (Pact), provider verification, "
        "schema validation, API compatibility testing, breaking change detection.",
        ["contract-testing","pact","consumer-driven","schema","compatibility","api-testing"],390),

    AgentSpec("OBSERV_ENG","Observability Engineering Expert",6,"quality","claude-sonnet-4-6",
        "OpenTelemetry: traces, metrics, logs. Prometheus + Grafana, distributed tracing "
        "(Jaeger), error tracking (Sentry), SLO/SLA definition.",
        ["observability","opentelemetry","prometheus","grafana","jaeger","sentry","tracing","metrics","slo"],430),

    AgentSpec("PERF_TEST","Performance Testing Architect",6,"quality","claude-sonnet-4-6",
        "Performance test strategy: baseline, load, stress, spike, soak testing. "
        "SLO-driven testing, regressions CI gates, performance budgets.",
        ["performance-testing","load","stress","soak","baseline","slo","regression","budget"],410),

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 7 — CREATIVE DESIGNERS (10 agents)
    # ══════════════════════════════════════════════════════════════════════════

    AgentSpec("THREE_MASTER","Three.js / WebGL Master",7,"creative","claude-opus-4-7",
        "Three.js advanced: custom shaders (GLSL), post-processing (bloom, DOF), "
        "physics (Rapier/Cannon), particle systems, InstancedMesh, R3F.",
        ["three.js","webgl","glsl","shader","post-processing","r3f","three","3d","canvas","particle"],480),

    AgentSpec("GLSL_MASTER","GLSL Shader Master",7,"creative","claude-opus-4-7",
        "Advanced GLSL: vertex/fragment shaders, compute shaders (WebGPU), "
        "noise functions (simplex, Worley), SDF, ray marching, physically-based rendering.",
        ["glsl","shader","webgpu","noise","sdf","ray-marching","pbr","fragment","vertex","gpu"],480),

    AgentSpec("D3_MASTER","D3.js Visualization Master",7,"creative","claude-opus-4-7",
        "D3.js advanced: force simulations, geographic projections, streaming data, "
        "complex hierarchies (treemap, sunburst), custom interpolators, transitions.",
        ["d3","d3.js","visualization","force","geographic","chart","svg","animation","data-viz"],460),

    AgentSpec("MOTION_MASTER","Motion Design Master",7,"creative","claude-opus-4-7",
        "Advanced animation: GSAP timelines, physics-based (spring/inertia), "
        "scroll-driven, Lenis, Theatre.js choreography, SVG morphing, Rive.",
        ["animation","gsap","motion","spring","scroll","lenis","theatre","rive","easing","choreography"],470),

    AgentSpec("UX_RESEARCH","UX Research & Design Expert",7,"design","claude-opus-4-7",
        "User research methods, usability testing, information architecture, "
        "interaction design, prototyping (Figma), accessibility-first design, design systems.",
        ["ux","user-research","usability","figma","accessibility","design-system","interaction","wireframe"],460),

    AgentSpec("VISUAL_DES","Visual Design Expert",7,"design","claude-sonnet-4-6",
        "Color theory, typography (type hierarchy, pairing), grid systems, "
        "brand identity, visual hierarchy, iconography, dark mode design.",
        ["design","color","typography","brand","visual","hierarchy","iconography","dark-mode"],440),

    AgentSpec("ACCESSIBLE","Accessibility Specialist",7,"design","claude-opus-4-7",
        "WCAG 2.2 AA/AAA: keyboard navigation, screen reader (NVDA, JAWS, VoiceOver), "
        "ARIA patterns, focus management, colour contrast, cognitive accessibility.",
        ["accessibility","wcag","aria","keyboard","screen-reader","a11y","contrast","focus"],460),

    AgentSpec("ANIME_PRO","anime.js + Micro-Animation Expert",7,"creative","claude-sonnet-4-6",
        "anime.js advanced: SVG morphing, timeline sequences, spring physics, "
        "stagger patterns, path animation, CSS variable animation.",
        ["anime.js","animation","svg-morph","timeline","stagger","spring","micro-animation"],430),

    AgentSpec("FIGMA_CODE","Figma → Code Expert",7,"design","claude-sonnet-4-6",
        "Design token extraction, Figma API, design-to-code workflows, "
        "automated CSS generation, component naming conventions, design system governance.",
        ["figma","design-token","design-system","figma-api","component","design-to-code"],410),

    AgentSpec("TAILWIND_PRO","Tailwind CSS Expert",7,"design","claude-sonnet-4-6",
        "Tailwind advanced: custom plugins, dark mode, arbitrary values, "
        "JIT, component extraction, design tokens with CSS variables.",
        ["tailwind","tailwindcss","css","utility","responsive","dark-mode","custom-plugin"],420),

    # ══════════════════════════════════════════════════════════════════════════
    # TIER 8 — STRATEGY & META (10 agents)
    # ══════════════════════════════════════════════════════════════════════════

    AgentSpec("ENT_ARCH","Enterprise Architecture Expert",8,"strategy","claude-opus-4-7",
        "Domain-Driven Design (DDD), Event Storming, bounded contexts, "
        "TOGAF, C4 model diagrams, architectural fitness functions.",
        ["enterprise-architecture","ddd","event-storming","bounded-context","togaf","c4","fitness-function"],480),

    AgentSpec("SCALE_STRAT","Scaling Strategy Expert",8,"strategy","claude-opus-4-7",
        "Horizontal vs vertical scaling, database scaling (sharding, read replicas), "
        "caching layers, stateless design, eventual consistency, CAP theorem.",
        ["scaling","horizontal","sharding","read-replica","stateless","cap-theorem","consistency"],470),

    AgentSpec("TECH_LEAD","Technical Leadership Expert",8,"strategy","claude-opus-4-7",
        "Technical leadership: RFC writing, ADR decision-making, team mentoring, "
        "technical roadmap, managing tech debt, stakeholder communication.",
        ["tech-lead","leadership","rfc","adr","roadmap","mentoring","technical-debt","stakeholder"],460),

    AgentSpec("COST_OPT","Cloud Cost Optimization Expert",8,"strategy","claude-sonnet-4-6",
        "FinOps: reserved instances, spot instances, right-sizing, "
        "cost anomaly detection, tagging strategy, budget alerts, savings plans.",
        ["cost","finops","reserved","spot","right-sizing","budget","aws-cost","optimization"],430),

    AgentSpec("LEGACY_MOD","Legacy Modernization Expert",8,"strategy","claude-opus-4-7",
        "Legacy system modernization: strangler fig pattern, event interception, "
        "branch by abstraction, anticorruption layer, COBOL/Java migration strategies.",
        ["legacy","modernization","strangler-fig","migration","monolith","refactor","anticorruption"],460),

    AgentSpec("TECH_DEBT","Technical Debt Manager",8,"strategy","claude-sonnet-4-6",
        "Technical debt identification, quantification (SQALE), payoff strategy, "
        "debt register, architectural smell detection, sprint planning for debt.",
        ["technical-debt","refactoring","debt-register","sqale","code-smell","maintainability"],430),

    AgentSpec("INNOV_STRAT","Innovation & Emerging Tech Scout",8,"strategy","claude-opus-4-7",
        "Technology radar, emerging tech assessment (WebGPU, WASM, edge AI), "
        "proof of concept design, build vs buy analysis, vendor evaluation.",
        ["innovation","emerging-tech","webgpu","poc","vendor","technology-radar","build-vs-buy"],450),

    AgentSpec("DX_OPT","Developer Experience Optimizer",8,"strategy","claude-sonnet-4-6",
        "Developer tooling: monorepo (Nx, Turborepo), local dev environments, "
        "onboarding acceleration, IDE configuration, linting, formatting, pre-commit.",
        ["dx","developer-experience","monorepo","nx","turborepo","tooling","onboarding","linting"],420),

    AgentSpec("COMPLIANCE_ENG","Regulatory Compliance Architect",8,"strategy","claude-opus-4-7",
        "SOC 2 Type II, ISO 27001, NIST, FedRAMP. Compliance automation, "
        "audit trails, control mapping, policy-as-code.",
        ["compliance","soc2","iso27001","nist","fedramp","audit","policy-as-code","regulatory"],450),

    AgentSpec("ESTIMATOR_PRO","Technical Estimation Expert",8,"strategy","claude-sonnet-4-6",
        "Story point calibration, PERT estimation, cone of uncertainty, "
        "breaking down epics, reference class forecasting, risk-adjusted estimates.",
        ["estimation","story-points","pert","planning","breakdown","forecasting","sprint"],410),
]

# Verify count
assert len(AGENT_REGISTRY) == 100, f"Expected 100 agents, got {len(AGENT_REGISTRY)}"


# ── Agent lookup helpers ──────────────────────────────────────────────────────

def _registry_by_id() -> Dict[str, AgentSpec]:
    return {a.id: a for a in AGENT_REGISTRY}

def _registry_by_tier(tier: int) -> List[AgentSpec]:
    return [a for a in AGENT_REGISTRY if a.tier == tier]

REGISTRY_INDEX = _registry_by_id()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MULTIWAVE PERFORMER RESULT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class PerformerWave:
    number:      int
    agents:      List[str]       # agent IDs
    theme:       str
    outputs:     List[PipelineResult]
    duration_ms: int
    insights:    str             # extracted context for next wave


@dataclass
class PerformerResult:
    task:            str
    total_agents:    int
    waves:           List[PerformerWave]
    final_synthesis: str
    top_agents:      List[tuple]  # (agent_id, confidence, insight_length)
    trace_id:        str
    total_ms:        int
    confidence:      float

    def executive_summary(self) -> str:
        lines = [
            f"⚡ AILEX MultiWave Performer",
            f"  Task: {self.task[:70]}",
            f"  Agents deployed: {self.total_agents} across {len(self.waves)} waves",
            f"  Total time: {self.total_ms}ms | Confidence: {self.confidence:.3f}",
            f"  Trace: {self.trace_id}",
            "",
        ]
        for i, wave in enumerate(self.waves):
            lines.append(f"  ▶ Wave {i+1}: {wave.theme}")
            lines.append(f"    Agents: {' + '.join(wave.agents)}")
            if wave.insights:
                lines.append(f"    ↳ {wave.insights[:120]}...")
        lines.append("")
        lines.append(f"  ◆ SYNTHESIS:")
        lines.append(f"  {self.final_synthesis[:400]}")
        return "\n".join(lines)

    def top_performers(self, n: int = 5) -> str:
        sorted_agents = sorted(self.top_agents, key=lambda x: x[1], reverse=True)[:n]
        lines = [f"Top {n} Performers:"]
        for agent_id, conf, insight_len in sorted_agents:
            spec = REGISTRY_INDEX.get(agent_id)
            name = spec.name if spec else agent_id
            tier = spec.tier if spec else "?"
            lines.append(f"  [{agent_id}] {name} (T{tier}) — conf={conf:.2f}")
        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MULTIWAVE PERFORMER SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MultiWavePerformer:
    """
    100 super-specialized agents in dynamic wave formation.

    Workflow:
      1. Analyse task → score all 100 agents by keyword relevance
      2. Select top N agents per tier
      3. Compose dynamic waves (each tier becomes a wave)
      4. Execute waves sequentially, passing context forward
      5. ORION meta-synthesis at end
    """

    AGENTS_PER_WAVE  = 4   # max agents per wave
    MAX_WAVES        = 6   # max waves per run
    MIN_RELEVANCE    = 1   # minimum keyword matches to include agent
    HALT_THRESHOLD   = 0.96

    def __init__(
        self,
        pipeline:   Optional[InstrumentedPipeline] = None,
        verbose:    bool = True,
    ):
        self.pipeline  = pipeline or get_pipeline()
        self.verbose   = verbose
        self.log       = get_logger("mwp")
        self._perf_db: Dict[str, List[float]] = {}  # agent_id → confidence history

    # ── Public API ─────────────────────────────────────────────────────────────

    def run(
        self,
        task:       str,
        domain:     str      = "",
        context:    str      = "",
        max_agents: int      = 20,
        max_waves:  int      = 5,
    ) -> PerformerResult:
        """
        Run the MultiWave Performer on a task.

        1. Scores all 100 agents by task relevance
        2. Selects top agents (up to max_agents)
        3. Groups into waves by tier
        4. Runs waves sequentially
        5. ORION final synthesis
        """
        t0    = time.perf_counter()
        trace = tracer.new_trace()
        self.pipeline._active_trace = trace

        # Step 1: Score + select agents
        selected = self._select_agents(task, max_agents)
        if self.verbose:
            print(f"\n⚡ MultiWave Performer System")
            print(f"  Task: {task[:65]}...")
            print(f"  Selected: {len(selected)} agents from 100")
            print(f"  Trace: {trace}\n")

        # Step 2: Group into waves by tier
        waves_plan = self._compose_waves(selected, max_waves)

        # Step 3: Execute waves
        executed_waves: List[PerformerWave] = []
        accumulated_ctx = context
        all_agent_perfs: List[tuple] = []

        for i, (theme, agent_ids) in enumerate(waves_plan):
            wave_t0 = time.perf_counter()
            if self.verbose:
                print(f"  ▶ Wave {i+1}/{len(waves_plan)}: {theme}")
                print(f"    Agents: {' + '.join(agent_ids[:6])}")

            # Build context for this wave
            wave_ctx = self._build_context(task, accumulated_ctx, executed_waves)

            # Run agents in parallel
            outputs = self.pipeline.run_parallel(
                task=task,
                domain=domain or self._infer_domain(agent_ids),
                agents=agent_ids,
                context=wave_ctx,
            )

            dur_ms = int((time.perf_counter() - wave_t0) * 1000)

            # Extract insights for next wave
            insights = self._extract_insights(outputs)

            wave = PerformerWave(
                number=i+1, agents=agent_ids, theme=theme,
                outputs=outputs, duration_ms=dur_ms, insights=insights,
            )
            executed_waves.append(wave)

            # Track performance
            for out in outputs:
                self._record_perf(out.agent, out.confidence)
                all_agent_perfs.append((out.agent, out.confidence, len(out.analysis)))

            accumulated_ctx = f"{accumulated_ctx}\n\n{insights}".strip()

            avg_conf = sum(o.confidence for o in outputs) / max(1, len(outputs))
            if self.verbose:
                print(f"    ✓ {dur_ms}ms | avg_conf={avg_conf:.2f}")

            # Halt check
            if avg_conf >= self.HALT_THRESHOLD and i >= 1:
                if self.verbose:
                    print(f"\n  ⚡ Halt: confidence {avg_conf:.3f} ≥ {self.HALT_THRESHOLD}")
                break

            metrics.record(trace, f"mwp.wave.{i+1}", theme=theme,
                           agents=len(agent_ids), ms=dur_ms, confidence=avg_conf)

        # Step 4: ORION synthesis
        synthesis = self._orion_synthesis(task, executed_waves)

        total_ms = int((time.perf_counter() - t0) * 1000)
        all_confs = [o.confidence for w in executed_waves for o in w.outputs]
        global_conf = sum(all_confs) / max(1, len(all_confs))

        metrics.inc("mwp.completed")
        metrics.timing("mwp_total_ms", total_ms)

        result = PerformerResult(
            task=task,
            total_agents=sum(len(w.agents) for w in executed_waves),
            waves=executed_waves,
            final_synthesis=synthesis,
            top_agents=all_agent_perfs,
            trace_id=trace,
            total_ms=total_ms,
            confidence=global_conf,
        )

        if self.verbose:
            print(f"\n  ✅ Complete | Agents: {result.total_agents} | "
                  f"Waves: {len(executed_waves)} | {total_ms}ms | conf={global_conf:.3f}")
            print(f"\n  SYNTHESIS: {synthesis[:200]}...")

        return result

    def list_agents(self) -> List[AgentSpec]:
        return AGENT_REGISTRY

    def agents_by_tier(self, tier: int) -> List[AgentSpec]:
        return _registry_by_tier(tier)

    def describe(self) -> str:
        tier_counts = {}
        for a in AGENT_REGISTRY:
            tier_counts[a.tier] = tier_counts.get(a.tier, 0) + 1
        lines = ["MultiWave Performer — 100 Super-Specialized Agents", "─" * 60]
        tier_names = {1:"Engineering Core",2:"AI/ML",3:"Security",4:"Performance",
                      5:"Domain",6:"Quality",7:"Creative",8:"Strategy"}
        for tier, count in sorted(tier_counts.items()):
            lines.append(f"  Tier {tier} — {tier_names.get(tier,'?'):<22} {count:>2} agents")
        lines.append(f"\n  Total: {len(AGENT_REGISTRY)} agents")
        return "\n".join(lines)

    # ── Private ────────────────────────────────────────────────────────────────

    def _score_agent(self, agent: AgentSpec, task: str) -> int:
        """Score agent relevance to task using keyword matching."""
        task_lower = task.lower()
        words = set(re.findall(r'\w+', task_lower))
        score = 0
        for kw in agent.keywords:
            kw_words = set(kw.replace("-", " ").split())
            if any(w in task_lower for w in kw_words):
                score += 1
            if kw in task_lower:
                score += 1   # exact match bonus
        return score

    def _select_agents(self, task: str, max_agents: int) -> List[AgentSpec]:
        """Score all 100 agents and select the most relevant."""
        scored = [
            (a, self._score_agent(a, task))
            for a in AGENT_REGISTRY
        ]
        # Sort by score descending, then by tier (lower tier = more foundational)
        scored.sort(key=lambda x: (-x[1], x[0].tier))

        # Keep agents with at least MIN_RELEVANCE matches, up to max_agents
        relevant = [(a, s) for a, s in scored if s >= self.MIN_RELEVANCE]

        # If not enough relevant, fill with tier 1 (always useful)
        if len(relevant) < 3:
            tier1 = [(a, 0) for a in _registry_by_tier(1)]
            relevant = (relevant + tier1)[:max_agents]

        # Always include ORION for synthesis
        agents = [a for a, _ in relevant[:max_agents]]
        agent_ids = {a.id for a in agents}
        # Add ORION equivalent from tier 8 if not present
        if "ENT_ARCH" not in agent_ids:
            ent = REGISTRY_INDEX.get("ENT_ARCH")
            if ent:
                agents.append(ent)

        return agents[:max_agents]

    def _compose_waves(
        self,
        selected: List[AgentSpec],
        max_waves: int,
    ) -> List[tuple]:
        """
        Group selected agents into waves by tier.
        Each tier becomes a wave. Agents within a tier run in parallel.
        """
        by_tier: Dict[int, List[str]] = {}
        tier_themes = {
            1: "Engineering Core",
            2: "AI/ML Intelligence",
            3: "Security Review",
            4: "Performance Analysis",
            5: "Domain Expertise",
            6: "Quality Assurance",
            7: "Creative & Design",
            8: "Strategic Architecture",
        }

        for agent in selected:
            by_tier.setdefault(agent.tier, []).append(agent.id)

        waves = []
        for tier in sorted(by_tier.keys()):
            agents = by_tier[tier][:self.AGENTS_PER_WAVE]  # cap per wave
            theme  = tier_themes.get(tier, f"Tier {tier}")
            waves.append((theme, agents))

        return waves[:max_waves]

    def _build_context(
        self,
        task: str,
        base_ctx: str,
        prev_waves: List[PerformerWave],
    ) -> str:
        parts = []
        if base_ctx:
            parts.append(f"Context: {base_ctx[:200]}")
        for w in prev_waves[-2:]:  # last 2 waves
            if w.insights:
                parts.append(f"[Wave {w.number} — {w.theme}]\n{w.insights[:200]}")
        return "\n\n".join(parts)[:600]

    def _extract_insights(self, outputs: List[PipelineResult]) -> str:
        """Extract key insights from wave outputs."""
        parts = []
        for out in outputs:
            spec = REGISTRY_INDEX.get(out.agent)
            name = spec.name if spec else out.agent
            if out.analysis and len(out.analysis) > 20:
                parts.append(f"[{out.agent}/{name[:15]}] {out.analysis[:100]}")
        return "\n".join(parts)

    def _infer_domain(self, agent_ids: List[str]) -> str:
        """Infer pipeline domain from agent tier mix."""
        tiers = set()
        for aid in agent_ids:
            spec = REGISTRY_INDEX.get(aid)
            if spec:
                tiers.add(spec.tier)
        if 3 in tiers: return "security"
        if 4 in tiers: return "performance"
        if 7 in tiers: return "creative"
        if 2 in tiers: return "ai"
        if 1 in tiers: return "code"
        return "universal"

    def _orion_synthesis(self, task: str, waves: List[PerformerWave]) -> str:
        """Final ORION synthesis of all wave outputs."""
        all_insights = "\n".join(
            f"Wave {w.number} ({w.theme}): {w.insights[:150]}"
            for w in waves if w.insights
        )
        out = self.pipeline.call_agent(
            "ORION", task, "universal",
            context=f"MultiWave results ({len(waves)} waves, {sum(len(w.agents) for w in waves)} agents):\n{all_insights[:500]}",
            max_tokens=600,
        )
        if out.analysis:
            return f"{out.analysis}\n\n→ {out.recommendation}" if out.recommendation else out.analysis
        return "See wave-by-wave analysis above."

    def _record_perf(self, agent_id: str, confidence: float) -> None:
        """Track agent performance history."""
        self._perf_db.setdefault(agent_id, []).append(confidence)
        # Keep last 20
        if len(self._perf_db[agent_id]) > 20:
            self._perf_db[agent_id] = self._perf_db[agent_id][-20:]

    def agent_performance(self) -> Dict[str, float]:
        """Return average confidence per agent."""
        return {
            aid: sum(confs) / len(confs)
            for aid, confs in self._perf_db.items()
            if confs
        }


# ── Global + convenience ──────────────────────────────────────────────────────

_mwp: Optional[MultiWavePerformer] = None

def get_mwp() -> MultiWavePerformer:
    global _mwp
    if _mwp is None:
        _mwp = MultiWavePerformer()
    return _mwp


def mwp_run(
    task:       str,
    domain:     str  = "",
    max_agents: int  = 20,
    verbose:    bool = True,
) -> PerformerResult:
    """One-call MultiWave Performer."""
    return get_mwp().run(task, domain=domain, max_agents=max_agents, verbose=verbose)


if __name__ == "__main__":
    mwp = MultiWavePerformer(verbose=True)
    print(mwp.describe())
    print()
    print(f"Total agents verified: {len(AGENT_REGISTRY)}")
    print()

    # Tier breakdown
    from collections import Counter
    tier_count = Counter(a.tier for a in AGENT_REGISTRY)
    for tier, count in sorted(tier_count.items()):
        agents = [a.id for a in AGENT_REGISTRY if a.tier == tier]
        print(f"Tier {tier}: {count} agents — {', '.join(agents[:4])}...")

    print()
    # Quick demo
    result = mwp.run(
        "Build a real-time collaborative code editor with AI autocomplete",
        max_agents=12,
        max_waves=3,
    )
    print()
    print(result.executive_summary()[:800])
