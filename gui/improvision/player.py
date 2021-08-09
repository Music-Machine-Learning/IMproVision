class Note:
    def __init__(self, note, bend, noteon):
        self.note = note
        self.bend = bend
        self.noteon = noteon

    def __str__(self):
        return "note: {} (b: {}), on: {}".format(self.note, self.bend, self.noteon)

    def __repr__(self):
        return str(self)


class AbsoluteNote(Note):
    def __init__(self, freq, noteon):
        self.freq = freq
        #TODO: translate freq to note

    def __str__(self):
        return "freq: {}, {}".format(self.freq, Note.__str__(self))


class NotePlayer:
    def play(self, notes: [Note]):
        raise NotImplementedError


class LogPlayer(NotePlayer):
    def play(self, notes: [Note]):
        print(notes)
