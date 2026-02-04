import logging
import docker

def restart_container(container_id: str, allowed_container_names: list = None) -> (bool, str):
    """Restart a Docker container by its ID with optional safety checks."""
    client = docker.from_env()
    try:
        container = client.containers.get(container_id)
        if allowed_container_names and container.name not in allowed_container_names:
            logging.warning(f"Container {container.name} is not in the allowed list. Restart aborted.")
            return False, f"Container {container.name} is not allowed to be restarted."

        container.restart()
        logging.info(f"Successfully restarted container: {container.name} (ID: {container_id})")
        return True, f"Container {container.name} restarted successfully."
    except docker.errors.NotFound:
        logging.error(f"Container with ID {container_id} not found.")
        return False, "Container not found."
    except Exception as e:
        logging.error(f"Error restarting container {container_id}: {e}")
        return False, str(e)