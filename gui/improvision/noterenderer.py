from .player import Note
from .configurable import Configurable, Configuration
from lib.gibindings import Gtk


class NoteRenderer(Configurable):
    def __init__(self):
        Configurable.__init__(self)

    def render(self, vals: [(int, int)]) -> [Note]:
        notes = set()
        for val, maxv in vals:
            notes.add(self.render_note(val, maxv))
        return notes

    def render_note(self, val: int, max_val: int) -> Note:
        raise NotImplementedError


class ChromaticRenderer(NoteRenderer):
    def __init__(self, app):
        Configurable.__init__(
            self, "Chromatic Renderer",
            {
                "min_note": Configuration("Lowest Note", "improvision-chromatic-renderer-minnote", app,
                                          Gtk.SpinButton, 21, 0, 127),
                "max_note": Configuration("Highest Note", "improvision-chromatic-renderer-maxnote", app,
                                          Gtk.SpinButton, 107, 0, 127),
            })

    def render_note(self, val: int, max_val: int) -> Note:
        return Note(
            note=self.min_note + int(val * (self.max_note - self.min_note) / max_val),
        )


class DiatonicRenderer(NoteRenderer):
    MinorPentatonic = [Note(0), Note(3), Note(5), Note(7), Note(10)]
    MajorPentatonic = [Note(0), Note(2), Note(4), Note(7), Note(9)]
    Major = [Note(0), Note(2), Note(4), Note(5), Note(7), Note(9), Note(11)]
    MinorNatural = [Note(0), Note(2), Note(3), Note(5), Note(7), Note(8), Note(10)]
    MinorHarmonic = [Note(0), Note(2), Note(3), Note(5), Note(7), Note(8), Note(11)]

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
