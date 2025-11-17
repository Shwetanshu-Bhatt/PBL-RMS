# simulator.py
from .blocks import Block
from .controllers import CentralizedController, OrderedLockingController

class Train:
    def __init__(self, id, track, speed, sim_ref=None):
        self.id = id
        self.track = track
        self.speed = speed
        self.block_idx = 0
        self.pos = 0.0
        self.status = "running"
        self.requesting = None
        self.held = []
        self.wait = 0.0
        self.route_index = 0
        self.sim_ref = sim_ref
        self.switch_cooldown = 0  # ticks

    def to_dict(self):
        return {
            "id": self.id,
            "track": self.track,
            "pos": round(self.pos, 3),
            "status": self.status,
            "waiting_time": round(self.wait, 3)
        }

class Simulator:
    TICK = 0.1
    SAFE_DISTANCE = 0.18
    TRANSFER_TIME = 0.8

    def __init__(self):
        self.running = False
        self.mode = "centralized"
        self._init_structure()
        self.deadlocks = 0
        self.no_progress = 0

    def _init_structure(self):
        self.tracks = {}
        self.blocks = {}
        for tname in ["A","B","C"]:
            self.tracks[tname] = []
            for i in range(1,5):
                bname = f"{tname}{i}"
                blk = Block(bname)
                self.blocks[bname] = blk
                self.tracks[tname].append(bname)

        self.trains = {
            "T1": Train("T1", "A", 0.03, sim_ref=self),
            "T2": Train("T2", "B", 0.026, sim_ref=self),
            "T3": Train("T3", "C", 0.034, sim_ref=self)
        }

        # initially lock first block for each train
        for t in self.trains.values():
            fb = f"{t.track}1"
            self.blocks[fb].lock(t.id)
            t.held = [fb]
            t.block_idx = 0
            t.pos = 0.0
            t.status = "running"
            t.requesting = None
            t.wait = 0.0
            t.switch_cooldown = 0

        self.set_controller(self.mode)
        self.deadlocks = 0
        self.no_progress = 0

    def reset(self):
        self._init_structure()

    def set_controller(self, mode):
        self.mode = mode
        if mode == "ordered":
            self.controller = OrderedLockingController(self.blocks)
        else:
            self.controller = CentralizedController(self.blocks)

    def build_wait_for_graph(self):
        graph = {tid: set() for tid in self.trains.keys()}
        for t in self.trains.values():
            if t.requesting:
                owner = self.blocks[t.requesting].locked_by
                if owner and owner != t.id:
                    graph[t.id].add(owner)
        return graph

    def detect_cycle(self, graph):
        WHITE, GREY, BLACK = 0,1,2
        color = {n: WHITE for n in graph}
        parent = {}
        def dfs(u):
            color[u] = GREY
            for v in graph[u]:
                if color[v] == WHITE:
                    parent[v] = u
                    cyc = dfs(v)
                    if cyc: return cyc
                elif color[v] == GREY:
                    cycle = [v]
                    cur = u
                    while cur != v and cur is not None:
                        cycle.append(cur)
                        cur = parent.get(cur)
                    cycle.append(v)
                    cycle.reverse()
                    return cycle
            color[u] = BLACK
            return None
        for n in graph:
            if color[n] == WHITE:
                parent[n] = None
                cyc = dfs(n)
                if cyc: return cyc
        return None

    def safe_to_enter(self, t, target_track):
        """
        Conservative check whether it's safe to enter the entry block of `target_track`.
        This ensures we don't collide with a train already on that track. If you want
        to loosen constraints for debugging animation, return True here.
        """
        entry = f"{target_track}1"
        blk = self.blocks.get(entry)
        if not blk or not blk.free():
            return False
        # find other trains on that target_track
        others = [x for x in self.trains.values() if x.track == target_track and x.id != t.id]
        if not others:
            return True
        nearest = min(others, key=lambda x: x.pos)
        future = nearest.pos + nearest.speed * self.TRANSFER_TIME
        # small relaxation compared to original strict check
        return future + 0.05 >= Simulator.SAFE_DISTANCE

    def _release_block_if_held(self, train, block_name):
        """Helper to release block both in Block and train.held list."""
        if block_name in self.blocks:
            self.controller.release(train, block_name)

    def step(self):
        if not self.running:
            return

        made_progress = False

        # decrement switch cooldowns and advance trains
        for t in self.trains.values():
            if t.switch_cooldown > 0:
                t.switch_cooldown -= 1

            if t.status == "running":
                t.pos += t.speed
                if t.pos >= 1.0:
                    t.pos = 1.0
                    next_idx = t.block_idx + 1
                    track_list = self.tracks[t.track]

                    # reached end of current track
                    if next_idx >= len(track_list):
                        # leaving this track: release last block only after successfully getting entry of next track
                        last_block = track_list[t.block_idx]

                        # decide next circular track
                        seq = ["A","B","C"]
                        next_track = seq[(seq.index(t.track) + 1) % 3]
                        entry = f"{next_track}1"

                        # attempt to enter next track
                        if t.switch_cooldown == 0 and self.safe_to_enter(t, next_track) and self.controller.request(t, entry):
                            # release last block cleanly (we transfer ownership - train continues to hold entry)
                            if last_block in t.held:
                                self.controller.release(t, last_block)
                            # reassign train to new track/list index
                            t.track = next_track
                            t.block_idx = 0
                            t.pos = 0.0
                            t.status = "running"
                            t.wait = 0.0
                            # small cooldown to avoid immediate re-switch spam (in ticks)
                            t.switch_cooldown = 2
                            made_progress = True
                        else:
                            t.status = "waiting_end"
                            t.requesting = entry
                            t.wait += self.TICK

                    else:
                        # normal move to next block within same track
                        nxt = track_list[next_idx]
                        t.requesting = nxt
                        # try to request the next block
                        if t.switch_cooldown == 0 and self.controller.request(t, nxt):
                            # release old block after acquiring new block
                            old = track_list[t.block_idx]
                            if old in t.held:
                                self.controller.release(t, old)
                            t.block_idx = next_idx
                            t.pos = 0.0
                            t.status = "running"
                            t.wait = 0.0
                            made_progress = True
                        else:
                            t.status = "waiting"
                            t.wait += self.TICK

            elif t.status in ("waiting", "waiting_end"):
                if t.requesting:
                    target_track = t.requesting[0]

                    if t.status == "waiting_end":
                        # waiting to get onto another track's entry block
                        if t.switch_cooldown == 0 and self.safe_to_enter(t, target_track) and self.controller.request(t, t.requesting):
                            # release all previous held blocks (transfer onto new block)
                            # safe to release everything because we just acquired entry
                            for b in list(t.held):
                                if b != t.requesting:
                                    self.controller.release(t, b)
                            # find which track the requested block belongs to and update state
                            for tr_name, blist in self.tracks.items():
                                if t.requesting in blist:
                                    t.track = tr_name
                                    t.block_idx = blist.index(t.requesting)
                                    break
                            t.pos = 0.0
                            t.status = "running"
                            t.wait = 0.0
                            t.switch_cooldown = 2
                            made_progress = True
                        else:
                            t.wait += self.TICK
                    else:
                        # waiting for next block on same track
                        if t.switch_cooldown == 0 and self.controller.request(t, t.requesting):
                            # release older block(s) - keep only the newly acquired block
                            for b in list(t.held):
                                if b != t.requesting:
                                    self.controller.release(t, b)
                            for tr_name, blist in self.tracks.items():
                                if t.requesting in blist:
                                    t.track = tr_name
                                    t.block_idx = blist.index(t.requesting)
                                    break
                            t.pos = 0.0
                            t.status = "running"
                            t.wait = 0.0
                            made_progress = True
                        else:
                            t.wait += self.TICK

        # build wait-for graph and detect deadlocks
        wfg = self.build_wait_for_graph()
        cycle = self.detect_cycle(wfg)
        if cycle:
            self.deadlocks += 1
            # pick victim: train in cycle with max wait
            victim = max((self.trains[x] for x in cycle), key=lambda u: u.wait)
            if victim.requesting:
                # release all victim's held locks to avoid ghost-locks
                for b in list(victim.held):
                    self.controller.release(victim, b)
                victim.held = []
                # force-assign the requested block
                self.controller.force_assign(victim, victim.requesting)
                # update victim's position/state to reflect the assignment
                for tr, blist in self.tracks.items():
                    if victim.requesting in blist:
                        victim.track = tr
                        victim.block_idx = blist.index(victim.requesting)
                        break
                victim.pos = 0.0
                victim.status = "running"
                victim.wait = 0.0
                victim.switch_cooldown = 2

        else:
            # no cycle: track progress or stagnation
            if any(t.wait > 0 for t in self.trains.values()):
                self.no_progress = 0
            else:
                self.no_progress += 1
            if self.no_progress > 50:
                # emergency: pick the train with max wait and force progress
                v = max(self.trains.values(), key=lambda u: u.wait)
                if v.requesting:
                    for b in list(v.held):
                        self.controller.release(v, b)
                    v.held = []
                    self.controller.force_assign(v, v.requesting)
                    for tr, blist in self.tracks.items():
                        if v.requesting in blist:
                            v.track = tr
                            v.block_idx = blist.index(v.requesting)
                            break
                    v.pos = 0.0
                    v.status = "running"
                    v.wait = 0.0
                    v.switch_cooldown = 2
                self.no_progress = 0

    def export(self):
        return {
            "trains": [t.to_dict() for t in self.trains.values()],
            "deadlocks": self.deadlocks,
            "trackStatus": {
                tr: ",".join([self.blocks[b].locked_by or "free" for b in blist])
                for tr, blist in self.tracks.items()
            }
        }
