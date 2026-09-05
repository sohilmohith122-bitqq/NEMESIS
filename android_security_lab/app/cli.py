"""
Android Security Lab - CLI Interface

Command-line interface using Typer.
"""

import asyncio
import sys
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime

app = typer.Typer(
    name="android-security-lab",
    help="Android Security Lab - Educational cybersecurity testing tool",
    add_completion=False
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print("[green]Android Security Lab v1.0.0[/green]")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit"
    )
):
    """Android Security Lab - Educational cybersecurity testing tool."""
    pass


@app.command()
def scan(
    cidr: str = typer.Option("192.168.1.0/24", "--cidr", "-c", help="CIDR range to scan")
):
    """Scan network for discoverable devices."""
    from .discovery.scanner import scanner
    
    console.print(f"[cyan]Scanning network: {cidr}[/cyan]")
    
    async def _scan():
        try:
            result = await scanner.scan_network(cidr)
            
            if not result.devices:
                console.print("[yellow]No devices found[/yellow]")
                return
            
            table = Table(title="Discovered Devices", show_header=True, header_style="bold magenta")
            table.add_column("IP Address", style="cyan")
            table.add_column("Hostname", style="green")
            table.add_column("MAC Address")
            table.add_column("Manufacturer")
            table.add_column("Services")
            
            for device in result.devices:
                table.add_row(
                    device.ip_address,
                    device.hostname or "-",
                    device.mac_address or "-",
                    device.manufacturer or "-",
                    ", ".join(device.services) if device.services else "-"
                )
            
            console.print(table)
            console.print(f"\n[dim]Scan completed in {result.duration:.2f} seconds[/dim]")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    asyncio.run(_scan())


