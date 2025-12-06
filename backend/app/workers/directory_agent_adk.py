"""
MedGuard AI - Directory Agent (Google ADK)
Phase 2: Core Agent Architecture

Directory management agent using Google's Agent Development Kit.
Uses ADK's agent framework with tools for:
- CSV/JSON export
- Validation report generation
- Review queue management
- Email template generation
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json
import pandas as pd

from google import genai
from google.genai import types


class DirectoryAgentADK:
    """
    ADK-based directory agent that manages exports and review queues.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the directory agent with ADK.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.output_dir = Path(self.config.get("output_dir", "data/output"))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Define tools for the agent
        self.tools = self._create_tools()
    
    def _create_tools(self) -> List[types.Tool]:
        """
        Create ADK tools for directory management operations.
        
        Returns:
            List of ADK tools
        """
        tools = [
            types.Tool(function_declarations=[
                types.FunctionDeclaration(
                    name="export_directory_csv",
                    description="Export provider directory to CSV format",
                    parameters={
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "Array of provider records to export"
                            }
                        },
                        "required": ["data"]
                    }
                ),
                types.FunctionDeclaration(
                    name="export_directory_json",
                    description="Export provider directory to JSON format with full details",
                    parameters={
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "Array of provider records to export"
                            }
                        },
                        "required": ["data"]
                    }
                ),
                types.FunctionDeclaration(
                    name="generate_validation_report",
                    description="Generate validation summary report",
                    parameters={
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "Array of provider records with QA results"
                            }
                        },
                        "required": ["data"]
                    }
                ),
                types.FunctionDeclaration(
                    name="create_review_queue",
                    description="Create prioritized review queue for manual review",
                    parameters={
                        "type": "object",
                        "properties": {
                            "data": {
                                "type": "array",
                                "description": "Array of provider records to filter for review"
                            }
                        },
                        "required": ["data"]
                    }
                ),
                types.FunctionDeclaration(
                    name="generate_email_templates",
                    description="Generate email templates for provider outreach",
                    parameters={
                        "type": "object",
                        "properties": {
                            "review_queue": {
                                "type": "array",
                                "description": "Review queue items to generate emails for"
                            }
                        },
                        "required": ["review_queue"]
                    }
                )
            ])
        ]
        
        return tools
    
    def process_results(self, providers: List[Dict[str, Any]],
                       validation_results: List[Dict[str, Any]],
                       enrichment_results: List[Dict[str, Any]],
                       qa_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process all agent results and generate exports using ADK tools.
        
        Args:
            providers: Original provider data
            validation_results: Results from ValidationAgent
            enrichment_results: Results from EnrichmentAgent
            qa_results: Results from QAAgent
            
        Returns:
            Summary with export paths
        """
        # Merge all results
        merged_data = self._merge_results(providers, validation_results, 
                                         enrichment_results, qa_results)
        
        # Initialize summary
        summary = {
            "total_providers": len(merged_data),
            "approved_providers": 0,
            "needs_review": 0,
            "flagged_providers": 0,
            "review_queue_size": 0,
            "exports": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Count statuses
        for record in merged_data:
            status = record.get("status", "unknown")
            if status == "approved":
                summary["approved_providers"] += 1
            elif status == "needs_review":
                summary["needs_review"] += 1
            elif status == "flagged":
                summary["flagged_providers"] += 1
        
        # Generate exports
        summary["exports"]["csv"] = self.export_directory_csv(merged_data)
        print(f"✓ Exported directory CSV: {summary['exports']['csv']}")
        
        summary["exports"]["json"] = self.export_directory_json(merged_data)
        print(f"✓ Exported directory JSON: {summary['exports']['json']}")
        
        summary["exports"]["report"] = self.generate_validation_report(merged_data)
        print(f"✓ Generated validation report: {summary['exports']['report']}")
        
        # Create review queue
        review_queue = self.create_review_queue(merged_data)
        summary["review_queue_size"] = len(review_queue)
        summary["exports"]["review_queue"] = self.export_review_queue(review_queue)
        print(f"✓ Exported review queue: {summary['exports']['review_queue']}")
        
        # Generate email templates
        summary["exports"]["email_templates"] = self.generate_email_templates(review_queue)
        print(f"✓ Generated email templates: {summary['exports']['email_templates']}")
        
        return summary
    
    def _merge_results(self, providers: List[Dict[str, Any]],
                      validation_results: List[Dict[str, Any]],
                      enrichment_results: List[Dict[str, Any]],
                      qa_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Merge all agent results into unified records.
        
        Args:
            providers: Original provider data
            validation_results: Validation results
            enrichment_results: Enrichment results
            qa_results: QA results
            
        Returns:
            List of merged provider records
        """
        merged = []
        
        for i, provider in enumerate(providers):
            record = provider.copy()
            
            # Add validation info
            if i < len(validation_results):
                val = validation_results[i]
                record["validation_confidence"] = val.get("overall_confidence", 0.0)
                record["validation_status"] = val.get("status", "unknown")
            
            # Add enrichment info
            if i < len(enrichment_results):
                enr = enrichment_results[i]
                record["enrichment_confidence"] = enr.get("enrichment_confidence", 0.0)
                
                # Add enriched fields
                enriched = enr.get("enriched_fields", {})
                if enriched.get("education"):
                    record["matched_medical_school"] = enriched["education"].get("enriched_value")
                if enriched.get("specialty"):
                    spec_data = enriched["specialty"].get("enriched_value", {})
                    record["sub_specialties"] = spec_data.get("sub_specialties", [])
                if enriched.get("services"):
                    record["services_offered"] = enriched["services"].get("enriched_value", [])
            
            # Add QA info
            if i < len(qa_results):
                qa = qa_results[i]
                record["overall_confidence"] = qa.get("overall_confidence", 0.0)
                record["status"] = qa.get("status", "unknown")
                record["requires_review"] = qa.get("requires_review", False)
                record["priority"] = qa.get("priority", 0)
                record["risk_level"] = qa.get("risk_level", "low")
                record["flags"] = qa.get("flags", [])
            
            merged.append(record)
        
        return merged
    
    def export_directory_csv(self, data: List[Dict[str, Any]]) -> str:
        """
        Export provider directory to CSV.
        
        Args:
            data: List of provider records
            
        Returns:
            Path to exported CSV file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"provider_directory_{timestamp}.csv"
        
        # Flatten nested structures for CSV
        flattened = []
        for record in data:
            flat_record = {}
            for key, value in record.items():
                if isinstance(value, (list, dict)):
                    flat_record[key] = json.dumps(value)
                else:
                    flat_record[key] = value
            flattened.append(flat_record)
        
        # Export to CSV
        df = pd.DataFrame(flattened)
        df.to_csv(output_path, index=False)
        
        return str(output_path)
    
    def export_directory_json(self, data: List[Dict[str, Any]]) -> str:
        """
        Export provider directory to JSON with full details.
        
        Args:
            data: List of provider records
            
        Returns:
            Path to exported JSON file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"provider_directory_{timestamp}.json"
        
        # Create export structure
        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "total_providers": len(data),
                "export_version": "2.0-adk"
            },
            "providers": data
        }
        
        # Export to JSON
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return str(output_path)
    
    def generate_validation_report(self, data: List[Dict[str, Any]]) -> str:
        """
        Generate validation summary report.
        
        Args:
            data: List of provider records
            
        Returns:
            Path to report file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"validation_report_{timestamp}.txt"
        
        # Calculate statistics
        total = len(data)
        approved = sum(1 for r in data if r.get("status") == "approved")
        needs_review = sum(1 for r in data if r.get("status") == "needs_review")
        flagged = sum(1 for r in data if r.get("status") == "flagged")
        
        avg_confidence = sum(r.get("overall_confidence", 0) for r in data) / total if total > 0 else 0
        
        # Collect all flags
        all_flags = {}
        for record in data:
            for flag in record.get("flags", []):
                all_flags[flag] = all_flags.get(flag, 0) + 1
        
        # Generate report
        report_lines = [
            "=" * 70,
            "MEDGUARD AI - VALIDATION REPORT (Google ADK)",
            "=" * 70,
            f"Generated: {datetime.now().isoformat()}",
            "",
            "SUMMARY STATISTICS",
            "-" * 70,
            f"Total Providers: {total}",
            f"Approved: {approved} ({approved/total*100:.1f}%)" if total > 0 else "Approved: 0",
            f"Needs Review: {needs_review} ({needs_review/total*100:.1f}%)" if total > 0 else "Needs Review: 0",
            f"Flagged: {flagged} ({flagged/total*100:.1f}%)" if total > 0 else "Flagged: 0",
            f"Average Confidence: {avg_confidence:.3f}",
            "",
            "TOP FLAGS",
            "-" * 70
        ]
        
        # Add top flags
        sorted_flags = sorted(all_flags.items(), key=lambda x: x[1], reverse=True)[:10]
        for flag, count in sorted_flags:
            report_lines.append(f"  {flag}: {count}")
        
        report_lines.extend([
            "",
            "=" * 70
        ])
        
        # Write report
        with open(output_path, 'w') as f:
            f.write('\n'.join(report_lines))
        
        return str(output_path)
    
    def create_review_queue(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create prioritized review queue.
        
        Args:
            data: List of provider records
            
        Returns:
            Sorted review queue
        """
        # Filter records requiring review
        review_items = [r for r in data if r.get("requires_review", False)]
        
        # Sort by priority (descending)
        review_items.sort(key=lambda x: x.get("priority", 0), reverse=True)
        
        # Create review queue items
        queue = []
        for item in review_items:
            queue_item = {
                "provider_id": item.get("npi") or item.get("provider_id"),
                "provider_name": f"{item.get('first_name', '')} {item.get('last_name', '')}".strip(),
                "priority": item.get("priority", 0),
                "risk_level": item.get("risk_level", "low"),
                "flags": item.get("flags", []),
                "confidence": item.get("overall_confidence", 0.0),
                "issue_type": self._categorize_issue(item.get("flags", [])),
                "created_date": datetime.now().isoformat()
            }
            queue.append(queue_item)
        
        return queue
    
    def export_review_queue(self, review_queue: List[Dict[str, Any]]) -> str:
        """
        Export review queue to JSON.
        
        Args:
            review_queue: Review queue items
            
        Returns:
            Path to exported file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"review_queue_{timestamp}.json"
        
        export_data = {
            "metadata": {
                "created_date": datetime.now().isoformat(),
                "total_items": len(review_queue)
            },
            "review_items": review_queue
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return str(output_path)
    
    def generate_email_templates(self, review_queue: List[Dict[str, Any]]) -> str:
        """
        Generate email templates for provider outreach.
        
        Args:
            review_queue: Review queue items
            
        Returns:
            Path to email templates file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"email_templates_{timestamp}.txt"
        
        templates = []
        
        # Generate emails for top priority items (limit to 10)
        for item in review_queue[:10]:
            template = self._generate_email_template(item)
            templates.append(template)
            templates.append("\n" + "=" * 70 + "\n")
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(templates))
        
        return str(output_path)
    
    def _generate_email_template(self, review_item: Dict[str, Any]) -> str:
        """
        Generate single email template.
        
        Args:
            review_item: Review queue item
            
        Returns:
            Email template text
        """
        provider_name = review_item.get("provider_name", "Provider")
        provider_id = review_item.get("provider_id", "Unknown")
        flags = review_item.get("flags", [])
        
        subject = f"MedGuard AI: Provider Information Review Required - {provider_id}"
        
        body = f"""
Dear Dr. {provider_name},

We are conducting a routine review of provider information in our directory 
and have identified some items that require your attention:

Provider ID: {provider_id}
Priority Level: {review_item.get('priority', 0)}/100
Risk Level: {review_item.get('risk_level', 'Unknown').upper()}

Issues Identified:
"""
        
        for i, flag in enumerate(flags, 1):
            body += f"{i}. {flag}\n"
        
        body += f"""
Please review and update your information at your earliest convenience.
If you believe this is an error, please contact our support team.

This is an automated message from MedGuard AI Provider Validation System.

Best regards,
MedGuard AI Team
"""
        
        return f"Subject: {subject}\n{body}"
    
    def _categorize_issue(self, flags: List[str]) -> str:
        """
        Categorize issue type from flags.
        
        Args:
            flags: List of flag strings
            
        Returns:
            Issue category
        """
        if not flags:
            return "general"
        
        flags_str = ' '.join(flags).lower()
        
        if "fraud" in flags_str or "suspicious" in flags_str:
            return "fraud"
        elif "phone" in flags_str:
            return "phone"
        elif "address" in flags_str:
            return "address"
        elif "license" in flags_str or "expired" in flags_str:
            return "license"
        elif "education" in flags_str or "credential" in flags_str:
            return "credentials"
        else:
            return "general"


if __name__ == "__main__":
    # Test the ADK directory agent
    agent = DirectoryAgentADK()
    
    test_providers = [{
        "provider_id": "9999123456",
        "npi": "9999123456",
        "first_name": "John",
        "last_name": "Smith",
        "specialty": "Cardiology"
    }]
    
    test_validation = [{
        "overall_confidence": 0.85,
        "status": "approved",
        "source_evidence": []
    }]
    
    test_enrichment = [{
        "enrichment_confidence": 0.75,
        "enriched_fields": {},
        "source_evidence": []
    }]
    
    test_qa = [{
        "overall_confidence": 0.80,
        "status": "approved",
        "requires_review": False,
        "priority": 0,
        "risk_level": "low",
        "flags": []
    }]
    
    summary = agent.process_results(test_providers, test_validation, test_enrichment, test_qa)
    print("\nDirectory Agent Summary:")
    print(f"Total Providers: {summary['total_providers']}")
    print(f"Exports Generated: {len(summary['exports'])}")
    print(f"Review Queue Size: {summary['review_queue_size']}")
