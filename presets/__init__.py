from __future__ import annotations

from presets.base import PRESET_REGISTRY, Preset, PresetRegistry, Question

# Import side-effect: register all presets
import presets.codebase_assistant
import presets.command_assistant
import presets.context_maintainer
import presets.docs_maintainer
import presets.file_organizer
import presets.github_maintainer
import presets.local_document_chat
import presets.research_report

__all__ = [
    "PRESET_REGISTRY",
    "Preset",
    "PresetRegistry",
    "Question",
    "codebase_assistant",
    "command_assistant",
    "context_maintainer",
    "docs_maintainer",
    "file_organizer",
    "github_maintainer",
    "local_document_chat",
    "research_report",
]
