from .base_provisioner import BaseComputerProvisioner


class ManualProvisioner(BaseComputerProvisioner):
    def setup(self) -> None:
        print(f"Please start the daemon manually using:")
        print(f"pip install commandlab[local,daemon]")
        print(f"python -m commandlab.daemon.daemon --port {self.port} --backend pynput")

    def teardown(self) -> None:
        print("Please stop the daemon manually")

    def is_running(self) -> bool:
        # Could implement a basic health check here
        return True
