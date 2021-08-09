from . import player


class NoteRenderer:
    def render(self, vals: [(int, int)]) -> [player.Note]:
        notes = []
        for val, maxv in vals:
            notes.append(self.render_note(val, maxv))
        return notes

    def render_note(self, val: int, max_val: int) -> player.Note:
        raise NotImplementedError


class ChromaticRenderer(NoteRenderer):
    def __init__(self, min_note: int, max_note: int):
        self.min_note = min_note
        self.max_note = max_note

    def render_note(self, val: int, max_val: int) -> player.Note:
        return player.Note(
            note=self.min_note + int(val * (self.max_note - self.min_note) / max_val),
            bend=0, noteon=True,
        )
