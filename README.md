[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/B3oR_XLF)

# Starting a Script/Game:

## Requirements
- Python3

## Initializing and starting Virtual Enviroment

### For Windows
Open The Root-Directory (Assignment-02-...) in a Terminal and create + activate the virtual enviroment with:

````
py -m venv venv
venv\Scripts\activate
````
(venv) should now be displayed before your new CommandLine in the Terminal

Next install the requirements:
````
pip install -r requirements.txt
````

Then open the desired file,\
For [Karaoke](#karaoke):
````
py karaoke_game\karaoke.py
````
For [Whistle-Input](#whistle-input):
````
py whistle_input\whistle-input.py
````
### For Mac
The Steps are the same, but the concrete commands different:
````
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 karaoke_game/karaoke.py
python3 whistle_input/whistle-input.py
````

### Closing
Just type:
````
deactivate
````

# Karaoke
On Start your connected sound-devices will show in the terminal.\
Select your sound-Device by typing the corresponding number in the terminal and press enter.\
Then select the title you want in the same way

- a window will show and you can press "S" to start a countdown before the title starts playing
- the red-line displays the current time and the point in it the current frequency of your voice
- match your frequency with the one of the song to gain points

# Whistle-Input
On Start select your sounddevice by typing the corresponding number in the terminal and press enter
- an example window with a stack of 6 Rectangles will open
- Whistleing with a decreasing pitch will move the red rectangle in the example menu "_down_" or with increasing picht "_up_"
- The same inputs will also trigger a _Arrow-Down_ / _Arrow-Up_ key-press, allowing you to navigate through whistleing

# Notes
- Testing was done with a headset
