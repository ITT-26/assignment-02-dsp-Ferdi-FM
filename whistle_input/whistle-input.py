import sounddevice as sd
import numpy as np
import pyglet
import os
import pynput
from enum import IntEnum

#Notes:
# - I can't really controll whistling up (I can only do down reliably, got better while testing)
# - Short whistleing to move 1, longer to move faster

CHUNK_SIZE = 1024
RATE = 11024
CHANNELS = 1
MENU_ITEMS = 5 
START_INDEX = MENU_ITEMS-1 #starts at top since im better at whistling down
DETECTION_THRESHOLD = int(RATE / CHUNK_SIZE * 0.5) #0.5 = Seconds a trend needs to occur to trigger a movement, since Rate/Chunks is how many callbacks per second there are (0.6/0.7 might be better)
win = pyglet.window.Window(2000, 1000)

class KeyDirection(IntEnum):
    KEY_LEFT = 0
    KEY_RIGHT = 1
    KEY_UP = 2
    KEY_DOWN = 3

class WhistleInput:
    def __init__(self):  
        self.batch = pyglet.graphics.Batch()
        self.menu = []
        self.last_Freq = 0
        self.selected_Index = START_INDEX
        self.moveMent_Threshold = 0
        self.keyboard_Controller = pynput.keyboard.Controller()

        print("Available input devices:\n")
        devices = sd.query_devices()

        self.input_devices = []
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                print(f"{i}: {dev['name']}")
                self.input_devices.append(i)

        if not self.input_devices:
            print("No Input Devices were found\nClosing the Script")
            os._exit(0)

        self.input_device = int(input("\nSelect input device: "))

        self.stream = sd.InputStream(
            device=self.input_device,
            channels=CHANNELS,
            samplerate=RATE,
            blocksize=CHUNK_SIZE,
            callback=self.audio_callback,
            latency='low'
        )
        
        self.create_Menu()
        self.stream.start()


    def create_Menu(self):
        for i in range(MENU_ITEMS):
            self.menu.append(
                pyglet.shapes.Rectangle(
                    x= win.width/2 - 60,
                    y= i * (win.height / MENU_ITEMS),
                    height= win.height/MENU_ITEMS - 20,
                    width=120,
                    batch=self.batch,
                    color=(255,255,255) if i != self.selected_Index else (0,255,0)
                )
            )

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.processVoiceInput(indata)

    def processVoiceInput(self,indata):
        data = indata[:, 0]

        fft = np.fft.rfft(data * np.hanning(len(data)), n=len(data))
        main_frequencies = np.fft.rfftfreq(data.size, 1. / RATE)

        amps = np.abs(fft)
        max_Ampl_Index = np.argmax(amps[1:]) + 1

        if amps[max_Ampl_Index] < 1: # since whistleing is very dominant the amplitudes are pretty high, allowing to just ignore any noise with too little power (else could be calculated by the median of all peaks?)
            return
        print(amps[max_Ampl_Index])

        main_freq = main_frequencies[max_Ampl_Index]
        print(main_freq)
        if main_freq < 600: #stopped whistleing (whistleing was often in the 900-1400Hz range and very dominant)
            self.moveMent_Threshold = 0
            return
        
        if main_freq > self.last_Freq:
            print("Going up")
            self.moveMent_Threshold += 1
        else:
            print("Going Down")
            self.moveMent_Threshold -= 1

        self.last_Freq = main_freq
        lastIndex = self.selected_Index

        if self.moveMent_Threshold > DETECTION_THRESHOLD:
            self.selected_Index += 1
            print("Moving index up")
            self.moveMent_Threshold = DETECTION_THRESHOLD/5 #so continous whistleing speeds up movement (like holding down a key) else just reset to 0
        elif self.moveMent_Threshold < -DETECTION_THRESHOLD:
            self.selected_Index -= 1
            print("Moving index down")
            self.moveMent_Threshold = -DETECTION_THRESHOLD/5
        
        if(self.selected_Index == lastIndex): 
            return         
                
        direction = KeyDirection.KEY_DOWN if self.selected_Index < lastIndex else KeyDirection.KEY_UP
        self.translate_ToKey_Event(direction)
        self.move_Test_Pyglet()
    
    def move_Test_Pyglet(self):
        self.selected_Index = max(0, min(self.selected_Index, MENU_ITEMS-1))
        for i, menuItem in enumerate(self.menu):
            menuItem.color = (0,255,0) if i == self.selected_Index else (255,255,255)
        
    def translate_ToKey_Event(self,direction):
        if direction == KeyDirection.KEY_UP:
            print("UP")
            self.keyboard_Controller.press(key=pynput.keyboard.Key.up)
        elif direction == KeyDirection.KEY_DOWN:
            print("DOWN")
            self.keyboard_Controller.press(key=pynput.keyboard.Key.down)

    def on_draw(self):
        win.clear()
        self.batch.draw()

whistleInput = WhistleInput()

@win.event
def on_draw():
    whistleInput.on_draw()

@win.event
def on_key_press(symbol, modifiers):
        if symbol == pyglet.window.key.Q:
            os._exit(0)

@win.event
def on_close():
    whistleInput.stream.close()
    pyglet.app.exit()
    os._exit(0)


pyglet.app.run()