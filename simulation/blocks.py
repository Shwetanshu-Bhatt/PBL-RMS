# blocks.py
class Block:
    def __init__(self, name: str):
        self.name = name
        self.locked_by = None

    def free(self):
        return self.locked_by is None

    def lock(self, train_id: str) -> bool:
        if self.locked_by is None:
            self.locked_by = train_id
            return True
        return False

    def release(self, train_id: str):
        if self.locked_by == train_id:
            self.locked_by = None
