"""
Android Security Lab - Report Generation

Generates JSON and human-readable security reports.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from ..config import get_settings, Severity
from ..models import SecurityAudit, SecurityReport
import logging

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Security report generator."""
    
    def __init__(self):
        self.settings = get_settings()
        self.console = Console()
        
        # Create reports directory
        self.settings.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_json_report(self, report: SecurityReport) -> str:
        """
        Generate JSON security report.
        
        Args:
            report: SecurityReport to generate
            
        Returns:
            Path to generated JSON file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"security_report_{report.device_id}_{timestamp}.json"
        filepath = self.settings.reports_dir / filename
        
        report_data = {
            "device_id": report.device_id,
            "device_name": report.device_name,
            "timestamp": report.timestamp.isoformat(),
            "authorized": report.authorized,
            "score": report.score,
            "findings": [
                {
                    "id": f.id,
                    "severity": f.severity.value,
                    "title": f.title,
                    "description": f.description,
                    "recommendation": f.recommendation,
                    "category": f.category
                }
                for f in report.findings
            ],
            "recommendations": report.recommendations,
            "summary": {
                "total_findings": len(report.findings),
                "high_severity": len([f for f in report.findings if f.severity == Severity.HIGH]),
                "medium_severity": len([f for f in report.findings if f.severity == Severity.MEDIUM]),
                "low_severity": len([f for f in report.findings if f.severity == Severity.LOW]),
                "info": len([f for f in report.findings if f.severity == Severity.INFO])
            }
        }
        
        with open(filepath, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        
        logger.info(f"JSON report generated: {filepath}")
        return str(filepath)
    
    def print_terminal_report(self, report: SecurityReport) -> None:
        """
        Print human-readable terminal report using Rich.
        
        Args:
            report: SecurityReport to print
        """
        # Clear console
        self.console.clear()
        
        # Header
        header = Text()
        header.append("🔍 ANDROID SECURITY LAB - SECURITY REPORT", style="bold green")
        header.append(f"\n\nDevice: {report.device_name} ({report.device_id})", style="cyan")
        header.append(f"\nTimestamp: {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}", style="dim")
        header.append(f"\nAuthorized: {'✓ Yes' if report.authorized else '✗ No'}", 
                     style="green" if report.authorized else "red")
        
        self.console.print(Panel(header, border_style="green"))
        
        # Score
        score_color = "green" if report.score >= 80 else "yellow" if report.score >= 60 else "red"
        score_text = Text()
        score_text.append(f"\nSecurity Score: {report.score}/100", style=f"bold {score_color}")
        
        # Score bar
        bar_length = 40
        filled = int(report.score / 100 * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        score_text.append(f"\n\n[{bar}] {report.score}%", style=score_color)
        
        self.console.print(Panel(score_text, border_style=score_color))
        
        # Findings table
        findings_table = Table(title="Security Findings", show_header=True, header_style="bold magenta")
        findings_table.add_column("Severity", style="bold", width=10)
        findings_table.add_column("Title", width=40)
        findings_table.add_column("Category", width=20)
        findings_table.add_column("Recommendation", width=50)
        
        for finding in report.findings:
            severity_color = {
                Severity.HIGH: "red",
                Severity.MEDIUM: "yellow",
                Severity.LOW: "blue",
                Severity.INFO: "dim"
            }.get(finding.severity, "white")
            
            findings_table.add_row(
                Text(finding.severity.value, style=severity_color),
                finding.title,
                finding.category,
                finding.recommendation
            )
        
        self.console.print(findings_table)
        
        # Summary
        summary = Text()
        summary.append("\n📊 SUMMARY", style="bold cyan")
        summary.append(f"\n\nTotal Findings: {len(report.findings)}")
        
        high_count = len([f for f in report.findings if f.severity == Severity.HIGH])
        medium_count = len([f for f in report.findings if f.severity == Severity.MEDIUM])
        low_count = len([f for f in report.findings if f.severity == Severity.LOW])
        info_count = len([f for f in report.findings if f.severity == Severity.INFO])
        
        summary.append(f"\n🔴 High: {high_count}", style="red" if high_count > 0 else "dim")
        summary.append(f"\n🟡 Medium: {medium_count}", style="yellow" if medium_count > 0 else "dim")
        summary.append(f"\n🔵 Low: {low_count}", style="blue" if low_count > 0 else "dim")
        summary.append(f"\n⚪ Info: {info_count}", style="dim")
        
        self.console.print(Panel(summary, border_style="cyan"))
        
        # Recommendations
        if report.recommendations:
            rec_text = Text()
            rec_text.append("\n💡 RECOMMENDATIONS", style="bold yellow")
            for i, rec in enumerate(report.recommendations, 1):
                rec_text.append(f"\n\n{i}. {rec}")
            
            self.console.print(Panel(rec_text, border_style="yellow"))
        
        # Footer
        footer = Text()
        footer.append("\n" + "="*60, style="dim")
        footer.append("\nAndroid Security Lab v1.0", style="dim")
        footer.append("\nFor authorized educational use only", style="dim")
        
        self.console.print(footer)
    
    def generate_summary_report(self, reports: list[SecurityReport]) -> dict:
        """
        Generate summary report from multiple device reports.
        
        Args:
            reports: List of SecurityReport objects
            
        Returns:
            Summary statistics
        """
        if not reports:
            return {"message": "No reports to summarize"}
        
        total_findings = sum(len(r.findings) for r in reports)
        avg_score = sum(r.score for r in reports) / len(reports)
        
        high_count = sum(
            len([f for f in r.findings if f.severity == Severity.HIGH])
            for r in reports
        )
        
        return {
            "total_devices": len(reports),
            "average_score": round(avg_score, 2),
            "total_findings": total_findings,
            "high_severity_findings": high_count,
            "devices_above_80": len([r for r in reports if r.score >= 80]),
            "devices_below_60": len([r for r in reports if r.score < 60])
        }


# Singleton instance
report_generator = ReportGenerator()
