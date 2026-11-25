"""Reserved server-side LLM configuration. No outbound calls until an adapter is installed."""
import os
from dataclasses import dataclass, field
from .personal import RuleDialogueProvider

@dataclass(frozen=True)
class LLMConfiguration:
    base_url: str = ''
    model: str = ''
    token: str = field(default='', repr=False)
    @classmethod
    def from_environment(cls):
        return cls(os.getenv('COURSEPILOT_LLM_BASE_URL',''), os.getenv('COURSEPILOT_LLM_MODEL',''), os.getenv('COURSEPILOT_LLM_TOKEN',''))

class PersonalLLMProvider(RuleDialogueProvider):
    """Replace extract with validated model output when the model integration is ready.

    Deliberately uses local rules even if a token is configured. A token alone does
    not identify a protocol/model and must never silently send student data.
    """
    def __init__(self, configuration=None):
        self.configuration = configuration or LLMConfiguration.from_environment()
