import sounddevice as sd
import numpy as np
from mido import MidiFile
import mido
import time
import threading
import pyglet
import os

#Notes:
# - The Balance between fft steps and rate is pretty fickle, research suggested using yin or interpolation instead of fft, but in context of the lesson i wanted to use fft
# - I think my voice is too slow for the samples.. so its really hard to test the latency since i cant really "stop my voice" for such short time spans?
# - RATE, CHUNK_SIZE picked for balance between quality and latency
# - Tested if Hz-Values are plausible by comparing with Audacity Spektrogramm

#Citation:
# - gave "Le Chat"(Mistral) my audio_callback function with prompt: "Is this correct", see details in function

CHUNK_SIZE = 512
RATE = 11025
BUFFER_SIZE = 2048
CHANNELS = 1
WIN_HEIGHT = 1000
BAR_HEIGHT_ADJUSTMENT = WIN_HEIGHT/500 #multiplies the frequency for better display
win = pyglet.window.Window(1600, WIN_HEIGHT)

# The current generation of pattern works for short files (0-15sec depending on win.width). For longer samples the timeline should be stationary and the bars move instead
# but i like to see the history of voice-frequency the stationary view allows
#if i wanted TODO it:
# - make timeline stationaire at e.g. 1/4 of win.width
# - generate pattern with width for rectangle with value only dependend on duration e.g. (duration of note/midi duration)*4
# - in update move all bars and gui_voice_points to the left by dt
# - check x of the time_line to bars x/y

