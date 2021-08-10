from pygame import midi
from .configurable import Configurable


class Note:
    def __init__(self, note, bend=0, noteon=True):
        self.note = int(note)
        self.bend = int(bend)
        self.noteon = noteon

    def __str__(self):
        return "note: {} (b: {}), on: {}".format(self.note, self.bend, self.noteon)

    def __repr__(self):
        return str(self)

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


class AbsoluteNote(Note):
    def __init__(self, freq, noteon):
        self.freq = freq
        #TODO: translate freq to note

    def __str__(self):
        return "freq: {}, {}".format(self.freq, Note.__str__(self))


class NotePlayer(Configurable):
    def __init__(self):
        Configurable.__init__(self)
        self.active_notes = set()

    def __del__(self):
        self.stop()

    def play(self, notes: set[Note]):
        stop_notes = self.active_notes - notes
        play_notes = notes - self.active_notes

        if len(play_notes) > 0:
            self.notes_on(play_notes)
        if len(stop_notes) > 0:
            self.notes_off(stop_notes)

        self.active_notes -= stop_notes
        self.active_notes |= play_notes

    def stop(self):
        self.notes_off(self.active_notes)
        self.active_notes = set()

    def notes_on(self, notes: set[Note]):
        raise NotImplementedError

    def notes_off(self, notes: set[Note]):
        raise NotImplementedError


class LogPlayer(NotePlayer):
    def notes_on(self, notes: set[Note]):
        print("notes on: {}, active_notes: {}".format(notes, self.active_notes))

    def notes_off(self, notes: set[Note]):
        print("notes off: {}, active_notes: {}".format(notes, self.active_notes))


class MidiPlayer(NotePlayer):
    def __init__(self, device_id=None, channel=0):
        NotePlayer.__init__(self)
        if not midi.get_init():
            midi.init()
        self.channel = channel
        if device_id is None:
            self.output = midi.Output(midi.get_default_output_id())
        else:
            self.output = midi.Output(device_id)

    def notes_on(self, notes: set[Note]):
        for n in notes:
            self.output.note_on(n.note, velocity=127, channel=self.channel)

    def notes_off(self, notes: set[Note]):
        for n in notes:
            self.output.note_off(n.note, velocity=0, channel=self.channel)


class MonoMidiPlayer(MidiPlayer):
    def __init__(self, device_id=None, channel=0, priority_high=False):
        super().__init__(device_id, channel)
        self.priority_high = priority_high

    def play(self, notes: set[Note]):
        if len(notes) > 0:
            pn = set()
            if self.priority_high:
                pn.add(max(notes))
            else:
                pn.add(min(notes))
        else:
            pn = notes
        super().play(pn)