@app.command()
def devices():
    """List all registered devices."""
    from .authorization.devices import device_manager
    
    devices_list = device_manager.list_devices()
    
    if not devices_list:
        console.print("[yellow]No devices registered[/yellow]")
        return
    
    table = Table(title="Registered Devices", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Name", style="green")
    table.add_column("IP Address")
    table.add_column("Status", style="bold")
    table.add_column("Last Seen")
    
    for device in devices_list:
        status_color = {
            "DISCOVERED": "yellow",
            "PAIRING": "blue",
            "AUTHORIZED": "green",
            "REVOKED": "red"
        }.get(device.status.value, "white")
        
        table.add_row(
            device.id,
            device.name,
            device.ip_address,
            Text(device.status.value, style=status_color),
            device.last_seen.strftime("%Y-%m-%d %H:%M:%S") if device.last_seen else "-"
        )
    
    console.print(table)


@app.command()
def pair(
    device_id: str = typer.Argument(help="Device ID to pair")
):
    """Initiate pairing for a device."""
    from .authorization.devices import device_manager
    
    try:
        pairing = device_manager.initiate_pairing(device_id)
        
        console.print(Panel(
            f"[green]Pairing initiated for device: {device_id}[/green]\n\n"
            f"[cyan]Pairing Token:[/cyan] {pairing['pairing_token']}\n"
            f"[cyan]Expires in:[/cyan] {pairing['expires_in']} seconds\n\n"
            f"[dim]Use this token to complete pairing from the device.[/dim]",
            border_style="green"
        ))
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def info(
    device_id: str = typer.Argument(help="Device ID")
):
    """Get device information."""
    from .authorization.devices import device_manager
    
    device = device_manager.get_device(device_id)
    
    if not device:
        console.print(f"[red]Device not found: {device_id}[/red]")
        raise typer.Exit(1)
    
    info_text = Text()
    info_text.append("Device Information\n\n", style="bold cyan")
    info_text.append(f"ID: {device.id}\n")
    info_text.append(f"Name: {device.name}\n")
    info_text.append(f"IP Address: {device.ip_address}\n")
    info_text.append(f"MAC Address: {device.mac_address or 'N/A'}\n")
    info_text.append(f"Manufacturer: {device.manufacturer or 'N/A'}\n")
    info_text.append(f"Status: {device.status.value}\n")
    info_text.append(f"Services: {', '.join(device.services) if device.services else 'None'}\n")
    info_text.append(f"ADB Serial: {device.adb_serial or 'N/A'}\n")
    
    if device.authorized_at:
        info_text.append(f"Authorized: {device.authorized_at.strftime('%Y-%m-%d %H:%M:%S')}\n")
    if device.authorization_expires:
        info_text.append(f"Expires: {device.authorization_expires.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    console.print(Panel(info_text, border_style="cyan"))


@app.command()
def battery(
    device_id: str = typer.Argument(help="Device ID")
):
    """Get device battery status."""
    from .android.adb import adb_manager
    
    async def _get_battery():
        try:
            adb_device = adb_manager.get_device(device_id)
            battery_info = await adb_device.get_battery()
            
            battery_text = Text()
            battery_text.append("Battery Status\n\n", style="bold green")
            battery_text.append(f"Level: {battery_info.level}%\n")
            battery_text.append(f"Status: {battery_info.status}\n")
            
            if battery_info.temperature:
                battery_text.append(f"Temperature: {battery_info.temperature}°C\n")
            if battery_info.voltage:
                battery_text.append(f"Voltage: {battery_info.voltage}V\n")
            
            console.print(Panel(battery_text, border_style="green"))
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    
    asyncio.run(_get_battery())


@app.command()
def audit(
    device_id: str = typer.Argument(help="Device ID")
):
    """Run security audit on device."""
    from .security.audit import auditor
    
    console.print(f"[cyan]Running security audit for device: {device_id}[/cyan]")
    
    try:
        audit_result = auditor.run_security_audit(device_id)
        
        # Print audit results
        score_color = "green" if audit_result.score >= 80 else "yellow" if audit_result.score >= 60 else "red"
        console.print(f"\n[bold {score_color}]Security Score: {audit_result.score}/100[/bold {score_color}]\n")
        
        if audit_result.findings:
            table = Table(title="Security Findings", show_header=True, header_style="bold magenta")
            table.add_column("Severity", style="bold", width=10)
            table.add_column("Title", width=40)
            table.add_column("Category", width=20)
            
            for finding in audit_result.findings:
                severity_color = {
                    "HIGH": "red",
                    "MEDIUM": "yellow",
                    "LOW": "blue",
                    "INFO": "dim"
                }.get(finding.severity.value, "white")
                
                table.add_row(
                    Text(finding.severity.value, style=severity_color),
                    finding.title,
                    finding.category
                )
            
            console.print(table)
        
        if audit_result.recommendations:
            console.print("\n[bold yellow]Recommendations:[/bold yellow]")
            for i, rec in enumerate(audit_result.recommendations, 1):
                console.print(f"  {i}. {rec}")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def report(
    device_id: str = typer.Argument(help="Device ID")
):
    """Generate security report for device."""
    from .security.audit import auditor
    from .security.report import report_generator
    
    console.print(f"[cyan]Generating security report for device: {device_id}[/cyan]")
    
    try:
        report_result = auditor.generate_report(device_id)
        
        # Print terminal report
        report_generator.print_terminal_report(report_result)
        
        # Generate JSON report
        json_path = report_generator.generate_json_report(report_result)
        console.print(f"\n[green]JSON report saved to: {json_path}[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def auth_lab_start(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8443, "--port", "-p", help="Port to bind")
):
    """Start the authentication laboratory."""
    from .security.authentication_lab import auth_lab
    
    console.print(f"[green]Starting Authentication Lab on {host}:{port}[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    
    try:
        import uvicorn
        uvicorn.run(auth_lab.app, host=host, port=port)
    except KeyboardInterrupt:
        console.print("\n[yellow]Authentication Lab stopped[/yellow]")


@app.command()
def auth_lab_test():
    """Run authentication lab tests."""
    from .security.authentication_lab import auth_lab
    
    console.print("[cyan]Running Authentication Lab Tests[/cyan]\n")
    
    tests = auth_lab.run_tests()
    
    table = Table(title="Authentication Tests", show_header=True, header_style="bold magenta")
    table.add_column("Test Name", style="cyan")
    table.add_column("Result", style="bold")
    table.add_column("Description")
    
    for test in tests:
        result_color = "green" if test["passed"] else "red"
        result_text = "✓ PASS" if test["passed"] else "✗ FAIL"
        
        table.add_row(
            test["test_name"],
            Text(result_text, style=result_color),
            test["description"]
        )
    
    console.print(table)
    
    # Print findings
    for test in tests:
        if test["findings"]:
            console.print(f"\n[bold]{test['test_name']}:[/bold]")
            for finding in test["findings"]:
                console.print(f"  • {finding}")


if __name__ == "__main__":
    app()
