"""Centralized leave (cuti) approval policy.

Defines which employee *levels* a requester of a given level may pick as their
supervisor/approver. Edit ``LEVEL_APPROVER_MAP`` to change the hierarchy.

Rules:
    - Level 1-4 may request anyone from level 5-7.
    - Level 5-6 may request level 7.
    - Level 7 may request level 8.
"""

LEVEL_APPROVER_MAP = {
    1: [5, 6, 7],
    2: [5, 6, 7],
    3: [5, 6, 7],
    4: [5, 6, 7],
    5: [7],
    6: [7, 8],
    7: [8],
}

# Employees at this level (and above) can act as supervisors in the portal
# approval tab.
MIN_SUPERVISOR_LEVEL = 5


def eligible_supervisor_levels(level):
    """Return the list of levels a requester of ``level`` may pick as supervisor."""
    return LEVEL_APPROVER_MAP.get(level, [])
