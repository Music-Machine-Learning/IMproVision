import math


class Note:
    _note_names = [("C"), ("C#", "Db"), ("D"), ("D#", "Eb"), ("E"), ("F"), ("F#", "Gb"), ("G"), ("G#", "Ab"), ("A"), ("A#", "Bb"), ("B")]
    _base_octave = -1

    def __init__(self, notedef):
        '''
        :param notedef: accepts three kinds of parameters:
           - string: decode note from string name (e.g. A2, C#4+24, ...)
           - float: create note from frequency
           - tuple: explicitly set note number and bend (e.g. (69, 0), (12, 32), ...)
        '''

        if type(notedef) is str:
            self.__from_string(notedef)
        elif type(notedef) is float or type(notedef) is int:
            self.__from_frequency(notedef)
        elif type(notedef) is tuple:
            self.note = int(notedef[0])
            self.bend = int(notedef[1])

        if self.note < 0 or self.note > 127:
            raise AttributeError("note {} out of midi range".format(self.note))
        if self.bend < 0 or self.bend > 127:
            raise AttributeError("bend {} out of midi range".format(self.bend))

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

    def __from_string(self, notename: str):
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
        self.note = notenum + (octavenum * 12)

        try:
            self.bend = int(bend)
        except ValueError:
            raise AttributeError("{} is not a valid bending value ({})".format(bend, notename))

    def freq(self):
        notefreq = 440 * 2 ** ((self.note - 69) / 12)
        return notefreq * 2 ** (self.bend / (12 * 128))

    def __from_frequency(self, freq: float):
        self.note = int(12 * math.log2(freq/440) + 69)
        self.bend = 0
        self.bend = int((12 * 128) * math.log2(freq / self.freq()))
        if self.bend < 0:
            self.note -= 1
            self.bend = 127 + self.bend


