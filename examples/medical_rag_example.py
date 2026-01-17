"""
Medical RAG Example: Multi-Agent System with Meta-Cognitive Reasoning

This example demonstrates:
1. Loading domain-specific medical documents
2. Creating specialized subagents for diabetes and COPD
3. Using the meta-cognitive reasoning framework
4. Optimizing with GEPA
5. Tracking with MLflow
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import dspy
from src.utils.config import config
from src.utils.vector_store import VectorStore, DocumentChunk
from src.tools.vector_search_tool import VectorSearchTool
from src.agents.subagent import DomainSubagent
from src.agents.meta_cognitive_agent import MetaCognitiveReasoningAgent
from src.optimizers.gepa_config import (
    GEPAConfig,
    create_gepa_optimizer,
    create_composite_metric,
    GroundednessMetric,
    CompletenessMetric,
    ConfidenceAccuracyMetric
)
from src.utils.mlflow_integration import MLflowTracker, enable_dspy_autologging
from src.metrics.evaluation import create_evaluation_suite, evaluate_predictions


# ========== Step 1: Sample Medical Documents ==========

DIABETES_DOCUMENTS = [
    {
        'text': (
            "Diabetes mellitus is a metabolic disorder characterized by high blood sugar levels. "
            "Type 1 diabetes is caused by autoimmune destruction of pancreatic beta cells, leading to "
            "absolute insulin deficiency. Type 2 diabetes is characterized by insulin resistance and "
            "relative insulin deficiency. Management includes lifestyle modifications, oral hypoglycemic "
            "agents like metformin, and insulin therapy when needed. Target HbA1c levels are typically "
            "below 7% for most adults. Common complications include diabetic nephropathy, retinopathy, "
            "and neuropathy. Regular monitoring of blood glucose and HbA1c is essential."
        ),
        'source': 'diabetes_overview.pdf',
        'metadata': {'category': 'pathophysiology', 'year': 2024}
    },
    {
        'text': (
            "Metformin is the first-line medication for type 2 diabetes. It works by decreasing hepatic "
            "glucose production and improving insulin sensitivity. Common side effects include "
            "gastrointestinal disturbances. It should be used with caution in patients with renal "
            "impairment (eGFR < 30 mL/min). SGLT2 inhibitors like empagliflozin provide cardiovascular "
            "and renal benefits. GLP-1 receptor agonists like semaglutide offer weight loss benefits "
            "and cardiovascular protection. Insulin therapy is indicated when oral agents are insufficient."
        ),
        'source': 'diabetes_treatment.pdf',
        'metadata': {'category': 'pharmacotherapy', 'year': 2024}
    },
    {
        'text': (
            "Diabetic ketoacidosis (DKA) is a life-threatening complication characterized by hyperglycemia, "
            "ketosis, and metabolic acidosis. It typically occurs in type 1 diabetes but can occur in type 2. "
            "Classic presentation includes polyuria, polydipsia, nausea, vomiting, and abdominal pain. "
            "Laboratory findings show glucose > 250 mg/dL, pH < 7.3, bicarbonate < 18 mEq/L, and positive "
            "ketones. Treatment involves IV fluids, insulin infusion, and electrolyte replacement, "
            "particularly potassium. Prevention includes patient education on sick day management."
        ),
        'source': 'dka_management.pdf',
        'metadata': {'category': 'emergency', 'year': 2024}
    }
]

COPD_DOCUMENTS = [
    {
        'text': (
            "Chronic Obstructive Pulmonary Disease (COPD) is a progressive lung disease characterized by "
            "airflow limitation that is not fully reversible. The primary risk factor is cigarette smoking. "
            "Diagnosis is confirmed by spirometry showing FEV1/FVC < 0.70 post-bronchodilator. "
            "Symptoms include dyspnea, chronic cough, and sputum production. GOLD classification stages "
            "severity based on FEV1 percentage predicted: GOLD 1 (≥80%), GOLD 2 (50-79%), GOLD 3 (30-49%), "
            "and GOLD 4 (<30%). Management includes smoking cessation, bronchodilators, and pulmonary rehabilitation."
        ),
        'source': 'copd_overview.pdf',
        'metadata': {'category': 'pathophysiology', 'year': 2024}
    },
    {
        'text': (
            "Bronchodilator therapy is the cornerstone of COPD management. Short-acting beta-2 agonists (SABA) "
            "like albuterol provide quick relief. Long-acting beta-2 agonists (LABA) like salmeterol and "
            "long-acting muscarinic antagonists (LAMA) like tiotropium are used for maintenance. "
            "Combination LABA/LAMA therapy improves lung function more than monotherapy. Inhaled corticosteroids "
            "(ICS) are added for patients with frequent exacerbations or eosinophilia. Triple therapy "
            "(LABA/LAMA/ICS) is used in severe cases. Proper inhaler technique is critical for efficacy."
        ),
        'source': 'copd_treatment.pdf',
        'metadata': {'category': 'pharmacotherapy', 'year': 2024}
    },
    {
        'text': (
            "COPD exacerbations are acute worsening of respiratory symptoms requiring additional therapy. "
            "Common triggers include viral infections, bacterial infections, and air pollution. "
            "Management includes increased bronchodilator use, systemic corticosteroids (prednisone 40mg "
            "for 5 days), and antibiotics if bacterial infection is suspected. Oxygen therapy should maintain "
            "SpO2 88-92% to avoid hypercapnia. Severe exacerbations may require non-invasive ventilation (NIV) "
            "or mechanical ventilation. Prevention includes vaccination against influenza and pneumococcus."
        ),
        'source': 'copd_exacerbation.pdf',
        'metadata': {'category': 'emergency', 'year': 2024}
    }
]


# ========== Step 2: Training Examples ==========

def create_training_examples():
    """Create training examples for GEPA optimization"""

    examples = [
        dspy.Example(
            question="What is the first-line treatment for type 2 diabetes?",
            answer="Metformin is the first-line medication for type 2 diabetes, as it decreases hepatic glucose production and improves insulin sensitivity."
        ).with_inputs('question'),

        dspy.Example(
            question="How is COPD diagnosed?",
            answer="COPD is diagnosed by spirometry showing FEV1/FVC < 0.70 post-bronchodilator, indicating airflow limitation."
        ).with_inputs('question'),

        dspy.Example(
            question="What are the laboratory findings in diabetic ketoacidosis?",
            answer="DKA laboratory findings include glucose > 250 mg/dL, pH < 7.3, bicarbonate < 18 mEq/L, and positive ketones."
        ).with_inputs('question'),

        dspy.Example(
            question="What is triple therapy for COPD?",
            answer="Triple therapy for COPD consists of LABA (long-acting beta-2 agonist), LAMA (long-acting muscarinic antagonist), and ICS (inhaled corticosteroid), used in severe cases."
        ).with_inputs('question'),

        dspy.Example(
            question="A patient with type 2 diabetes and cardiovascular disease needs better glucose control. What medication should be considered?",
            answer="GLP-1 receptor agonists like semaglutide or SGLT2 inhibitors like empagliflozin should be considered, as they provide cardiovascular protection in addition to glucose control."
        ).with_inputs('question'),

        dspy.Example(
            question="How should oxygen be managed in a COPD exacerbation?",
            answer="In COPD exacerbations, oxygen therapy should target SpO2 of 88-92% to maintain adequate oxygenation while avoiding hypercapnia."
        ).with_inputs('question')
    ]

    return examples


# ========== Step 3: Main Example Function ==========

def main():
    """
    Main example demonstrating the full multi-agent RAG system.
    """

    print("=" * 70)
    print("Multi-Agent RAG with Meta-Cognitive Reasoning - Medical Example")
    print("=" * 70)

    # Initialize DSPy with OpenAI
    lm = dspy.OpenAI(model=config.student_model, max_tokens=2000)
    dspy.settings.configure(lm=lm)

    # Initialize MLflow tracking
    tracker = MLflowTracker(
        tracking_uri=config.mlflow_tracking_uri,
        experiment_name=config.mlflow_experiment_name
    )

    tracker.start_run(run_name="medical_rag_example", tags={'type': 'demo'})

    try:
        # ========== Step 4: Create Vector Stores ==========
        print("\n[1/7] Creating vector stores for diabetes and COPD...")

        diabetes_store = VectorStore(
            embedding_model=config.embedding_model,
            index_path=config.vector_db_path / "diabetes"
        )

        copd_store = VectorStore(
            embedding_model=config.embedding_model,
            index_path=config.vector_db_path / "copd"
        )

        # Add documents
        diabetes_store.add_documents(
            DIABETES_DOCUMENTS,
            domain='diabetes',
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )

        copd_store.add_documents(
            COPD_DOCUMENTS,
            domain='copd',
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap
        )

        # Save vector stores
        diabetes_store.save()
        copd_store.save()

        # Log stats to MLflow
        diabetes_stats = diabetes_store.get_domain_stats()
        copd_stats = copd_store.get_domain_stats()
        tracker.log_vector_store_stats({**diabetes_stats, **copd_stats})

        print(f"  ✓ Diabetes: {diabetes_stats}")
        print(f"  ✓ COPD: {copd_stats}")

        # ========== Step 5: Create Subagents ==========
        print("\n[2/7] Creating domain-specialized subagents...")

        # Create tools
        diabetes_tool = VectorSearchTool(
            vector_store=diabetes_store,
            domain='diabetes',
            top_k=3
        )

        copd_tool = VectorSearchTool(
            vector_store=copd_store,
            domain='copd',
            top_k=3
        )

        # Create subagents
        diabetes_agent = DomainSubagent(
            domain='diabetes',
            vector_search_tool=diabetes_tool,
            max_iterations=3
        )

        copd_agent = DomainSubagent(
            domain='copd',
            vector_search_tool=copd_tool,
            max_iterations=3
        )

        subagents = {
            'diabetes': diabetes_agent,
            'copd': copd_agent
        }

        print(f"  ✓ Created {len(subagents)} specialized subagents")

        # ========== Step 6: Create Meta-Cognitive Agent ==========
        print("\n[3/7] Initializing meta-cognitive reasoning agent...")

        meta_agent = MetaCognitiveReasoningAgent(
            subagents=subagents,
            confidence_threshold=config.confidence_threshold,
            max_retry_attempts=config.max_retry_attempts
        )

        print("  ✓ Meta-cognitive agent ready")

        # ========== Step 7: Test Inference ==========
        print("\n[4/7] Testing inference with example question...")

        test_question = (
            "A 65-year-old patient has both type 2 diabetes and COPD. "
            "They are experiencing dyspnea and have blood glucose of 300 mg/dL. "
            "What are the key management considerations?"
        )

        print(f"\nQuestion: {test_question}\n")

        result = meta_agent(test_question)

        print("Answer:")
        print("-" * 70)
        print(result.answer)
        print("-" * 70)
        print(f"\nConfidence: {result.confidence:.3f}")
        print(f"Retry Count: {result.retry_count}")
        print(f"\nKey Caveats:")
        for caveat in result.caveats:
            print(f"  • {caveat}")

        # Log trace to MLflow
        tracker.log_trace(
            trace_id="test_inference_1",
            question=test_question,
            answer=result.answer,
            confidence=result.confidence,
            sub_solutions=result.sub_solutions,
            verification_trace=result.verification_trace,
            reflection_notes=result.reflection_notes,
            retry_count=result.retry_count
        )

        # ========== Step 8: Prepare for Optimization ==========
        print("\n[5/7] Preparing GEPA optimization...")

        # Create training set
        trainset = create_training_examples()
        print(f"  ✓ Created {len(trainset)} training examples")

        # Create composite metric
        metrics = [
            GroundednessMetric(weight=1.0),
            CompletenessMetric(weight=1.0),
            ConfidenceAccuracyMetric(weight=0.8)
        ]

        composite_metric = create_composite_metric(metrics)
        print(f"  ✓ Configured {len(metrics)} GEPA feedback metrics")

        # ========== Step 9: Run GEPA Optimization (Simulated) ==========
        print("\n[6/7] GEPA optimization (demonstration mode)...")
        print("  Note: Full GEPA optimization would run here with:")
        print(f"    - {config.gepa_num_iterations} iterations")
        print(f"    - Population size: {config.gepa_population_size}")
        print(f"    - Pareto frontier: {config.gepa_pareto_frontier_size}")
        print(f"    - Tool optimization: {config.enable_tool_optimization}")

        # Log optimization parameters
        tracker.log_params({
            'student_model': config.student_model,
            'reflection_model': config.reflection_model,
            'confidence_threshold': config.confidence_threshold,
            'max_retry_attempts': config.max_retry_attempts,
            'gepa_iterations': config.gepa_num_iterations,
            'population_size': config.gepa_population_size
        })

        # Evaluate on training set (before optimization)
        print("\n  Evaluating baseline performance...")
        eval_suite = create_evaluation_suite()

        predictions = []
        for example in trainset[:3]:  # Test on first 3 for demo
            pred = meta_agent(example.question)
            predictions.append(pred)

        baseline_metrics = evaluate_predictions(predictions, trainset[:3], eval_suite)

        print("  Baseline Metrics:")
        for metric_name, score in baseline_metrics.items():
            print(f"    {metric_name}: {score:.3f}")
            tracker.log_metrics({f'baseline_{metric_name}': score})

        # ========== Step 10: Summary ==========
        print("\n[7/7] Summary")
        print("=" * 70)
        print("✓ Multi-agent RAG system successfully initialized")
        print("✓ Meta-cognitive reasoning framework operational")
        print("✓ Vector stores created and indexed")
        print("✓ MLflow tracking enabled")
        print(f"✓ Results logged to: {tracker.tracking_uri}")
        print("\nNext steps:")
        print("  1. Run full GEPA optimization: optimize_system.py")
        print("  2. Deploy optimized system for production inference")
        print("  3. Monitor with MLflow UI: mlflow ui")
        print("=" * 70)

    finally:
        tracker.end_run()


if __name__ == "__main__":
    main()
