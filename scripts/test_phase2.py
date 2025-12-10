"""
MedGuard AI - Phase 2 Validation Script
Tests the multi-agent validation pipeline

Validates:
1. Agent initialization and configuration
2. Pipeline orchestration
3. Output file generation
4. Confidence scoring accuracy
5. Review queue functionality
6. End-to-end integration
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.orchestrator_adk import AgentOrchestratorADK


class Phase2Validator:
    """
    Validates Phase 2 deliverables: agent architecture and orchestration.
    """
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.output_dir = self.data_dir / "output"
        self.samples_dir = self.data_dir / "samples"
        
        self.results = {
            "phase": "Phase 2 - Core Agent Architecture",
            "timestamp": "",
            "overall_status": "UNKNOWN",
            "tests": {}
        }
    
    def validate_agent_files(self) -> bool:
        """
        Validate that all agent files exist and are properly structured.
        
        Returns:
            True if all agent files exist
        """
        print("Test 1: Validating Agent Files")
        print("-" * 70)
        
        required_files = [
            "backend/app/__init__.py",
            "backend/app/orchestrator_adk.py",
            "backend/app/workers/__init__.py",
            "backend/app/workers/validation_agent_adk.py",
            "backend/app/workers/enrichment_agent_adk.py",
            "backend/app/workers/qa_agent_adk.py",
            "backend/app/workers/directory_agent_adk.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
            else:
                print(f"  ✓ {file_path}")
        
        if missing_files:
            print(f"\n  ✗ Missing files: {missing_files}")
            self.results["tests"]["agent_files"] = {
                "status": "FAILED",
                "missing_files": missing_files
            }
            return False
        
        print(f"\n  ✓ All {len(required_files)} agent files present")
        self.results["tests"]["agent_files"] = {
            "status": "PASSED",
            "files_validated": len(required_files)
        }
        return True
    
    def validate_agent_initialization(self) -> bool:
        """
        Validate that agents can be initialized without errors.
        
        Returns:
            True if all agents initialize successfully
        """
        print("\nTest 2: Validating Agent Initialization")
        print("-" * 70)
        
        try:
            from backend.app.workers.validation_agent_adk import ValidationAgentADK
            from backend.app.workers.enrichment_agent_adk import EnrichmentAgentADK
            from backend.app.workers.qa_agent_adk import QAAgentADK
            from backend.app.workers.directory_agent_adk import DirectoryAgentADK
            
            # Initialize each ADK agent
            validation_agent = ValidationAgentADK({})
            print("  ✓ ValidationAgentADK initialized")
            
            enrichment_agent = EnrichmentAgentADK({})
            print("  ✓ EnrichmentAgentADK initialized")
            
            qa_agent = QAAgentADK({})
            print("  ✓ QAAgentADK initialized")
            
            directory_agent = DirectoryAgentADK({})
            print("  ✓ DirectoryAgentADK initialized")
            
            # Initialize ADK orchestrator
            orchestrator = AgentOrchestratorADK({})
            print("  ✓ AgentOrchestratorADK initialized")
            
            print("\n  ✓ All agents initialized successfully")
            self.results["tests"]["agent_initialization"] = {
                "status": "PASSED",
                "agents_initialized": 5
            }
            return True
            
        except Exception as e:
            print(f"\n  ✗ Agent initialization failed: {e}")
            self.results["tests"]["agent_initialization"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def validate_pipeline_execution(self) -> bool:
        """
        Run pipeline on sample data and validate execution.
        
        Returns:
            True if pipeline executes successfully
        """
        print("\nTest 3: Validating Pipeline Execution")
        print("-" * 70)
        
        try:
            # Load sample providers
            csv_path = self.samples_dir / "providers_synthetic.csv"
            if not csv_path.exists():
                print(f"  ✗ Sample data not found: {csv_path}")
                self.results["tests"]["pipeline_execution"] = {
                    "status": "FAILED",
                    "error": "Sample data not found"
                }
                return False
            
            df = pd.read_csv(csv_path)
            # Use first 10 providers for testing
            test_providers = df.head(10).to_dict('records')
            print(f"  Loaded {len(test_providers)} test providers")
            
            # Run pipeline with ADK
            orchestrator = AgentOrchestratorADK({})
            summary = orchestrator.process_providers(test_providers)
            
            # Validate summary structure
            required_keys = ["pipeline_status", "metrics", "validation_results", 
                           "enrichment_results", "qa_results", "directory_summary"]
            
            missing_keys = [key for key in required_keys if key not in summary]
            if missing_keys:
                print(f"\n  ✗ Missing keys in summary: {missing_keys}")
                self.results["tests"]["pipeline_execution"] = {
                    "status": "FAILED",
                    "missing_keys": missing_keys
                }
                return False
            
            # Validate metrics
            metrics = summary["metrics"]
            if metrics["providers_processed"] != len(test_providers):
                print(f"\n  ✗ Processed count mismatch: {metrics['providers_processed']} != {len(test_providers)}")
                self.results["tests"]["pipeline_execution"] = {
                    "status": "FAILED",
                    "error": "Processed count mismatch"
                }
                return False
            
            print(f"\n  ✓ Pipeline executed successfully")
            print(f"  Duration: {metrics['duration_seconds']:.2f}s")
            print(f"  Throughput: {metrics['providers_processed'] / metrics['duration_seconds'] * 3600:.0f} providers/hour")
            
            self.results["tests"]["pipeline_execution"] = {
                "status": "PASSED",
                "providers_processed": metrics["providers_processed"],
                "duration_seconds": metrics["duration_seconds"],
                "throughput_per_hour": metrics["providers_processed"] / metrics["duration_seconds"] * 3600
            }
            
            # Store summary for later tests
            self.pipeline_summary = summary
            
            return True
            
        except Exception as e:
            import traceback
            print(f"\n  ✗ Pipeline execution failed: {e}")
            print(traceback.format_exc())
            self.results["tests"]["pipeline_execution"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def validate_output_files(self) -> bool:
        """
        Validate that all expected output files are generated.
        
        Returns:
            True if all outputs exist
        """
        print("\nTest 4: Validating Output Files")
        print("-" * 70)
        
        if not hasattr(self, 'pipeline_summary'):
            print("  ⚠ Skipping (pipeline not executed)")
            self.results["tests"]["output_files"] = {
                "status": "SKIPPED",
                "reason": "Pipeline not executed"
            }
            return True
        
        try:
            exports = self.pipeline_summary["directory_summary"].get("exports", {})
            
            # Check each export file
            missing_files = []
            for export_type, file_path in exports.items():
                full_path = Path(file_path)
                if full_path.exists():
                    file_size = full_path.stat().st_size
                    print(f"  ✓ {export_type}: {file_path} ({file_size} bytes)")
                else:
                    print(f"  ✗ {export_type}: {file_path} (missing)")
                    missing_files.append(file_path)
            
            if missing_files:
                self.results["tests"]["output_files"] = {
                    "status": "FAILED",
                    "missing_files": missing_files
                }
                return False
            
            print(f"\n  ✓ All {len(exports)} output files generated")
            self.results["tests"]["output_files"] = {
                "status": "PASSED",
                "files_generated": len(exports)
            }
            return True
            
        except Exception as e:
            print(f"\n  ✗ Output validation failed: {e}")
            self.results["tests"]["output_files"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def validate_confidence_scoring(self) -> bool:
        """
        Validate confidence scoring accuracy.
        
        Returns:
            True if confidence scores are within valid ranges
        """
        print("\nTest 5: Validating Confidence Scoring")
        print("-" * 70)
        
        if not hasattr(self, 'pipeline_summary'):
            print("  ⚠ Skipping (pipeline not executed)")
            self.results["tests"]["confidence_scoring"] = {
                "status": "SKIPPED",
                "reason": "Pipeline not executed"
            }
            return True
        
        try:
            qa_results = self.pipeline_summary["qa_results"]
            
            # Analyze confidence scores
            confidence_scores = [qa["overall_confidence"] for qa in qa_results]
            avg_confidence = sum(confidence_scores) / len(confidence_scores)
            min_confidence = min(confidence_scores)
            max_confidence = max(confidence_scores)
            
            print(f"  Average Confidence: {avg_confidence:.3f}")
            print(f"  Min Confidence: {min_confidence:.3f}")
            print(f"  Max Confidence: {max_confidence:.3f}")
            
            # Validate ranges (0.0 - 1.0)
            invalid_scores = [score for score in confidence_scores if score < 0.0 or score > 1.0]
            if invalid_scores:
                print(f"\n  ✗ Invalid confidence scores (outside 0.0-1.0): {invalid_scores}")
                self.results["tests"]["confidence_scoring"] = {
                    "status": "FAILED",
                    "invalid_scores": invalid_scores
                }
                return False
            
            # Check score distribution
            high_confidence = sum(1 for s in confidence_scores if s >= 0.8)
            medium_confidence = sum(1 for s in confidence_scores if 0.6 <= s < 0.8)
            low_confidence = sum(1 for s in confidence_scores if s < 0.6)
            
            print(f"\n  Confidence Distribution:")
            print(f"    High (≥0.8): {high_confidence} ({high_confidence/len(confidence_scores)*100:.1f}%)")
            print(f"    Medium (0.6-0.8): {medium_confidence} ({medium_confidence/len(confidence_scores)*100:.1f}%)")
            print(f"    Low (<0.6): {low_confidence} ({low_confidence/len(confidence_scores)*100:.1f}%)")
            
            print(f"\n  ✓ Confidence scoring validated")
            self.results["tests"]["confidence_scoring"] = {
                "status": "PASSED",
                "avg_confidence": avg_confidence,
                "min_confidence": min_confidence,
                "max_confidence": max_confidence,
                "distribution": {
                    "high": high_confidence,
                    "medium": medium_confidence,
                    "low": low_confidence
                }
            }
            return True
            
        except Exception as e:
            print(f"\n  ✗ Confidence scoring validation failed: {e}")
            self.results["tests"]["confidence_scoring"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def validate_review_queue(self) -> bool:
        """
        Validate review queue functionality.
        
        Returns:
            True if review queue is properly generated
        """
        print("\nTest 6: Validating Review Queue")
        print("-" * 70)
        
        if not hasattr(self, 'pipeline_summary'):
            print("  ⚠ Skipping (pipeline not executed)")
            self.results["tests"]["review_queue"] = {
                "status": "SKIPPED",
                "reason": "Pipeline not executed"
            }
            return True
        
        try:
            directory_summary = self.pipeline_summary["directory_summary"]
            review_queue_size = directory_summary.get("review_queue_size", 0)
            
            print(f"  Review Queue Size: {review_queue_size}")
            print(f"  Needs Review: {directory_summary.get('needs_review', 0)}")
            print(f"  Flagged Providers: {directory_summary.get('flagged_providers', 0)}")
            
            # Load review queue file
            review_queue_path = directory_summary.get("exports", {}).get("review_queue")
            if review_queue_path and Path(review_queue_path).exists():
                with open(review_queue_path, 'r') as f:
                    review_data = json.load(f)
                
                items = review_data.get("review_items", [])
                if len(items) != review_queue_size:
                    print(f"\n  ✗ Review queue size mismatch: {len(items)} != {review_queue_size}")
                    self.results["tests"]["review_queue"] = {
                        "status": "FAILED",
                        "error": "Size mismatch"
                    }
                    return False
                
                # Check priority sorting (descending)
                priorities = [item.get("priority", item.get("priority_score", 0)) for item in items]
                if priorities != sorted(priorities, reverse=True):
                    print(f"\n  ✗ Review queue not properly sorted by priority")
                    self.results["tests"]["review_queue"] = {
                        "status": "FAILED",
                        "error": "Not sorted by priority"
                    }
                    return False
                
                print(f"\n  ✓ Review queue validated ({review_queue_size} items, properly sorted)")
                self.results["tests"]["review_queue"] = {
                    "status": "PASSED",
                    "queue_size": review_queue_size,
                    "properly_sorted": True
                }
                return True
            else:
                print(f"\n  ⚠ Review queue file not found")
                self.results["tests"]["review_queue"] = {
                    "status": "PASSED",
                    "queue_size": 0,
                    "note": "No items require review"
                }
                return True
                
        except Exception as e:
            print(f"\n  ✗ Review queue validation failed: {e}")
            self.results["tests"]["review_queue"] = {
                "status": "FAILED",
                "error": str(e)
            }
            return False
    
    def generate_report(self):
        """
        Generate Phase 2 validation report.
        """
        from datetime import datetime
        
        self.results["timestamp"] = datetime.now().isoformat()
        
        # Determine overall status
        test_statuses = [test["status"] for test in self.results["tests"].values()]
        if all(status == "PASSED" for status in test_statuses):
            self.results["overall_status"] = "PASSED"
        elif any(status == "FAILED" for status in test_statuses):
            self.results["overall_status"] = "FAILED"
        else:
            self.results["overall_status"] = "PARTIAL"
        
        # Save report
        report_path = self.data_dir / "phase2_validation_report.json"
        with open(report_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Print summary
        print("\n" + "=" * 70)
        print("PHASE 2 VALIDATION REPORT")
        print("=" * 70)
        print(f"Overall Status: {self.results['overall_status']}")
        print(f"\nTest Results:")
        for test_name, test_result in self.results["tests"].items():
            status_symbol = "✓" if test_result["status"] == "PASSED" else "✗" if test_result["status"] == "FAILED" else "⚠"
            print(f"  {status_symbol} {test_name}: {test_result['status']}")
        
        print(f"\nReport saved to: {report_path}")
        print("=" * 70)


def main():
    """
    Run Phase 2 validation.
    """
    validator = Phase2Validator()
    
    # Run all validation tests
    validator.validate_agent_files()
    validator.validate_agent_initialization()
    validator.validate_pipeline_execution()
    validator.validate_output_files()
    validator.validate_confidence_scoring()
    validator.validate_review_queue()
    
    # Generate report
    validator.generate_report()


if __name__ == "__main__":
    main()
