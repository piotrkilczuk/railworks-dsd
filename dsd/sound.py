import os
import threading
import winsound


__all__ = (
    'Beeper',
)


class Beeper(object):

    running = False
    thread = None

    sound_beep = None
    sound_silence = None

    def __init__(self):
        sound_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'binary'))
        self.sound_beep = os.path.join(sound_dir, 'dsd-beep.wav')

    def _main_loop(self):
        winsound.PlaySound(self.sound_beep, winsound.SND_ASYNC | winsound.SND_LOOP)
        while self.running:
            pass
        winsound.PlaySound(self.sound_beep, winsound.SND_PURGE)  # TODO: replace with silence / fadeout

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._main_loop)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()
