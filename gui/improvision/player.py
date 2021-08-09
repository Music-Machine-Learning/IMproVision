from pygame import midi

class Note:
    def __init__(self, note, bend, noteon):
        self.note = note
        self.bend = bend
        self.noteon = noteon

    def __str__(self):
        return "note: {} (b: {}), on: {}".format(self.note, self.bend, self.noteon)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return self.note == other.note and self.bend == other.bend and self.noteon == other.noteon

    def __lt__(self, other):
        return self.note < other.note or (
            self.note == other.note and self.bend < other.bend or
            (
                self.note == other.note and self.bend == other.bend and not self.noteon and other.noteon
            )
        )


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


class MidiPlayer(NotePlayer):
    def __init__(self, device_id=None, channel=0):
        self.active_notes = []
        if not midi.get_init():
            midi.init()
        self.channel = channel
        if device_id is None:
            self.output = midi.Output(midi.get_default_output_id())
        else:
            self.output = midi.Output(device_id)

    def play(self, notes: [Note]):
        play_notes = []
        stop_notes = self.active_notes[:]
        for n in notes:
            if n in self.active_notes:
                stop_notes.remove(n)
            else:
                play_notes.append(n)

        for n in stop_notes:
            self.output.note_off(n.note, velocity=0, channel=self.channel)
            self.active_notes.remove(n)

        for n in play_notes:
            self.output.note_on(n.note, velocity=127, channel=self.channel)
            self.active_notes.append(n)
