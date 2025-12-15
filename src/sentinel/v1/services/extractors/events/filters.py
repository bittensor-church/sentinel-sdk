"""Runtime upgrade event filtering utilities."""

from sentinel.v1.dto import EventDTO

# Runtime upgrade event identifiers
RUNTIME_UPGRADE_MODULE = "System"
RUNTIME_UPGRADE_EVENT = "CodeUpdated"


def is_runtime_upgrade_event(event: EventDTO) -> bool:
    """
    Check if an event is a runtime upgrade (CodeUpdated).

    Args:
        event: The event to check

    Returns:
        True if the event indicates a runtime upgrade

    """
    return event.module_id == RUNTIME_UPGRADE_MODULE and event.event_id == RUNTIME_UPGRADE_EVENT


def filter_runtime_upgrade_events(events: list[EventDTO]) -> list[EventDTO]:
    """
    Filter a list of events to only include runtime upgrades.

    Args:
        events: List of events to filter

    Returns:
        List containing only runtime upgrade events

    """
    return [event for event in events if is_runtime_upgrade_event(event)]


def get_runtime_upgrade_info(event: EventDTO, block_number: int) -> dict | None:
    """
    Extract runtime upgrade info from an event.

    Args:
        event: The event to extract info from
        block_number: The block number where the upgrade occurred

    Returns:
        Dict with upgrade info if it's a runtime upgrade, None otherwise

    """
    if not is_runtime_upgrade_event(event):
        return None

    return {
        "block_number": block_number,
        "event_index": event.event_index,
        "extrinsic_idx": event.extrinsic_idx,
    }


# def process_block_for_runtime_upgrades(block: Block) -> dict | None:
#     """Check if a block contains a runtime upgrade."""
#     upgrade_events = filter_runtime_upgrade_events(block.events)

#     if upgrade_events:
#         # Runtime was upgraded in this block
#         return {
#             "block_number": block.block_number,
#             "block_hash": block.block_hash,
#             "upgrades": [
#                 get_runtime_upgrade_info(e, block.block_number)
#                 for e in upgrade_events
#             ],
#         }
#     return None
