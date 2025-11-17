# controllers.py
from typing import Dict, List
from .blocks import Block

class CentralizedController:
    def __init__(self, blocks: Dict[str, Block]):
        self.blocks = blocks
        # per-block queue of train ids
        self.queues: Dict[str, List[str]] = {name: [] for name in blocks.keys()}
        self.STARVATION_THRESHOLD = 5.0  # seconds of waiting considered "aged"

    def request(self, train, block_name: str) -> bool:
        if block_name not in self.blocks:
            return False

        q = self.queues[block_name]
        if train.id not in q:
            q.append(train.id)

        blk = self.blocks[block_name]

        if blk.free():
            # check for any aged candidate in the queue (prevent starvation)
            aged_candidate = None
            for tid in q:
                t = train.sim_ref.trains.get(tid) if hasattr(train, "sim_ref") else None
                if t and t.wait >= self.STARVATION_THRESHOLD:
                    aged_candidate = tid
                    break

            front = aged_candidate if aged_candidate is not None else q[0]

            if front == train.id:
                # grant lock
                granted = blk.lock(train.id)
                if not granted:
                    return False
                # cleanup queue
                if train.id in q:
                    q.remove(train.id)
                # add to held
                if block_name not in train.held:
                    train.held.append(block_name)
                train.requesting = None
                return True
            else:
                return False
        else:
            return False

    def release(self, train, block_name: str):
        if block_name not in self.blocks:
            return
        blk = self.blocks[block_name]
        # Block.release will check ownership
        blk.release(train.id)
        # also ensure train.held is consistent (controller may be used externally)
        if block_name in train.held:
            try:
                train.held.remove(block_name)
            except ValueError:
                pass

    def force_assign(self, train, block_name: str) -> bool:
        """
        Force-assign a block to `train`. This will attempt to remove the block from any previous
        owner, clean up their held list, and assign it to `train`. Also clears train.requesting.
        """
        if block_name not in self.blocks:
            return False

        blk = self.blocks[block_name]
        prev_owner = blk.locked_by

        # If some other train held it, remove that reference
        if prev_owner and prev_owner != train.id:
            prev_train = None
            if hasattr(train, "sim_ref") and train.sim_ref:
                prev_train = train.sim_ref.trains.get(prev_owner)
            # clear previous train's held list entry
            if prev_train and block_name in prev_train.held:
                try:
                    prev_train.held.remove(block_name)
                except ValueError:
                    pass

        # remove any queue entry for this train on the block
        if train.id in self.queues.get(block_name, []):
            self.queues[block_name].remove(train.id)

        # forcibly assign
        blk.locked_by = train.id
        if block_name not in train.held:
            train.held.append(block_name)
        train.requesting = None
        return True


class OrderedLockingController(CentralizedController):
    def __init__(self, blocks: Dict[str, Block]):
        super().__init__(blocks)
        # global_order is lexicographic: A1..A4,B1.. etc.
        self.global_order = sorted(blocks.keys())

    def request(self, train, block_name: str) -> bool:
        if block_name not in self.blocks:
            return False

        # Allow ordering enforcement only within the same track prefix
        # e.g., if train already holds blocks on track 'A', only allow requests on 'A'
        # that are strictly after the highest held index on that track.
        req_track = block_name[0] if block_name else None
        if train.held and req_track:
            # find indices of held blocks that belong to same track
            held_indices_same_track = [
                self.global_order.index(b) for b in train.held if b in self.global_order and b[0] == req_track
            ]
            if held_indices_same_track:
                req_index = self.global_order.index(block_name)
                if any(req_index <= idx for idx in held_indices_same_track):
                    # requested block is not strictly after currently held blocks on same track
                    return False

        return super().request(train, block_name)
