"""Agent profile registry for specialized subagent definitions."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from loguru import logger


@dataclass
class AgentProfile:
    """Definition of a specialized agent type."""

    name: str
    system_prompt: str
    owned_skills: list[str] = field(default_factory=list)
    available_skills: list[str] = field(default_factory=list)
    model: str | None = None
    max_iterations: int = 15
    max_tokens: int | None = None


class AgentProfileRegistry:
    """Loads and manages agent definitions from the definitions/ directory.

    Each agent definition is a subdirectory of definitions/ containing:
    - AGENTS.md: The system prompt with persona, guidelines, and skill declarations
    - config.yaml: Optional runtime overrides (model, max_iterations, max_tokens)

    Skills are declared in AGENTS.md under two sections:
    - ## Owned Skills: Always loaded, tools registered at spawn time
    - ## Available Skills: On-demand, agent reads SKILL.md when needed
    """

    def __init__(self, definitions_dir: Path) -> None:
        self._definitions_dir = definitions_dir
        self._profiles: dict[str, AgentProfile] = {}

    def load_all(self) -> None:
        """Scan definitions/ subdirectories and load profiles."""
        if not self._definitions_dir.exists():
            logger.debug("Agent definitions directory not found: {}", self._definitions_dir)
            return

        for agent_dir in sorted(self._definitions_dir.iterdir()):
            if not agent_dir.is_dir():
                continue
            agents_md = agent_dir / "AGENTS.md"
            if not agents_md.exists():
                logger.warning("Agent definition '{}' missing AGENTS.md, skipping", agent_dir.name)
                continue

            profile = self._load_profile(agent_dir.name, agents_md, agent_dir / "config.yaml")
            if profile:
                self._profiles[profile.name] = profile
                logger.info(
                    "Loaded agent profile '{}': {} owned skills, {} available skills",
                    profile.name, len(profile.owned_skills), len(profile.available_skills),
                )

    def get(self, name: str) -> AgentProfile | None:
        """Get an agent profile by name."""
        return self._profiles.get(name)

    def list_names(self) -> list[str]:
        """List all loaded agent profile names."""
        return list(self._profiles.keys())

    def _load_profile(
        self, name: str, agents_md: Path, config_yaml: Path
    ) -> AgentProfile | None:
        """Load a single agent profile from its definition files."""
        system_prompt = agents_md.read_text(encoding="utf-8")
        owned, available = self._parse_skills_from_prompt(system_prompt)

        model = None
        max_iterations = 15
        max_tokens = None

        if config_yaml.exists():
            try:
                config = yaml.safe_load(config_yaml.read_text()) or {}
                model = config.get("model")
                max_iterations = config.get("max_iterations", 15)
                max_tokens = config.get("max_tokens")
            except Exception as e:
                logger.error("Failed to parse config.yaml for '{}': {}", name, e)

        return AgentProfile(
            name=name,
            system_prompt=system_prompt,
            owned_skills=owned,
            available_skills=available,
            model=model,
            max_iterations=max_iterations,
            max_tokens=max_tokens,
        )

    @staticmethod
    def _parse_skills_from_prompt(prompt: str) -> tuple[list[str], list[str]]:
        """Extract skill names from **skill_name** patterns in Owned/Available sections.

        Looks for markdown headings:
            ## Owned Skills
            ## Available Skills

        And extracts bold skill names (e.g., **ranking_tracker**) under each.
        """
        owned: list[str] = []
        available: list[str] = []
        current_section: str | None = None

        for line in prompt.splitlines():
            heading_match = re.match(r"^##\s+(.+)", line)
            if heading_match:
                heading = heading_match.group(1).strip().lower()
                if "owned" in heading and "skill" in heading:
                    current_section = "owned"
                elif "available" in heading and "skill" in heading:
                    current_section = "available"
                else:
                    current_section = None
            elif current_section:
                match = re.search(r"\*\*(\w[\w_-]*)\*\*", line)
                if match:
                    skill_name = match.group(1)
                    if current_section == "owned":
                        if skill_name not in owned:
                            owned.append(skill_name)
                    else:
                        if skill_name not in available:
                            available.append(skill_name)

        return owned, available
