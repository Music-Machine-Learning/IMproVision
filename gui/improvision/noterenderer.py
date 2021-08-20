from .player import Note
from .configurable import Configurable, NumericConfiguration, ListConfiguration
from lib.gibindings import Gtk


class NoteRenderer(Configurable):
    def __init__(self):
        super().__init__()

    def render(self, vals: [(int, int)]) -> [Note]:
        notes = set()
        for val, maxv in vals:
            notes.add(self.render_note(val, maxv))
        return notes

    def render_note(self, val: int, max_val: int) -> Note:
        raise NotImplementedError


class ChromaticRenderer(NoteRenderer):
    def __init__(self):
        Configurable.__init__(
            self, "Chromatic Renderer", "chromatic-renderer",
            {
                "min_note": Configuration("Lowest Note", "minnote",
                                          Gtk.SpinButton, 21, 0, 127),
                "max_note": Configuration("Highest Note", "maxnote",
                                          Gtk.SpinButton, 107, 0, 127),
            })

    def render_note(self, val: int, max_val: int) -> Note:
        return Note(
            note=self.min_note + int(val * (self.max_note - self.min_note) / max_val),
        )


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
            'fundamental': NumericConfiguration("Fundamental", 'fundamental',
                                   Gtk.SpinButton, fundamental.note, 0, 127),
            'scale': ListConfiguration("Scale", 'scale', scale, self.scales),
        })

    def render_note(self, val: int, max_val: int) -> Note:
        scale = self.scale
        trasl = int(round(val * (self.range * (len(scale)-1)) / max_val, 0))
        scalenote = scale[trasl % len(scale)]
        octave = int(trasl / len(scale))
        note = self.fundamental + scalenote.note + (octave * 12)
        return Note(
            note=min(max(int(note), 0), 127) #limit note in
        )
