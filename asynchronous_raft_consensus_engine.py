import asyncio
import random
import time
from enum import Enum
from typing import Dict, List, Optional


class NodeRole(Enum):
    FOLLOWER = 1
    CANDIDATE = 2
    LEADER = 3


class RaftNode:
    """
    A self-contained Raft Consensus Node handling Leader Election 
    and Heartbeat Keep-Alives via asynchronous event loops.
    """
    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = peers  # List of peer node IDs
        
        # Persistent State
        self.current_term: int = 0
        self.voted_for: Optional[str] = None
        self.log: List[Dict] = []
        
        # Volatile State
        self.role: NodeRole = NodeRole.FOLLOWER
        self.leader_id: Optional[str] = None
        self.last_heartbeat: float = time.time()
        
        # Async Control Tasks
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    async def start(self):
        """Bootstraps the asynchronous node event loop."""
        self._running = True
        self.last_heartbeat = time.time()
        self._loop_task = asyncio.create_task(self._event_loop())
        print(f"[{self.node_id}] Initialized as FOLLOWER (Term: {self.current_term})")

    async def stop(self):
        """Gracefully halts node execution."""
        self._running = False
        if self._loop_task:
            self._loop_task.cancel()
        print(f"[{self.node_id}] Shutdown complete.")

    # -------------------------------------------------------------------------
    # Core Event Loop & State Machine
    # -------------------------------------------------------------------------

    async def _event_loop(self):
        """Main execution thread evaluating timeouts and role transitions."""
        while self._running:
            if self.role == NodeRole.FOLLOWER or self.role == NodeRole.CANDIDATE:
                # Randomized election timeout (150ms - 300ms) to prevent split votes
                timeout = random.uniform(0.15, 0.30)
                if time.time() - self.last_heartbeat > timeout:
                    await self._start_election()
            elif self.role == NodeRole.LEADER:
                # Leader sends periodic heartbeats every 50ms
                await self._send_heartbeats()
                await asyncio.sleep(0.05)
                
            await asyncio.sleep(0.01)

    async def _start_election(self):
        """Transitions node to CANDIDATE and requests votes across the cluster."""
        self.role = NodeRole.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.last_heartbeat = time.time()
        
        votes_received = 1  # Self vote
        print(f"[{self.node_id}] Election Timeout! Starting election for Term {self.current_term}")

        # Broadcast RequestVote to all peers
        for peer in self.peers:
            granted = await self._rpc_request_vote(peer, self.current_term, self.node_id)
            if granted:
                votes_received += 1

        # Majority check (Quorum = (N / 2) + 1)
        quorum = ((len(self.peers) + 1) // 2) + 1
        if votes_received >= quorum and self.role == NodeRole.CANDIDATE:
            self.role = NodeRole.LEADER
            self.leader_id = self.node_id
            print(f"[{self.node_id}] QUORUM REACHED ({votes_received}/{len(self.peers)+1}). Promoted to LEADER!")
        else:
            # Fallback to Follower on election failure
            self.role = NodeRole.FOLLOWER
            self.voted_for = None

    async def _send_heartbeats(self):
        """Leader heartbeats to maintain cluster authority and prevent new elections."""
        for peer in self.peers:
            await self._rpc_append_entries(peer, self.current_term, self.node_id)

    # -------------------------------------------------------------------------
    # Simulated Remote Procedure Calls (RPCs)
    # -------------------------------------------------------------------------

    async def _rpc_request_vote(self, peer: str, term: int, candidate_id: str) -> bool:
        """Simulates an outbound RequestVote RPC to a peer node."""
        await asyncio.sleep(random.uniform(0.001, 0.005))  # Network latency simulation
        # In a real system, network layer evaluates node state:
        if term >= self.current_term:
            return True
        return False

    async def _rpc_append_entries(self, peer: str, term: int, leader_id: str):
        """Simulates an outbound AppendEntries (Heartbeat) RPC to a peer node."""
        await asyncio.sleep(random.uniform(0.001, 0.003))

    def receive_heartbeat(self, leader_id: str, term: int):
        """Inbound RPC handler triggered when a follower receives a Leader heartbeat."""
        if term >= self.current_term:
            self.current_term = term
            self.leader_id = leader_id
            self.role = NodeRole.FOLLOWER
            self.last_heartbeat = time.time()


# -------------------------------------------------------------------------
# Cluster Execution Runner
# -------------------------------------------------------------------------

async def main():
    print("--- STARTING 3-NODE RAFT CONSENSUS CLUSTER SIMULATION ---\n")
    
    # Initialize 3 distinct cluster nodes
    node_a = RaftNode("Node-A", ["Node-B", "Node-C"])
    node_b = RaftNode("Node-B", ["Node-A", "Node-C"])
    node_c = RaftNode("Node-C", ["Node-A", "Node-B"])

    nodes = [node_a, node_b, node_c]

    # Boot up all nodes concurrently
    for node in nodes:
        await node.start()

    # Let the cluster run long enough to elect a leader and stabilize
    await asyncio.sleep(0.5)

    # Shutdown the cluster
    for node in nodes:
        await node.stop()

if __name__ == "__main__":
    asyncio.run(main())