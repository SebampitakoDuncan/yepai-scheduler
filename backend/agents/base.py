from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from enum import Enum
import time


class MessageType(str, Enum):
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class AgentMessage(BaseModel):
    sender: str
    recipient: str
    message_type: MessageType
    action: str
    payload: Dict[str, Any]
    timestamp: float = None
    correlation_id: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = time.time()
    
    class Config:
        use_enum_values = True


class AgentState(BaseModel):
    """Represents the current state of an agent."""
    name: str
    status: str = "idle"
    last_action: Optional[str] = None
    last_action_time: Optional[float] = None
    context: Dict[str, Any] = {}


class BaseAgent(ABC):
    """Base class for all agents in the multi-agent system."""
    
    def __init__(self, name: str):
        self.name = name
        self.state = AgentState(name=name)
        self.message_log: List[AgentMessage] = []
    
    @abstractmethod
    def process(self, message: AgentMessage) -> AgentMessage:
        """Process an incoming message and return a response."""
        pass
    
    def send_message(
        self,
        recipient: str,
        action: str,
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.REQUEST,
        correlation_id: Optional[str] = None,
    ) -> AgentMessage:
        """Create and log an outgoing message."""
        message = AgentMessage(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            action=action,
            payload=payload,
            correlation_id=correlation_id,
        )
        self.message_log.append(message)
        self.state.last_action = action
        self.state.last_action_time = message.timestamp
        return message
    
    def receive_message(self, message: AgentMessage) -> None:
        """Log an incoming message."""
        self.message_log.append(message)
    
    def update_context(self, key: str, value: Any) -> None:
        """Update agent's context state."""
        self.state.context[key] = value
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a value from agent's context."""
        return self.state.context.get(key, default)
    
    def set_status(self, status: str) -> None:
        """Update agent status."""
        self.state.status = status
    
    def get_state(self) -> Dict[str, Any]:
        """Get current agent state as dict."""
        return self.state.model_dump()
