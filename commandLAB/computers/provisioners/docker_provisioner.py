from enum import Enum
from pathlib import Path
import subprocess
import time
from typing import Optional, List
import boto3
from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.identity import DefaultAzureCredential
from google.cloud import container_v1
from google.cloud import run_v2
from .base_provisioner import BaseComputerProvisioner
from commandLAB.version import get_container_version


class DockerPlatform(str, Enum):
    LOCAL = "local"
    AWS_ECS = "aws_ecs"
    AZURE_CONTAINER_INSTANCES = "azure_container_instances"
    GCP_CLOUD_RUN = "gcp_cloud_run"


class DockerProvisioner(BaseComputerProvisioner):
    def __init__(
        self,
        port: int = 8000,
        container_name: str = "commandlab-daemon",
        platform: DockerPlatform = DockerPlatform.LOCAL,
        version: Optional[str] = None,
        # Cloud-specific parameters
        region: str = None,
        resource_group: str = None,
        project_id: str = None,
        # Add these parameters
        subnets: List[str] = None,
        security_groups: List[str] = None,
        subscription_id: str = None,
        max_retries: int = 3,
        timeout: int = 900,  # 15 minutes
        dockerfile_path: Optional[str] = Path(__file__).parent.parent.parent.parent / "resources" / "docker" / "Dockerfile",
    ):
        super().__init__(port)
        self.container_name = container_name
        self.platform = platform
        self.version = version or get_container_version()
        self.region = region
        self.resource_group = resource_group
        self.project_id = project_id
        self.subnets = subnets or ["subnet-xxxxx"]
        self.security_groups = security_groups or ["sg-xxxxx"]
        self.subscription_id = subscription_id
        self.max_retries = max_retries
        self.timeout = timeout
        self._status = "not_started"
        self.container_id = None
        self._task_arn = None
        self.dockerfile_path = dockerfile_path

        # Initialize cloud clients if needed
        if platform == DockerPlatform.AWS_ECS:
            if not self.region:
                raise ValueError("Region must be specified for AWS ECS")
            self.ecs_client = boto3.client("ecs", region_name=region)
        elif platform == DockerPlatform.AZURE_CONTAINER_INSTANCES:
            if not self.subscription_id:
                raise ValueError(
                    "Subscription ID must be specified for Azure Container Instances"
                )
            self.aci_client = ContainerInstanceManagementClient(
                credential=DefaultAzureCredential(),
                subscription_id=self.subscription_id,
            )
        elif platform == DockerPlatform.GCP_CLOUD_RUN:
            if not self.project_id:
                raise ValueError("Project ID must be specified for GCP Cloud Run")
            self.cloud_run_client = run_v2.ServicesClient()
    def setup(self) -> None:
        print(f"Setting up container with platform {self.platform}")
        self._status = "starting"
        print(f"Status set to: {self._status}")
        retry_count = 0

        while retry_count < self.max_retries:
            print(f"Attempt {retry_count + 1}/{self.max_retries} to setup container")
            try:
                print(f"Attempt {retry_count + 1}/{self.max_retries} to setup container")
                print(f"Attempt {retry_count + 1}/{self.max_retries} to setup container")
                if self.platform == DockerPlatform.LOCAL:
                    print("Using LOCAL platform setup")
                    self._setup_local()
                elif self.platform == DockerPlatform.AWS_ECS:
                    print("Using AWS ECS platform setup") 
                    self._setup_aws_ecs()
                elif self.platform == DockerPlatform.AZURE_CONTAINER_INSTANCES:
                    print("Using Azure Container Instances platform setup")
                    self._setup_azure_container_instances()
                elif self.platform == DockerPlatform.GCP_CLOUD_RUN:
                    print("Using GCP Cloud Run platform setup")
                    self._setup_gcp_cloud_run()

                # Wait for the container to be running
                print(f"Waiting for container to be running (timeout: {self.timeout}s)")
                start_time = time.time()
                while time.time() - start_time < self.timeout:
                    if self.is_running():
                        self._status = "running"
                        print(f"Container is now running after {int(time.time() - start_time)}s")
                        return
                    print("Container not yet running, checking again in 5s")
                    time.sleep(5)

                # If we get here, the container didn't start in time
                self._status = "error"
                elapsed = int(time.time() - start_time)
                print(f"Timeout waiting for container to start after {elapsed}s")
                raise TimeoutError(f"Timeout waiting for container to start after {elapsed}s")

            except Exception as e:
                retry_count += 1
                if retry_count >= self.max_retries:
                    self._status = "error"
                    print(
                        f"Failed to setup container after {self.max_retries} attempts: {str(e)}"
                    )
                    raise
                backoff = 2**retry_count
                print(
                    f"Error setting up container, retrying in {backoff}s ({retry_count}/{self.max_retries}): {str(e)}"
                )
                time.sleep(backoff)  # Exponential backoff

    def _setup_local(self):
        """Setup local Docker container"""
        print(f"Starting local Docker container {self.container_name}")

        import docker

        # Use Docker client
        docker_client = docker.from_env()

        if self.dockerfile_path:
            dockerfile = self.dockerfile_path if self.dockerfile_path else "Dockerfile"
            dockerfile_dir = str(Path(dockerfile).parent)
            dockerfile_name = Path(dockerfile).name
            
            print(f"Building Docker image from Dockerfile: {dockerfile}")
            
            try:
                # Build the image using docker-py
                image, build_logs = docker_client.images.build(
                    path=dockerfile_dir,
                    dockerfile=dockerfile_name,
                    tag=f"commandlab-daemon:{self.version}",
                    rm=True,  # Remove intermediate containers
                )
                
                # Print build logs
                for log in build_logs:
                    if 'stream' in log:
                        log_line = log['stream'].strip()
                        if log_line:
                            print(f"Docker build: {log_line}")
                
                print(f"Docker image built successfully: {image.tags[0]}")
            except docker.errors.BuildError as e:
                print(f"Docker build failed: {str(e)}")
                raise RuntimeError(f"Docker build failed: {str(e)}")

        container = docker_client.containers.run(
            f"commandlab-daemon:{self.version}",
            name=self.container_name,
            detach=True,
            ports={f"{self.port}/tcp": self.port},
            command=["poetry", "run", "commandLAB.daemon", "start", "--port", str(self.port), "--backend", "pynput"],
        )

        self.container_id = container.id
        print(f"Started Docker container with ID: {self.container_id}")

    def _setup_aws_ecs(self):
        """Setup AWS ECS container"""
        print(f"Starting AWS ECS task in region {self.region}")

        response = self.ecs_client.run_task(
            cluster="commandlab-cluster",
            taskDefinition="commandlab-daemon",
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": self.subnets,
                    "securityGroups": self.security_groups,
                    "assignPublicIp": "ENABLED",
                }
            },
            overrides={
                "containerOverrides": [
                    {
                        "name": "commandlab-daemon",
                        "image": f"commandlab-daemon:{self.version}",
                    }
                ]
            },
        )
        self._task_arn = response["tasks"][0]["taskArn"]
        print(f"Started ECS task with ARN: {self._task_arn}")

    def _setup_azure_container_instances(self):
        """Setup Azure Container Instances"""
        print(
            f"Starting Azure Container Instance {self.container_name} in resource group {self.resource_group}"
        )

        container_group = {
            "location": self.region,
            "containers": [
                {
                    "name": self.container_name,
                    "image": f"commandlab-daemon:{self.version}",
                    "ports": [{"port": self.port}],
                    "resources": {"requests": {"memoryInGB": 1.5, "cpu": 1.0}},
                }
            ],
            "osType": "Linux",
            "ipAddress": {
                "type": "Public",
                "ports": [{"protocol": "TCP", "port": self.port}],
            },
        }

        poller = self.aci_client.container_groups.begin_create_or_update(
            self.resource_group, self.container_name, container_group
        )

        # Wait for the operation to complete with timeout
        start_time = time.time()
        while not poller.done() and time.time() - start_time < self.timeout:
            time.sleep(5)

        if not poller.done():
            raise TimeoutError(f"Timeout waiting for Azure Container Instance creation")

        result = poller.result()
        print(f"Started Azure Container Instance: {result.name}")

    def _setup_gcp_cloud_run(self):
        """Setup GCP Cloud Run container"""
        print(
            f"Starting GCP Cloud Run service {self.container_name} in project {self.project_id}"
        )

        service = {
            "apiVersion": "serving.knative.dev/v1",
            "kind": "Service",
            "metadata": {"name": self.container_name},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "image": f"commandlab-daemon:{self.version}",
                                "ports": [{"containerPort": self.port}],
                            }
                        ]
                    }
                }
            },
        }

        parent = f"projects/{self.project_id}/locations/{self.region}"
        operation = self.cloud_run_client.create_service(parent=parent, service=service)

        # Wait for the operation to complete
        print(f"Waiting for Cloud Run service creation to complete")
        start_time = time.time()
        while not operation.done() and time.time() - start_time < self.timeout:
            time.sleep(5)

        if not operation.done():
            raise TimeoutError(f"Timeout waiting for Cloud Run service creation")

        result = operation.result()
        print(f"Started Cloud Run service: {result.name}")

    def teardown(self) -> None:
        self._status = "stopping"

        try:
            if self.platform == DockerPlatform.LOCAL:
                self._teardown_local()
            elif self.platform == DockerPlatform.AWS_ECS:
                self._teardown_aws_ecs()
            elif self.platform == DockerPlatform.AZURE_CONTAINER_INSTANCES:
                self._teardown_azure_container_instances()
            elif self.platform == DockerPlatform.GCP_CLOUD_RUN:
                self._teardown_gcp_cloud_run()

            self._status = "stopped"
        except Exception as e:
            self._status = "error"
            print(f"Error during teardown: {e}")

    def _teardown_local(self):
        """Teardown local Docker container"""
        try:
            import docker

            # Use Docker client
            docker_client = docker.from_env()

            try:
                container = docker_client.containers.get(self.container_name)
                print(f"Stopping Docker container {self.container_name}")
                container.stop()
                print(f"Removing Docker container {self.container_name}")
                container.remove()
            except docker.errors.NotFound:
                print(f"Docker container {self.container_name} not found")
        except ImportError:
            # Fall back to subprocess if docker-py is not available
            print(
                "Docker Python client not available, falling back to subprocess"
            )
            if not self.container_id and self.container_name:
                # Try to get container ID from name
                try:
                    result = subprocess.run(
                        ["docker", "ps", "-aqf", f"name={self.container_name}"],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    self.container_id = result.stdout.strip()
                except Exception as e:
                    print(
                        f"Could not get container ID for {self.container_name}: {e}"
                    )

            if self.container_id or self.container_name:
                print(f"Stopping Docker container {self.container_name}")
                try:
                    subprocess.run(["docker", "stop", self.container_name], check=True)
                    print(f"Removing Docker container {self.container_name}")
                    subprocess.run(["docker", "rm", self.container_name], check=True)
                except Exception as e:
                    print(f"Error stopping/removing Docker container: {e}")

    def _teardown_aws_ecs(self):
        """Teardown AWS ECS task"""
        if self._task_arn:
            print(f"Stopping ECS task {self._task_arn}")
            try:
                self.ecs_client.stop_task(
                    cluster="commandlab-cluster", task=self._task_arn
                )

                # Wait for the task to stop
                start_time = time.time()
                while time.time() - start_time < self.timeout:
                    try:
                        response = self.ecs_client.describe_tasks(
                            cluster="commandlab-cluster", tasks=[self._task_arn]
                        )
                        if not response["tasks"]:
                            break
                        status = response["tasks"][0]["lastStatus"]
                        if status == "STOPPED":
                            print(
                                f"ECS task {self._task_arn} stopped successfully"
                            )
                            break
                        print(f"ECS task status: {status}")
                        time.sleep(5)
                    except Exception as e:
                        print(f"Task {self._task_arn} no longer exists: {e}")
                        break
            except Exception as e:
                print(f"Error stopping ECS task: {e}")

    def _teardown_azure_container_instances(self):
        """Teardown Azure Container Instance"""
        print(f"Deleting Azure Container Instance {self.container_name}")
        try:
            poller = self.aci_client.container_groups.begin_delete(
                self.resource_group, self.container_name
            )

            # Wait for the operation to complete with timeout
            start_time = time.time()
            while not poller.done() and time.time() - start_time < self.timeout:
                time.sleep(5)

            if poller.done():
                print(
                    f"Azure Container Instance {self.container_name} deleted successfully"
                )
            else:
                print(f"Timeout waiting for Azure Container Instance deletion")
        except Exception as e:
            print(f"Error deleting Azure Container Instance: {e}")

    def _teardown_gcp_cloud_run(self):
        """Teardown GCP Cloud Run service"""
        print(f"Deleting Cloud Run service {self.container_name}")
        try:
            name = f"projects/{self.project_id}/locations/{self.region}/services/{self.container_name}"
            operation = self.cloud_run_client.delete_service(name=name)

            # Wait for the operation to complete
            start_time = time.time()
            while not operation.done() and time.time() - start_time < self.timeout:
                time.sleep(5)

            if operation.done():
                print(
                    f"Cloud Run service {self.container_name} deleted successfully"
                )
            else:
                print(f"Timeout waiting for Cloud Run service deletion")
        except Exception as e:
            print(f"Error deleting Cloud Run service: {e}")

    def is_running(self) -> bool:
        try:
            if self.platform == DockerPlatform.LOCAL:
                return self._is_local_running()
            elif self.platform == DockerPlatform.AWS_ECS:
                return self._is_aws_ecs_running()
            elif self.platform == DockerPlatform.AZURE_CONTAINER_INSTANCES:
                return self._is_azure_container_instances_running()
            elif self.platform == DockerPlatform.GCP_CLOUD_RUN:
                return self._is_gcp_cloud_run_running()
            return False
        except Exception as e:
            print(f"Error checking if container is running: {e}")
            return False

    def _is_local_running(self) -> bool:
        """Check if local Docker container is running"""
        try:
            import docker

            # Use Docker client
            docker_client = docker.from_env()

            try:
                container = docker_client.containers.get(self.container_name)
                is_running = container.status == "running"
                print(
                    f"Docker container {self.container_name} running status: {is_running}"
                )
                return is_running
            except docker.errors.NotFound:
                print(f"Docker container {self.container_name} not found")
                return False
        except ImportError:
            # Fall back to subprocess if docker-py is not available
            print(
                "Docker Python client not available, falling back to subprocess"
            )
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "inspect",
                        "-f",
                        "{{.State.Running}}",
                        self.container_name,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                is_running = result.stdout.strip() == "true"
                print(
                    f"Docker container {self.container_name} running status: {is_running}"
                )
                return is_running
            except Exception as e:
                print(f"Error checking Docker container status: {e}")
                return False

    def _is_aws_ecs_running(self) -> bool:
        """Check if AWS ECS task is running"""
        try:
            if not self._task_arn:
                return False

            response = self.ecs_client.describe_tasks(
                cluster="commandlab-cluster", tasks=[self._task_arn]
            )

            if not response["tasks"]:
                return False

            status = response["tasks"][0]["lastStatus"]
            is_running = status == "RUNNING"
            print(f"ECS task {self._task_arn} status: {status}")
            return is_running
        except Exception as e:
            print(f"Error checking ECS task status: {e}")
            return False

    def _is_azure_container_instances_running(self) -> bool:
        """Check if Azure Container Instance is running"""
        try:
            container_group = self.aci_client.container_groups.get(
                self.resource_group, self.container_name
            )
            is_running = (
                container_group.containers[0].instance_view.current_state.state
                == "Running"
            )
            print(
                f"Azure Container Instance {self.container_name} running status: {is_running}"
            )
            return is_running
        except Exception as e:
            print(f"Error checking Azure Container Instance status: {e}")
            return False

    def _is_gcp_cloud_run_running(self) -> bool:
        """Check if GCP Cloud Run service is running"""
        try:
            name = f"projects/{self.project_id}/locations/{self.region}/services/{self.container_name}"
            service = self.cloud_run_client.get_service(name=name)
            is_running = service.status.conditions[0].status == True
            print(
                f"Cloud Run service {self.container_name} running status: {is_running}"
            )
            return is_running
        except Exception as e:
            print(f"Error checking Cloud Run service status: {e}")
            return False

    def get_status(self) -> str:
        """Get the current status of the provisioner."""
        return self._status
