"""
Build commandAGI daemon images for different platforms.

This module provides functions to build Docker, Kubernetes, AWS, Azure, and GCP images
for the commandAGI daemon.
"""

from commandAGI._utils.command import run_command

from .all import build_all_images
from .aws import build_aws_ami
from .azure import build_azure_vm
from .cli import cli
from .docker import build_docker_image
from .gcp import build_gcp_vm
from .kubernetes import build_kubernetes_image
from .utils import ensure_packer_template

__all__ = [
    "run_command",
    "ensure_packer_template",
    "build_docker_image",
    "build_kubernetes_image",
    "build_aws_ami",
    "build_azure_vm",
    "build_gcp_vm",
    "build_all_images",
    "cli",
]
