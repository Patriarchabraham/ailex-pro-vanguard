"""AILEX Pro Vanguard — Example 5: MARY with 2026 LLM Knowledge"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ailex_pilot.mary_2026 import Mary2026, enrich_mary, mary_compare_models

m = Mary2026()

# LLM landscape
print("=== 2026 LLM Landscape ===")
print(m.describe_llm_landscape())

# Technique reference
print("\n=== RAG Techniques ===")
print(m.describe_techniques("RAG & Retrieval"))

# Model recommendation
print("\n=== Model Recommendation ===")
print(mary_compare_models("Build a multi-tenant AI SaaS with RAG and vector search"))

# Context injection (use in any prompt)
ctx = enrich_mary("Implement a RAG pipeline with reranking")
print(f"\n=== Context for MARY (first 300 chars) ===\n{ctx[:300]}")
