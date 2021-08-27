import math


class Note:
    _note_names = [("C"), ("C#", "Db"), ("D"), ("D#", "Eb"), ("E"), ("F"), ("F#", "Gb"), ("G"), ("G#", "Ab"), ("A"), ("A#", "Bb"), ("B")]
    _base_octave = -1

    def __init__(self, note, bend=0):
        self.note = int(note)
        if note < 0 or note > 127:
            raise AttributeError("note {} out of midi range".format(note))
        self.bend = int(bend)
        if bend < 0 or bend > 127:
            raise AttributeError("bend {} out of midi range".format(bend))

    def __repr__(self):
        return str(self) + ", note: {}, bend: {}, freq: {}".format(self.note, self.bend, self.freq())

    def __hash__(self):
        return hash((self.note, self.bend))

    def __eq__(self, other):
        return self.note == other.note and self.bend == other.bend

    def __lt__(self, other):
        return self.note < other.note or (self.note == other.note and self.bend < other.bend)

    def __str__(self):
        note = self._note_names[self.note % len(self._note_names)][0]
        octave = int(math.floor(self.note / len(self._note_names)) + self._base_octave)
        if self.bend == 0:
            return note + str(octave)
        else:
            return note + str(octave) + "+" + str(self.bend)

    @staticmethod
    def from_string(notename: str):
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

        notename = notename[len(note):]

        if '+' in notename:
            octave = notename[:notename.index('+')]
            bend = notename[notename.index('+')+1:]
        else:
            octave = notename
            bend = "0"

        try:
            octavenum = int(octave) - Note._base_octave
        except ValueError:
            raise AttributeError("{} is not a valid octave number ({})".format(octave, notename))

        try:
            bendnum = int(bend)
        except ValueError:
            raise AttributeError("{} is not a valid bending value ({})".format(bend, notename))

        return Note(notenum + (octavenum * 12), bendnum)

    def freq(self):
        notefreq = 440 * 2 ** ((self.note - 69) / 12)
        return notefreq * 2 ** (self.bend / (12 * 128))

    @staticmethod
    def from_frequency(freq: float):
        note = int(12 * math.log2(freq/440) + 69)
        bend = int((12 * 128) * math.log2(freq / Note(note).freq()))
        if bend < 0:
            note -= 1
            bend = 127 + bend
        return Note(note, bend)


