import threading
import queue

class IMproVisionConsumer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self, daemon=True)
        self.queue = queue.SimpleQueue()

    def run(self) -> None:
        while True:
            self.process_data(self.queue.get(True, None))

    def data_ready(self, color_column):
        self.queue.put(color_column, False)

    def process_data(self, color_column):
        raise NotImplementedError


class IMproVisionLumaConsumer(IMproVisionConsumer):
    def __init__(self, minluma, maxluma):
        IMproVisionConsumer.__init__(self)
        self.minluma = minluma
        self.maxluma = maxluma

    def process_data(self, color_column):
        notes = []
        window = 0
        windowsize = 0
        for y in range(len(color_column)):
            luma = color_column[y].get_luma()
            if self.minluma <= luma <= self.maxluma:
                window += y
                windowsize += 1
            else:
                if windowsize > 0:
                    notes.append(len(color_column) - int(window / windowsize))
                    window = 0
                    windowsize = 0

        print("notes: {}".format(notes))
