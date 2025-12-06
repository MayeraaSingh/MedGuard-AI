"""
MedGuard AI - Agent Orchestrator (Google ADK)
Phase 2: Core Agent Architecture with Google ADK

Coordinates the execution of all ADK-based agents in the validation pipeline:
1. Validation Agent → validates against external sources
2. Enrichment Agent → adds additional information
3. QA Agent → resolves conflicts and scores confidence
4. Directory Agent → exports results and manages review queue

Pipeline Flow:
Input Data → Validation (ADK) → Enrichment (ADK) → QA (ADK) → Directory Management → Output
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workers.validation_agent_adk import ValidationAgentADK
from app.workers.enrichment_agent_adk import EnrichmentAgentADK
from app.workers.qa_agent_adk import QAAgentADK
from app.workers.directory_agent_adk import DirectoryAgentADK


class AgentOrchestratorADK:
    """
    Orchestrates the multi-agent validation pipeline using Google ADK agents.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize orchestrator with all ADK agents.
        
        Args:
            config: Configuration dictionary for agents
        """
        self.config = config or {}
        
        # Initialize ADK agents
        self.validation_agent = ValidationAgentADK(self.config.get("validation", {}))
        self.enrichment_agent = EnrichmentAgentADK(self.config.get("enrichment", {}))
        self.qa_agent = QAAgentADK(self.config.get("qa", {}))
        self.directory_agent = DirectoryAgentADK(self.config.get("directory", {}))
        
        # Pipeline metrics
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "duration_seconds": 0,
            "providers_processed": 0,
            "providers_succeeded": 0,
            "providers_failed": 0,
            "stage_durations": {}
        }
    
    def process_providers(self, providers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run full validation pipeline on a list of providers using ADK agents.
        
        Args:
            providers: List of provider dictionaries
            
        Returns:
            Pipeline execution summary with results
        """
        self.metrics["start_time"] = time.time()
        self.metrics["providers_processed"] = len(providers)
        
        print("=" * 70)
        print("MEDGUARD AI - MULTI-AGENT VALIDATION PIPELINE (Google ADK)")
        print("=" * 70)
        print(f"Processing {len(providers)} providers with ADK agents...")
        print()
        
        # Stage 1: Validation (ADK)
        print("Stage 1/4: Validation Agent (ADK) - Verifying data against external sources")
        print("-" * 70)
        stage_start = time.time()
        
        validation_results = self.validation_agent.validate_batch(providers)
        
        self.metrics["stage_durations"]["validation"] = time.time() - stage_start
        print(f"✓ Validation complete ({self.metrics['stage_durations']['validation']:.2f}s)")
        print()
        
        # Stage 2: Enrichment (ADK)
        print("Stage 2/4: Enrichment Agent (ADK) - Adding additional information")
        print("-" * 70)
        stage_start = time.time()
        
        enrichment_results = self.enrichment_agent.enrich_batch(providers, validation_results)
        
        self.metrics["stage_durations"]["enrichment"] = time.time() - stage_start
        print(f"✓ Enrichment complete ({self.metrics['stage_durations']['enrichment']:.2f}s)")
        print()
        
        # Stage 3: Quality Assurance (ADK)
        print("Stage 3/4: QA Agent (ADK) - Resolving conflicts and scoring confidence")
        print("-" * 70)
        stage_start = time.time()
        
        qa_results = self.qa_agent.assess_batch(providers, validation_results, enrichment_results)
        
        self.metrics["stage_durations"]["qa"] = time.time() - stage_start
        print(f"✓ QA assessment complete ({self.metrics['stage_durations']['qa']:.2f}s)")
        print()
        
        # Stage 4: Directory Management (ADK)
        print("Stage 4/4: Directory Agent (ADK) - Generating exports and review queue")
        print("-" * 70)
        stage_start = time.time()
        
        directory_summary = self.directory_agent.process_results(
            providers, validation_results, enrichment_results, qa_results
        )
        
        self.metrics["stage_durations"]["directory"] = time.time() - stage_start
        print(f"✓ Directory management complete ({self.metrics['stage_durations']['directory']:.2f}s)")
        print()
        
        # Calculate final metrics
        self.metrics["end_time"] = time.time()
        self.metrics["duration_seconds"] = self.metrics["end_time"] - self.metrics["start_time"]
        
        # Count successes/failures
        for qa_result in qa_results:
            if qa_result.get("status") in ["approved", "needs_review"]:
                self.metrics["providers_succeeded"] += 1
            else:
                self.metrics["providers_failed"] += 1
        
        # Build summary
        summary = {
            "pipeline_status": "completed",
            "pipeline_type": "Google ADK",
            "metrics": self.metrics,
            "validation_results": validation_results,
            "enrichment_results": enrichment_results,
            "qa_results": qa_results,
            "directory_summary": directory_summary
        }
        
        # Print summary
        self._print_summary(summary)
        
        return summary
    
    def process_single_provider(self, provider: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run pipeline on a single provider using ADK agents.
        
        Args:
            provider: Provider dictionary
            
        Returns:
            Complete validation result
        """
        # Run through each agent
        validation_result = self.validation_agent.validate_provider(provider)
        enrichment_result = self.enrichment_agent.enrich_provider(provider, validation_result)
        qa_result = self.qa_agent.assess_provider(provider, validation_result, enrichment_result)
        
        return {
            "provider": provider,
            "validation": validation_result,
            "enrichment": enrichment_result,
            "qa": qa_result
        }
    
    def _print_summary(self, summary: Dict[str, Any]):
        """
        Print pipeline execution summary.
        
        Args:
            summary: Pipeline summary dictionary
        """
        metrics = summary["metrics"]
        directory = summary["directory_summary"]
        
        print("=" * 70)
        print("PIPELINE EXECUTION SUMMARY (Google ADK)")
        print("=" * 70)
        print()
        
        print("PERFORMANCE METRICS")
        print("-" * 70)
        print(f"Total Duration: {metrics['duration_seconds']:.2f} seconds")
        print(f"Providers Processed: {metrics['providers_processed']}")
        print(f"Throughput: {metrics['providers_processed'] / metrics['duration_seconds'] * 3600:.0f} providers/hour")
        print()
        
        print("Stage Durations:")
        for stage, duration in metrics['stage_durations'].items():
            print(f"  {stage.capitalize()}: {duration:.2f}s")
        print()
        
        print("QUALITY METRICS")
        print("-" * 70)
        print(f"Succeeded: {metrics['providers_succeeded']}")
        print(f"Failed: {metrics['providers_failed']}")
        print(f"Success Rate: {metrics['providers_succeeded']/metrics['providers_processed']*100:.1f}%")
        print()
        
        print("DIRECTORY SUMMARY")
        print("-" * 70)
        print(f"Approved Providers: {directory.get('approved_providers', 0)}")
        print(f"Needs Review: {directory.get('needs_review', 0)}")
        print(f"Flagged: {directory.get('flagged_providers', 0)}")
        print(f"Review Queue Size: {directory.get('review_queue_size', 0)}")
        print()
        
        print("EXPORTS GENERATED")
        print("-" * 70)
        for export_type, export_path in directory.get('exports', {}).items():
            print(f"  {export_type}: {export_path}")
        print()
        
        print("=" * 70)
        print("✓ PIPELINE COMPLETE (Google ADK)")
        print("=" * 70)


def run_pipeline_from_csv(csv_path: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Convenience function to run ADK pipeline from CSV file.
    
    Args:
        csv_path: Path to CSV file with provider data
        config: Optional configuration
        
        Returns:
        Pipeline summary
    """
    import pandas as pd
    
    # Load providers from CSV
    df = pd.read_csv(csv_path)
    providers = df.to_dict('records')
    
    # Create orchestrator and run
    orchestrator = AgentOrchestratorADK(config)
    summary = orchestrator.process_providers(providers)
    
    return summary


if __name__ == "__main__":
    # Test with sample data
    test_providers = [
        {
            "provider_id": "9999123456",
            "npi": "9999123456",
            "first_name": "John",
            "last_name": "Smith",
            "degree": "MD",
            "specialty": "Cardiology",
            "phone": "(617) 555-1234",
            "email": "john.smith@hospital.com",
            "street_address": "123 Main St",
            "city": "Boston",
            "state": "MA",
            "zip_code": "02101",
            "license_number": "MD12345",
            "license_state": "MA",
            "medical_school": "Harvard Medical School",
            "graduation_year": 2010,
            "practice_type": "Hospital-based"
        }
    ]
    
    orchestrator = AgentOrchestratorADK()
    summary = orchestrator.process_providers(test_providers)
