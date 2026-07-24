from typing import Dict, Any


class BaseAgent:
    """Base class for all agents in the NEXUS Swarm architecture."""

    def health_check(self) -> Dict[str, Any]:
        """Returns the health status of the agent."""
        return {"status": "ok", "message": f"{self.__class__.__name__} is operational"}

    async def run(self, *args, **kwargs) -> Any:
        """Executes the agent's primary logic."""
        raise NotImplementedError
