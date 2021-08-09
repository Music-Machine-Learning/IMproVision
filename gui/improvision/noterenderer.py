from . import player
from .player import Note


class NoteRenderer:
    def render(self, vals: [(int, int)]) -> [Note]:
        notes = set()
        for val, maxv in vals:
            notes.add(self.render_note(val, maxv))
        return notes

    def render_note(self, val: int, max_val: int) -> Note:
        raise NotImplementedError


class ChromaticRenderer(NoteRenderer):
    def __init__(self, min_note: int, max_note: int):
        self.min_note = min_note
        self.max_note = max_note

    def render_note(self, val: int, max_val: int) -> Note:
        return Note(
            note=self.min_note + int(val * (self.max_note - self.min_note) / max_val),
        )


class DiatonicRenderer(NoteRenderer):
    def __init__(self, fundamental: Note, octaves_range: int, scale_notes: [Note]):
        self.fundamental = fundamental
        self.range = octaves_range
        self.scale = scale_notes
        self.totalnotes = octaves_range * len(scale_notes)

    def render_note(self, val: int, max_val: int) -> Note:
        trasl = int(round(val * self.totalnotes / max_val, 0))
        scalenote = self.scale[trasl % len(self.scale)]
        octave = int(trasl / len(self.scale))
        note = self.fundamental.note + scalenote.note + (octave * 12)
        return Note(
            note=note,
        )
