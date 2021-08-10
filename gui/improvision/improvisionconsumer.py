import threading
import queue

from lib.gibindings import Gtk
from .noterenderer import NoteRenderer
from .player import NotePlayer
from .configurable import Configurable, Configuration


class IMproVisionConsumer(threading.Thread):
    def __init__(self,  renderer: NoteRenderer, players: [NotePlayer]):
        threading.Thread.__init__(self, daemon=True)
        self.renderer = renderer
        if type(players) is list:
            self.players = players
        else:
            self.players = [players]
        self.queue = queue.SimpleQueue()

    def run(self) -> None:
        while True:
            notes = self.renderer.render(
                self.process_data(self.queue.get(True, None))
            )
            for p in self.players:
                p.play(notes)

    def stop(self):
        for p in self.players:
            p.stop()

    def data_ready(self, color_column):
        self.queue.put(color_column, False)

    # subclasses must implement this method
    def process_data(self, color_column) -> [(int, int)]:
        raise NotImplementedError


class IMproVisionLumaConsumer(IMproVisionConsumer, Configurable):
    def __init__(self, renderer: NoteRenderer, player: NotePlayer, app, minluma: float, maxluma: float):
        IMproVisionConsumer.__init__(self, renderer, player)

        def configureDecimalSpinbuttons(sb: Gtk.SpinButton):
            sb.set_digits(2)

        Configurable.__init__(self, 'Luma Detector', {
            "minluma": Configuration(
                "Min Luma", "improvision-luma-minluma", app, Gtk.SpinButton,
                minluma, 0, 1, step_incr=0.01, page_incr=0.1, gui_setup_cb=configureDecimalSpinbuttons
            ),
            "maxluma": Configuration(
                "Max Luma", "improvision-luma-maxluma", app, Gtk.SpinButton,
                maxluma, 0, 1, step_incr=0.01, page_incr=0.1, gui_setup_cb=configureDecimalSpinbuttons
            ),
        })

    def process_data(self, color_column):
        notes = []
        window = 0
        windowsize = 0
        maxv = len(color_column)
        for y in range(maxv):
            luma = color_column[y].get_luma()
            if self.minluma <= luma <= self.maxluma:
                window += y
                windowsize += 1
            else:
                if windowsize > 0:
                    notes.append((maxv - int(window / windowsize), maxv))
                    window = 0
                    windowsize = 0

        return notes
