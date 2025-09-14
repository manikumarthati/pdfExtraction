"""
Cost tracking and monitoring utilities for OpenAI API usage
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, List
from dataclasses import dataclass, asdict

@dataclass
class UsageRecord:
    timestamp: str
    task_type: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    document_id: str = None
    response_time: float = None

class CostTracker:
    def __init__(self, log_file: str = 'usage_log.json'):
        self.log_file = log_file
        self.session_costs = []
    
    def log_usage(self, usage_data: Dict[str, Any], document_id: str = None) -> None:
        """Log usage data to file and session tracker"""
        
        if not usage_data or 'error' in usage_data:
            return
        
        record = UsageRecord(
            timestamp=datetime.now().isoformat(),
            task_type=usage_data.get('task_type', 'unknown'),
            model=usage_data.get('model', 'unknown'),
            input_tokens=usage_data.get('input_tokens', 0),
            output_tokens=usage_data.get('output_tokens', 0),
            total_tokens=usage_data.get('total_tokens', 0),
            estimated_cost=usage_data.get('estimated_cost', 0.0),
            document_id=document_id,
            response_time=usage_data.get('response_time')
        )
        
        # Add to session tracking
        self.session_costs.append(record)
        
        # Append to log file
        self._append_to_log(record)
    
    def _append_to_log(self, record: UsageRecord) -> None:
        """Append usage record to log file"""
        try:
            # Read existing log
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r') as f:
                    logs = json.load(f)
            else:
                logs = []
            
            # Add new record
            logs.append(asdict(record))
            
            # Write back
            with open(self.log_file, 'w') as f:
                json.dump(logs, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Could not log usage data: {e}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session costs"""
        if not self.session_costs:
            return {"total_cost": 0, "total_tokens": 0, "requests": 0}
        
        total_cost = sum(record.estimated_cost for record in self.session_costs)
        total_tokens = sum(record.total_tokens for record in self.session_costs)
        
        # Group by task type
        task_breakdown = {}
        for record in self.session_costs:
            task = record.task_type
            if task not in task_breakdown:
                task_breakdown[task] = {
                    "requests": 0,
                    "tokens": 0,
                    "cost": 0.0,
                    "models": set()
                }
            
            task_breakdown[task]["requests"] += 1
            task_breakdown[task]["tokens"] += record.total_tokens
            task_breakdown[task]["cost"] += record.estimated_cost
            task_breakdown[task]["models"].add(record.model)
        
        # Convert sets to lists for JSON serialization
        for task in task_breakdown:
            task_breakdown[task]["models"] = list(task_breakdown[task]["models"])
        
        return {
            "total_cost": round(total_cost, 6),
            "total_tokens": total_tokens,
            "requests": len(self.session_costs),
            "task_breakdown": task_breakdown,
            "average_cost_per_request": round(total_cost / len(self.session_costs), 6)
        }
    
    def get_cost_analysis(self, days: int = 7) -> Dict[str, Any]:
        """Analyze costs over specified period"""
        try:
            if not os.path.exists(self.log_file):
                return {"error": "No usage data available"}
            
            with open(self.log_file, 'r') as f:
                logs = json.load(f)
            
            # Filter by date range
            cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)
            recent_logs = [
                log for log in logs 
                if datetime.fromisoformat(log['timestamp']).timestamp() > cutoff_date
            ]
            
            if not recent_logs:
                return {"error": f"No usage data in last {days} days"}
            
            # Calculate totals
            total_cost = sum(log['estimated_cost'] for log in recent_logs)
            total_tokens = sum(log['total_tokens'] for log in recent_logs)
            
            # Model usage breakdown
            model_stats = {}
            for log in recent_logs:
                model = log['model']
                if model not in model_stats:
                    model_stats[model] = {"requests": 0, "tokens": 0, "cost": 0.0}
                
                model_stats[model]["requests"] += 1
                model_stats[model]["tokens"] += log['total_tokens']
                model_stats[model]["cost"] += log['estimated_cost']
            
            # Task type breakdown
            task_stats = {}
            for log in recent_logs:
                task = log['task_type']
                if task not in task_stats:
                    task_stats[task] = {"requests": 0, "tokens": 0, "cost": 0.0}
                
                task_stats[task]["requests"] += 1
                task_stats[task]["tokens"] += log['total_tokens']
                task_stats[task]["cost"] += log['estimated_cost']
            
            return {
                "period_days": days,
                "total_requests": len(recent_logs),
                "total_tokens": total_tokens,
                "total_cost": round(total_cost, 6),
                "average_cost_per_request": round(total_cost / len(recent_logs), 6),
                "model_breakdown": {k: {**v, "cost": round(v["cost"], 6)} for k, v in model_stats.items()},
                "task_breakdown": {k: {**v, "cost": round(v["cost"], 6)} for k, v in task_stats.items()}
            }
            
        except Exception as e:
            return {"error": f"Could not analyze costs: {e}"}
    
    def get_cost_optimization_suggestions(self) -> List[str]:
        """Provide suggestions for cost optimization"""
        suggestions = []
        
        if not self.session_costs:
            return ["No usage data available for optimization suggestions"]
        
        # Analyze current usage patterns
        task_costs = {}
        for record in self.session_costs:
            task = record.task_type
            if task not in task_costs:
                task_costs[task] = {"cost": 0, "count": 0, "models": set()}
            
            task_costs[task]["cost"] += record.estimated_cost
            task_costs[task]["count"] += 1
            task_costs[task]["models"].add(record.model)
        
        # Generate suggestions
        for task, data in task_costs.items():
            avg_cost = data["cost"] / data["count"]
            
            if task == "classification" and "gpt-4" in data["models"]:
                suggestions.append(f"Classification: Consider using gpt-3.5-turbo instead of gpt-4 (avg cost: ${avg_cost:.4f})")
            
            if task == "field_identification" and avg_cost > 0.01:
                suggestions.append(f"Field identification: High average cost ${avg_cost:.4f} - consider gpt-4o-mini")
            
            if task == "data_extraction" and "gpt-3.5-turbo" in data["models"]:
                suggestions.append(f"Data extraction: Using cheaper model may reduce accuracy. Current avg: ${avg_cost:.4f}")
        
        if not suggestions:
            suggestions.append("Current model selection appears optimized for the workload")
        
        return suggestions