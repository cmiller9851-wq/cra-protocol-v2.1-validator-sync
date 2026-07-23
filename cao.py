import hashlib
import json
import logging
import math
import struct
import time
from typing import Any, Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("CRA_PROTOCOL_v2.1")


# =====================================================================
# 1. Pure Linear Algebra & Vector Mathematics
# =====================================================================

def vector_norm(v: List[float]) -> float:
    """Calculates Euclidean L2 norm of a vector."""
    return math.sqrt(sum(x * x for x in v)) or 1.0


def normalize_vector(v: List[float]) -> List[float]:
    """Scales a vector to unit length (L2 norm = 1.0)."""
    norm = vector_norm(v)
    return [x / norm for x in v]


def softmax(vector: List[float]) -> List[float]:
    """Computes stable numerical softmax over a 1D vector."""
    max_val = max(vector) if vector else 0.0
    exp_v = [math.exp(x - max_val) for x in vector]
    sum_exp = sum(exp_v) or 1.0
    return [x / sum_exp for x in exp_v]


def dot_product(v1: List[float], v2: List[float]) -> float:
    """Computes inner dot product of two equal-length vectors."""
    return sum(a * b for a, b in zip(v1, v2))


# =====================================================================
# 2. Deterministic Holographic State Engine
# =====================================================================

class HolographicStateEvaluator:
    """
    Evaluates process state transitions for Compute Units (CU) via
    ordered message interaction sequences.
    """

    def __init__(self, state_dim: int = 4):
        self.state_dim = state_dim
        # Initialize uniform baseline unit state
        initial_val = 1.0 / math.sqrt(state_dim)
        self.current_state: List[float] = [initial_val] * state_dim

    def process_payload_vector(self, raw_payload: List[float]) -> List[float]:
        """Enforces uniform dimension constraints (truncates or zero-pads)."""
        if len(raw_payload) < self.state_dim:
            return raw_payload + [0.0] * (self.state_dim - len(raw_payload))
        return raw_payload[: self.state_dim]

    def evaluate_transition(self, current_state: List[float], payload: List[float]) -> List[float]:
        """
        Executes a deterministic state projection:
        Blends prior state tensor and payload weighted by softmax attention.
        """
        padded_payload = self.process_payload_vector(payload)
        attn_weights = softmax(padded_payload)

        # Convex combination of prior state and input payload
        next_state = [
            (s * w) + (p * (1.0 - w))
            for s, w, p in zip(current_state, attn_weights, padded_payload)
        ]

        return normalize_vector(next_state)


# =====================================================================
# 3. Process Execution & State Checkpoint Auditor
# =====================================================================

class ComputeUnitProcess:
    """
    Stateless, isolated process runner enforcing deterministic state
    progression and snapshot verification.
    """

    def __init__(self, process_id: str, protocol_version: str = "CRA_PROTOCOL_v2.1", state_dim: int = 4):
        self.process_id = process_id
        self.protocol_version = protocol_version
        self.evaluator = HolographicStateEvaluator(state_dim=state_dim)
        self.message_log: List[Dict[str, Any]] = []
        self.state_hashes: List[str] = []

    def compute_canonical_hash(self, nonce: int, state_vector: List[float]) -> str:
        """
        Generates a strict binary-packed SHA-256 state hash.
        Fixed double-precision floats prevent cross-platform string variation.
        """
        buffer = bytearray()
        buffer.extend(self.process_id.encode("utf-8"))
        buffer.extend(struct.pack(">Q", nonce))  # Unsigned 64-bit int, big-endian

        for val in state_vector:
            buffer.extend(struct.pack(">d", round(val, 8)))  # Double precision float

        return hashlib.sha256(buffer).hexdigest()[:16]

    def ingest_message(self, message_id: str, nonce: int, vector_payload: List[float]) -> str:
        """
        Ingests a message item, updates state, and records audit snapshot.
        """
        msg_item = {
            "id": message_id,
            "nonce": nonce,
            "timestamp": time.time(),
            "payload": vector_payload,
        }
        self.message_log.append(msg_item)

        # Pure state update
        new_state = self.evaluator.evaluate_transition(
            current_state=self.evaluator.current_state,
            payload=vector_payload
        )
        self.evaluator.current_state = new_state

        # Compute deterministic cryptographic snapshot
        state_hash = self.compute_canonical_hash(nonce=nonce, state_vector=new_state)
        self.state_hashes.append(state_hash)

        logger.info(f"Process [{self.process_id}] Msg [{message_id}] Nonce [{nonce}] -> State Hash: {state_hash}")
        return state_hash

    def get_holographic_projection(self) -> Dict[str, Any]:
        """Outputs current state representation."""
        return {
            "process_id": self.process_id,
            "protocol": self.protocol_version,
            "message_count": len(self.message_log),
            "state_vector": [round(x, 8) for x in self.evaluator.current_state],
            "latest_snapshot_hash": self.state_hashes[-1] if self.state_hashes else None,
        }


# =====================================================================
# 4. Verification Execution
# =====================================================================

if __name__ == "__main__":
    PROCESS_ID = "process_cra_v2_1_prod_01"

    logger.info("Initializing Compute Unit Execution Engine")
    runner = ComputeUnitProcess(process_id=PROCESS_ID, state_dim=4)

    # Ingest message queue
    incoming_queue = [
        {"msg_id": "msg_001", "nonce": 1, "payload": [0.85, 0.15, 0.45, 0.20]},
        {"msg_id": "msg_002", "nonce": 2, "payload": [0.10, 0.95, 0.30, 0.70]},
        {"msg_id": "msg_003", "nonce": 3, "payload": [0.50, 0.50, 0.85, 0.10]},
    ]

    print("\n--- State Transition Sequence ---")
    for item in incoming_queue:
        runner.ingest_message(
            message_id=item["msg_id"],
            nonce=item["nonce"],
            vector_payload=item["payload"],
        )

    projection = runner.get_holographic_projection()
    print("\n--- Holographic State Projection ---")
    print(json.dumps(projection, indent=2))
