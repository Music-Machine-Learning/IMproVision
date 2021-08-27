from .note import Note, NoteConfiguration
from .configurable import Configurable, NumericConfiguration, ListConfiguration
from lib.gibindings import Gtk


class NoteRenderer(Configurable):
    def __init__(self):
        super().__init__(expanded=True)

    def render(self, vals: [(int, int)]) -> [Note]:
        notes = set()
        for val, maxv in vals:
            notes.add(self.render_note(val, maxv))
        return notes

    def render_note(self, val: int, max_val: int) -> Note:
        raise NotImplementedError


class ChromaticRenderer(NoteRenderer):
    def __init__(self, minnote: Note, maxnote: Note):
        Configurable.__init__(
            self, "Chromatic Renderer", "chromatic-renderer",
            {
                "min_note": NoteConfiguration("Lowest Note", "minnote", minnote),
                "max_note": NoteConfiguration("Highest Note", "maxnote", maxnote),
            })

    def render_note(self, val: int, max_val: int) -> Note:
        return self.min_note + int(val * (self.max_note - self.min_note).note / max_val)

class DiatonicRenderer(NoteRenderer):
    scales = {
        'minor pentatonic': [Note(0), Note(3), Note(5), Note(7), Note(10)],
        'major pentatonic': [Note(0), Note(2), Note(4), Note(7), Note(9)],
        'major': [Note(0), Note(2), Note(4), Note(5), Note(7), Note(9), Note(11)],
        'minor natural': [Note(0), Note(2), Note(3), Note(5), Note(7), Note(8), Note(10)],
        'minor harmonic': [Note(0), Note(2), Note(3), Note(5), Note(7), Note(8), Note(11)],
    }

    def __init__(self, fundamental: Note, octaves_range: int, scale: str):
        super().__init__()

        self.setup_configurable("Diatonic Reader", 'diatonic', {
            'range': NumericConfiguration("Octaves Range", 'range',
                                   Gtk.SpinButton, octaves_range, 1, 16),
            'fundamental': NoteConfiguration("Fundamental", 'fundamental', fundamental),
            'scale': ListConfiguration("Scale", 'scale', scale, self.scales),
        })

    def render_note(self, val: int, max_val: int) -> Note:
        scale = self.scale
        trasl = int(round(val * ((self.range * len(scale))-1) / max_val, 0))
        scalenote = scale[trasl % len(scale)]
        octave = int(trasl / len(scale))
        return self.fundamental + scalenote.note + (octave * 12)
