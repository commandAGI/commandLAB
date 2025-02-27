"""CLI commands for building CommandLAB daemon images."""

import subprocess
import logging
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from commandLAB.version import get_container_version


logger = logging.getLogger("build_images")
console = Console()

cli = typer.Typer(help="Build CommandLAB daemon images for different platforms")
