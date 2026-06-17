"""LangGraph ResolutionState TypedDict definition."""

from typing import TypedDict, Optional, Literal, List


class ChunkInfo(TypedDict):
    """Information about a single chunk involved in a conflict."""
    id: str
    document_id: str
    document_title: str
    content: str
    claim: str


class RepairActionResult(TypedDict):
    """Result of a single repair action."""
    action_type: str  # delete_chunk | update_chunk | create_chunk
    chunk_id: Optional[str]
    old_content: Optional[str]
    new_content: Optional[str]
    success: bool
    error_message: Optional[str]


class ResolutionState(TypedDict):
    """State for the resolution workflow graph."""

    # Input (set by POST /resolve)
    conflict_id: str
    chunk_a: ChunkInfo
    chunk_b: ChunkInfo
    conflict_type: str
    conflict_summary: str

    # Filled by extract_claims (updated during runtime)
    claims_extracted: bool

    # Filled by analyze_contradiction
    contradiction_analysis: Optional[str]

    # Filled by generate_resolution
    proposed_action: Optional[str]  # replace_both | keep_a_remove_b | keep_b_remove_a | merge | manual_rewrite
    proposed_content: Optional[str]
    reasoning: Optional[str]
    resolution_id: Optional[str]

    # Filled by human_review interrupt
    human_decision: Optional[str]  # approved | rejected | modified
    human_notes: Optional[str]
    human_modified_content: Optional[str]

    # Filled by apply_repair
    repair_results: List[RepairActionResult]

    # Error handling
    error: Optional[str]