class KaraokeGame:
    def __init__(self):
        global win
        self.start = time.time()

        self.batch = pyglet.graphics.Batch()
        self.voice_Batch = pyglet.graphics.Batch()
        self.point_Counter = 0
        #bars of the midi file
        self.bars = []
        self.audio_time = 0

        self.player = pyglet.media.Player()

        self.cur_Freq = 0
        #the pure data-Points of captured voice
        self.raw_Voice_Points = []
        #the gui representation of the data-Points since one can't directly generate shapes in the audio thread
        self.gui_voice_Points = []
        
        self.score = 0
        self.finisehd = True
        #rolling window buffer for higher resolution
        self.buffer =  np.zeros(BUFFER_SIZE) #*4 = window with 75% overlap

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

        print(f"Choose your song:\n1: berge\n2: freude")
        choice = int(input("Select Song: "))

        if choice == 1:
            self.midi_File = MidiFile('karaoke_game/berge.mid')
            self.music = pyglet.media.load("karaoke_game/berge.mp3")
        else:
            self.midi_File = MidiFile('karaoke_game/freude.mid')
            self.music = pyglet.media.load("karaoke_game/freude.mp3")

        self.midi_list = list(self.midi_File)

        #calculating the length of 1 voice point so the whole length of the window is filled out at the end
        max_chunks = self.midi_File.length * RATE / CHUNK_SIZE
        self.voice_bar_width = win.width / max_chunks

        self.stream = sd.InputStream(
            device=self.input_device,
            channels=CHANNELS,
            samplerate=RATE,
            blocksize=CHUNK_SIZE,
            callback=self.audio_callback,
            latency='low'
        )

        self.generate_Elements()

        #bool to controll the start of countdown
        self.start_Count_Down = False
        self.count = 4

        pyglet.clock.schedule_interval(self.update, 1/20)
        pyglet.clock.schedule_interval(self.update_Count_Down, 1)

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        data = indata[:, 0]
        
        # lots of reading e.g. 
        # https://stackoverflow.com/questions/4082358/improving-frequency-resolution-of-fft-output-by-limiting-frequency-range, https://dsp.stackexchange.com/questions/3537/can-you-increase-frequency-resolution-of-fft-without-increasing-window-size, https://dsp.stackexchange.com/questions/58149/what-is-a-sliding-window
        # resulting in the following buffer with 75% overlap
        # Then gave "Le Chat"(Mistral) the audio_callback function and asked if the code is correct, which added the "...[1:]) + 1" saying 0Hz dc-component should be removed

        self.buffer[:-len(data)] = self.buffer[len(data):] # previous last 3/4 are now first 3/4
        self.buffer[-len(data):] = data #last 1/4 is new data

        fft = np.fft.rfft(self.buffer * np.hanning(len(self.buffer)))
        main_frequencies = np.fft.rfftfreq(self.buffer.size, 1. / RATE)
        amps = np.abs(fft)

        max_Ampl_Index = np.argmax(amps[1:]) + 1
        main_freq = main_frequencies[max_Ampl_Index]
        
        print(f"Frequency: {main_freq}")
        self.cur_Freq = main_freq 
        self.audio_time += frames / RATE
        self.add_Voice_Point(main_freq)

    def add_Voice_Point(self, main_freq): 
        if main_freq < 70 or main_freq > 1000:
            return     
        self.raw_Voice_Points.append((self.audio_time, main_freq))

    #Formulas from https://en.wikipedia.org/wiki/MIDI_tuning_standard 
    def note_To_Frequency(self, note):
        return 440 * 2**((note - 69) / 12)
    
    def frequency_To_Note(self, freq):
        return round(69 + 12 * np.log2(freq / 440))   

    def update(self, dt):
        if self.finisehd:
            return
        timeX = (self.audio_time / self.midi_File.length) * win.width

        self.time_Line.position = (timeX, 0)
        self.time_Line_Point.position = (timeX, self.cur_Freq* BAR_HEIGHT_ADJUSTMENT - 3)

        if timeX >= win.width:
            print("END")
            self.stream.stop()
            self.finisehd = True
            self.info_Label.text = f"Score: {self.score}\n Press \"S\" to restart"
            self.audio_time = 0
       
        while self.raw_Voice_Points:
            (atTime, freqe) = self.raw_Voice_Points.pop(0)

            #alternative: normalize by "rounding" to MIDI-Note and back to frequency to better fit with bars
            #yNote = self.frequency_To_Note(freqe)
            #y = self.note_To_Frequency(yNote) * 2
            
            #due to my singing-capablilities the tolerance for error is quite high +-30Hz
            color = (255, 0, 0, 120)
            height = 20
            x = (atTime / self.midi_File.length) * win.width
            y = freqe * BAR_HEIGHT_ADJUSTMENT - (height/2) #-half height so right frequency is in the middle and +-10 is added as tolerance

           
            for bar in self.bars:
                if x < bar.x + bar.width and x + self.voice_bar_width > bar.x:
                    self.note_text.text = f"Sang Note:       {self.frequency_To_Note(freqe)}\nNeeded Note: {self.frequency_To_Note(bar.y/BAR_HEIGHT_ADJUSTMENT-10)}-{self.frequency_To_Note(bar.y/BAR_HEIGHT_ADJUSTMENT+40+10)}"
                    if y < bar.y + bar.height and y + height > bar.y: # bar.y should be required freq - 20 and bar.y + bar.height required freq + 20 also +-10 from the height of the y of current freq
                        self.score += 10
                        color = (0, 255, 0)
                        y = bar.y #if hit fill out the bar
                        height=40 #if hit fill out the bar
                        break
                #alternate approach converting to midi note:
                #barNote = self.frequency_To_Note((bar.y+20)/BAR_HEIGHT_ADJUSTMENT)
                #if barNote-1 <= yNote <= barNote+1:
                #    self.score += 10
                #    color = (0, 255, 0)
                #    y = bar.y
                #    height=40
                #    break            

            self.gui_voice_Points.append(
                pyglet.shapes.RoundedRectangle(
                    x=x,
                    y=y,
                    height=height,
                    width=self.voice_bar_width,
                    color=color,
                    radius=3,
                    batch=self.voice_Batch
                )
            )

        self.score_Label.text = f"Score: {self.score}"

    def on_draw(self):
        win.clear()
        self.batch.draw()
        self.voice_Batch.draw()

    #Game-starting countdown
    def update_Count_Down(self, dt):
        if self.start_Count_Down:
            self.count -= 1
            self.info_Label.text = f"{self.count}"

            if self.count == 0:
                self.info_Label.text = ""
            
                self.player.volume = 0.3
                self.player.queue(self.music)

                self.finisehd = False
                
                timer = threading.Timer(self.midi_list[0].time, self.player.play) # when converting midi to mp3 with ffmpeg it skips the first time before the note_on
                timer.start()
                self.stream.start()

                self.start_Count_Down = False
                self.count = 4
    
    def generate_Pattern(self):
        music_duration = self.midi_File.length
        midi_time_counter = 0 #added up time of the midi
        on_notes = {} #HashMap with note as key and start_Time as value        

        for msg in self.midi_list:
            if not hasattr(msg, "note"): #last msg has no note
                continue

            midi_time_counter += msg.time

            if msg.type == "note_on" and msg.velocity > 0:
                on_notes[msg.note] = midi_time_counter #sets HashMap entry with note as key and the midiTime as value 
            elif msg.type == "note_off":
                if msg.note not in on_notes: #shouldn't be necessary as long as midi-format is correct (any on_note has a paired off_note)
                    continue
                note_Start_Time = on_notes[msg.note]
                note_duration = midi_time_counter - note_Start_Time #checks after what time (of the added together midiTime) the note got turned off
                freNote = self.note_To_Frequency(msg.note)

                self.bars.append(
                    pyglet.shapes.RoundedRectangle(
                        x=(note_Start_Time / music_duration * win.width),
                        y=freNote * BAR_HEIGHT_ADJUSTMENT - 20, #-20 ajustment for height
                        width=(note_duration / music_duration * win.width),
                        height=40,
                        color=(147, 215, 237),
                        radius=5,
                        batch=self.batch
                    )
                )
                del on_notes[msg.note]

    def generate_Elements(self):
        #red line representing current time
        self.time_Line = pyglet.shapes.Rectangle(
           x=0,
           y=0,
           height=win.height,
           width=2,
           color=(255, 0, 0),
           batch=self.batch
        )

        #red dot on the time_Line representing the current frequency
        self.time_Line_Point = pyglet.shapes.Circle(
            x=0,
            y=0,
            radius=6,
            color=(255, 0, 0),
            batch=self.batch
        )

        #current Note and the window of tolerance of the bar
        self.note_text = pyglet.text.Label(
            text="Sang Note: #\nNeeded Note: #",
            x=win.width-200,
            y=60,
            width=200,
            align="right",
            font_size=15,
            multiline=True,
            batch=self.batch
        )

        #80Hz line for visual support
        self.help_Line = pyglet.shapes.Line(
            y= 80*BAR_HEIGHT_ADJUSTMENT,
            y2= 80*BAR_HEIGHT_ADJUSTMENT,
            x=0,
            x2=win.width,
            color=(255,255,255,80),
            batch=self.batch
        )

        #label of help_Line
        self.help_Line_Text = pyglet.text.Label(
            "80Hz",
            y=80*BAR_HEIGHT_ADJUSTMENT - 5,
            x=0,
            batch=self.batch
        )
    
        #Score label
        self.score_Label = pyglet.text.Label(
            text="Score: 0",
            x=10,
            y=10,
            font_size=30,
            batch=self.batch
        )

        #Re/Start-Info
        self.info_Label = pyglet.text.Label(
            text="Press \"S\" to start\nPress \"Q\" to close",
            width=win.width,
            height=win.height,
            anchor_y="bottom",
            align="center",
            font_size=60,
            multiline=True,
            batch=self.batch
        )

        #generates the bars fitting the midi
        self.generate_Pattern()

    def startGame(self):
        if not self.finisehd:
            return 
        self.score = 0
        self.score_Label.text = f"Score: {self.score}"
        self.gui_voice_Points.clear()
        self.start_Count_Down = True

game = KaraokeGame()

@win.event
def on_draw():
    game.on_draw()

@win.event
def on_key_press(symbol, modifiers):
        if symbol == pyglet.window.key.S:
            game.startGame()
        if symbol == pyglet.window.key.Q:
            os._exit(0)

@win.event
def on_close():
    game.stream.close()
    pyglet.app.exit()
    os._exit(0)

pyglet.app.run()