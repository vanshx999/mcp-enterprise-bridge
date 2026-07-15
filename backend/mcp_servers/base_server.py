from abc import ABC, abstractmethod
from typing import Any


class BaseMCPServer(ABC):
    @abstractmethod
    async def execute_tool(self, tool_name: str, args: dict) -> Any:
        pass
