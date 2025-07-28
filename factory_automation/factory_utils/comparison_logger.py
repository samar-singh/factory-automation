"""Comparison logger for A/B testing orchestrator versions."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import pandas as pd

logger = logging.getLogger(__name__)

class ComparisonLogger:
    """Log and compare results between orchestrator v1 and v2 for A/B testing."""
    
    def __init__(self, log_dir: Optional[str] = None):
        """Initialize comparison logger.
        
        Args:
            log_dir: Directory to store comparison logs
        """
        if log_dir is None:
            from factory_config.settings import settings
            log_dir = settings.comparison_log_dir
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # CSV file for quick analysis
        self.csv_path = self.log_dir / "comparison_summary.csv"
        
        # Initialize CSV if it doesn't exist
        if not self.csv_path.exists():
            df = pd.DataFrame(columns=[
                'timestamp', 'email_id', 'orchestrator_version', 
                'processing_time', 'api_cost', 'decisions_made',
                'success', 'error', 'complexity_score'
            ])
            df.to_csv(self.csv_path, index=False)
    
    def log_processing(self, 
                      email_id: str,
                      orchestrator_version: str,
                      processing_time: float,
                      result: Dict[str, Any],
                      api_cost: Optional[float] = None) -> None:
        """Log processing results for comparison.
        
        Args:
            email_id: Unique email identifier
            orchestrator_version: "v1" or "v2"
            processing_time: Time taken to process in seconds
            result: Processing result dictionary
            api_cost: Estimated API cost (for v2)
        """
        timestamp = datetime.now().isoformat()
        
        # Calculate complexity score based on actions taken
        complexity_score = self._calculate_complexity(result)
        
        # Create log entry
        log_entry = {
            'timestamp': timestamp,
            'email_id': email_id,
            'orchestrator_version': orchestrator_version,
            'processing_time': processing_time,
            'api_cost': api_cost or 0.0,
            'decisions_made': len(result.get('actions_taken', [])),
            'success': result.get('success', False),
            'error': result.get('error', ''),
            'complexity_score': complexity_score,
            'full_result': result
        }
        
        # Save detailed log as JSON
        log_file = self.log_dir / f"{email_id}_{orchestrator_version}_{timestamp}.json"
        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)
        
        # Append to CSV for analysis
        df = pd.DataFrame([{
            'timestamp': timestamp,
            'email_id': email_id,
            'orchestrator_version': orchestrator_version,
            'processing_time': processing_time,
            'api_cost': api_cost or 0.0,
            'decisions_made': len(result.get('actions_taken', [])),
            'success': result.get('success', False),
            'error': result.get('error', ''),
            'complexity_score': complexity_score
        }])
        df.to_csv(self.csv_path, mode='a', header=False, index=False)
        
        logger.info(f"Logged {orchestrator_version} processing for {email_id}")
    
    def _calculate_complexity(self, result: Dict[str, Any]) -> int:
        """Calculate email complexity score based on processing result.
        
        Args:
            result: Processing result
            
        Returns:
            Complexity score (0-10)
        """
        score = 0
        
        # Check for various complexity indicators
        if result.get('multiple_attachments'):
            score += 2
        if result.get('requires_approval'):
            score += 2
        if result.get('special_instructions'):
            score += 3
        if result.get('modification_request'):
            score += 2
        if result.get('urgent_flag'):
            score += 1
            
        return min(score, 10)
    
    def generate_comparison_report(self) -> Dict[str, Any]:
        """Generate comparison report between v1 and v2.
        
        Returns:
            Comparison statistics and insights
        """
        df = pd.read_csv(self.csv_path)
        
        if df.empty:
            return {"error": "No data available for comparison"}
        
        # Group by orchestrator version
        v1_data = df[df['orchestrator_version'] == 'v1']
        v2_data = df[df['orchestrator_version'] == 'v2']
        
        report = {
            'total_emails_processed': {
                'v1': len(v1_data),
                'v2': len(v2_data)
            },
            'average_processing_time': {
                'v1': v1_data['processing_time'].mean() if len(v1_data) > 0 else 0,
                'v2': v2_data['processing_time'].mean() if len(v2_data) > 0 else 0
            },
            'success_rate': {
                'v1': (v1_data['success'].sum() / len(v1_data) * 100) if len(v1_data) > 0 else 0,
                'v2': (v2_data['success'].sum() / len(v2_data) * 100) if len(v2_data) > 0 else 0
            },
            'total_api_cost': {
                'v1': v1_data['api_cost'].sum(),
                'v2': v2_data['api_cost'].sum()
            },
            'average_complexity_handled': {
                'v1': v1_data['complexity_score'].mean() if len(v1_data) > 0 else 0,
                'v2': v2_data['complexity_score'].mean() if len(v2_data) > 0 else 0
            },
            'error_rate': {
                'v1': (v1_data['error'].notna().sum() / len(v1_data) * 100) if len(v1_data) > 0 else 0,
                'v2': (v2_data['error'].notna().sum() / len(v2_data) * 100) if len(v2_data) > 0 else 0
            }
        }
        
        # Add recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on comparison statistics.
        
        Args:
            stats: Comparison statistics
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        # Compare processing times
        if stats['average_processing_time']['v2'] > stats['average_processing_time']['v1'] * 1.5:
            recommendations.append("V2 is significantly slower - consider optimization or use V1 for simple emails")
        
        # Compare success rates
        if stats['success_rate']['v2'] > stats['success_rate']['v1'] + 10:
            recommendations.append("V2 shows better success rate - good candidate for complex emails")
        
        # Compare costs
        monthly_v2_cost = stats['total_api_cost']['v2'] * 30
        if monthly_v2_cost > 150:
            recommendations.append(f"V2 projected monthly cost (${monthly_v2_cost:.2f}) exceeds budget")
        
        # Compare complexity handling
        if stats['average_complexity_handled']['v2'] > stats['average_complexity_handled']['v1']:
            recommendations.append("V2 handles more complex scenarios effectively")
        
        return recommendations

# Global instance
comparison_logger = ComparisonLogger()