import math

class Note:
    _note_names = [("C"), ("C#", "Db"), ("D"), ("D#", "Eb"), ("E"), ("F"), ("F#", "Gb"), ("G"), ("G#", "Ab"), ("A"), ("A#", "Bb"), ("B")]
    _base_octave = -1

    def __init__(self, note, bend=0, noteon=True):
        self.note = int(note)
        if note < 0 or note > 127:
            raise AttributeError("note {} out of midi range".format(note))
        self.bend = int(bend)
        if bend < 0 or bend > 127:
            raise AttributeError("bend {} out of midi range".format(bend))
        self.noteon = noteon

    def __str__(self):
        note = self._note_names[self.note % len(self._note_names)][0]
        octave = int(math.floor(self.note / len(self._note_names)) + self._base_octave)
        return note + str(octave)

    def __repr__(self):
        return str(self) + " ({}, f: {}), b: {}, on: {}".format(self.note, self.freq(), self.bend, self.noteon)

    def __hash__(self):
        return hash((self.note, self.bend, self.noteon))

    def __eq__(self, other):
        return self.note == other.note and self.bend == other.bend and self.noteon == other.noteon

    def __lt__(self, other):
        return self.note < other.note or (
                self.note == other.note and self.bend < other.bend or
                (
                        self.note == other.note and self.bend == other.bend and not self.noteon and other.noteon
                )
        )

    def freq(self):
        return 440 * 2 ** ((self.note - 69) / 12)

    @staticmethod
    def from_string(notename: str, noteon=True):
        if type(notename) is not str:
            raise AttributeError("{} must be a string".format(notename))
        notename = notename.strip()
        notename = notename[0].upper() + notename[1:].lower()
        note = notename[:1]
        if notename[1] == '#' or notename[1] == 'b':
            note = notename[:2]
        notenum = None
        for n in range(len(Note._note_names)):
            if note in Note._note_names[n]:
                notenum = n
        if notenum is None:
            raise AttributeError("{} is not a valid note name".format(notename))

        octave = notename[len(note):]
        try:
            octavenum = int(octave) - Note._base_octave
        except ValueError:
            raise AttributeError("{} is not a valid octave number ({})".format(octave, notename))

        return Note(notenum + (octavenum * 12), noteon=noteon)

    @staticmethod
    def from_frequency(freq: float, noteon=True):
        note = int(12 * math.log2(freq/440) + 69)
        bend = int((12 * 128) * math.log2(freq / Note(note).freq()))
        if bend < 0:
            note -= 1
            bend = 127 + bend
        return Note(note, bend, noteon)

