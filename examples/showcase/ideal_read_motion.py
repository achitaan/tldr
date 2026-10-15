"""Pure authored state for the connected ideal-read explanation.

The values are inputs to the original logical teaching illustration.  They do
not describe measured hardware behavior or an analog timing simulation.
"""
from __future__ import annotations

from copy import deepcopy


SOURCE_ID = "ideal-source-page-13"
CURSOR_ID = "ideal-clock-cursor"
REGISTER_ID = "ideal-master-mdr"
SELECTED_ROW_ID = "ideal-memory-row-16"
RETURN_PATH_ID = "ideal-return-data-path"

CONTEXT_IDS = (
    SOURCE_ID,
    CURSOR_ID,
    REGISTER_ID,
    SELECTED_ROW_ID,
    RETURN_PATH_ID,
)

# Full-page normalized x positions.  These are the centers of the three
# reviewed source overlays already used for page 13.
EDGE_X = {1: 0.2115, 2: 0.5325, 3: 0.8525}


def ideal_read_state(
    sentence_index: int,
    *,
    prior_register: int = 19,
    selected_address: int = 16,
    selected_value: int = 42,
) -> dict:
    """Return the visible logical state at an authored narration boundary."""
    if not isinstance(sentence_index, int) or sentence_index < 0:
        raise ValueError("sentence_index must be a non-negative integer")

    replay = sentence_index == 13
    revealed = sentence_index >= 14
    stored = (9 <= sentence_index < 13) or revealed
    cursor_edge = None
    if 3 <= sentence_index < 6:
        cursor_edge = 1
    elif 6 <= sentence_index < 8:
        cursor_edge = 2
    elif 8 <= sentence_index < 13 or revealed:
        cursor_edge = 3
    if replay:
        cursor_edge = None

    if replay:
        phase = "prediction_replay"
    elif revealed:
        phase = "answer_revealed"
    elif stored:
        phase = "stored"
    elif sentence_index == 8:
        phase = "edge_three_before_storage"
    elif sentence_index >= 7:
        phase = "returned_data_available"
    elif sentence_index >= 6:
        phase = "slave_response_edge"
    elif sentence_index >= 5:
        phase = "address_valid_data_pending"
    elif sentence_index >= 3:
        phase = "address_selected"
    else:
        phase = "prior_register_example"

    return {
        "sentence_index": sentence_index,
        "phase": phase,
        "prior_register": prior_register,
        "selected_address": selected_address,
        "selected_value": selected_value,
        "register_value": selected_value if stored else prior_register,
        "address_selected": sentence_index >= 3,
        "returned_data_available": (7 <= sentence_index < 13) or revealed,
        "address_token_motion": sentence_index == 3,
        "return_token_motion": sentence_index == 7,
        "cursor_edge": cursor_edge,
        "storage_visible": stored,
        "prediction_replay": replay,
        "answer_hidden": replay,
        "illustration_scope": "original logical example; ordering only, not an analog delay simulation",
    }


def ideal_context_objects(state: dict) -> list[dict]:
    """Build stable exported objects for every interval of the ideal chapter."""
    edge = state["cursor_edge"]
    objects = [
        {
            "id": SOURCE_ID,
            "kind": "source_image",
            "label": "Original Part Va diagram, page 13",
            "page": 13,
            "provenance": "original_source",
        },
        {
            "id": CURSOR_ID,
            "kind": "geometry",
            "label": "Illustrative logical example: clock-edge reading cursor" if edge is None else f"Illustrative logical example: clock-edge reading cursor at event {edge}",
            "shape": "rectangle",
            "provenance": "conceptual",
            "state": {"edge": edge, "visible": edge is not None},
        },
        {
            "id": REGISTER_ID,
            "kind": "text",
            "label": f"Illustrative logical example: master MDR holds {state['register_value']}",
            "text": f"Illustrative logical example: MDR = {state['register_value']}",
            "provenance": "conceptual",
            "state": {
                "value": state["register_value"],
                "prior_value": state["prior_register"],
                "storage_visible": state["storage_visible"],
            },
        },
        {
            "id": SELECTED_ROW_ID,
            "kind": "text",
            "label": f"Illustrative logical example: selected memory row {state['selected_address']} stores {state['selected_value']}",
            "text": f"Illustrative logical example: Memory[{state['selected_address']}] = {state['selected_value']}",
            "provenance": "conceptual",
            "state": {
                "address": state["selected_address"],
                "value": state["selected_value"],
                "selected": state["address_selected"],
                "address_token_motion": state["address_token_motion"],
            },
        },
        {
            "id": RETURN_PATH_ID,
            "kind": "process",
            "label": "Illustrative logical example: returned-data path" if not state["returned_data_available"] else f"Illustrative logical example: returned-data path carries {state['selected_value']}",
            "nodes": ["Illustrative memory row 16", "Illustrative master MDR"],
            "provenance": "conceptual",
            "state": {
                "available": state["returned_data_available"],
                "value": state["selected_value"] if state["returned_data_available"] else None,
                "token_motion": state["return_token_motion"],
            },
        },
    ]
    if tuple(item["id"] for item in objects) != CONTEXT_IDS:
        raise AssertionError("Ideal-read context IDs changed unexpectedly")
    return deepcopy(objects)
