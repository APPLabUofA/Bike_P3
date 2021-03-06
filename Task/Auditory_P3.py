import time
import os

###create a dummy display for pygame###
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import sys
from random import randint
from random import shuffle
import datetime
import numpy
import pygame
import RPi.GPIO as GPIO
from pylsl import StreamInfo, StreamOutlet, local_clock

###variables for filenames and save locations###
partnum = '001'
device = 'Amp'
filename = 'Auditory_P3_Bike'
exp_loc = 'Auditory_P3_Bike'
date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

###create our stream variables###
info = StreamInfo('Markers', 'Markers', 1, 0, 'int32', 'myuidw43536')

###next make an outlet to record the streamed data###
outlet = StreamOutlet(info)

###initialise pygame###
GPIO.setmode(GPIO.BCM)
pygame.mixer.pre_init(44100,-16,2,1024)
pygame.init()
pygame.display.set_mode((1,1))
pygame.mixer.init()

###create variables for our sounds###
standard = '/home/pi/research_experiments/Experiments/Stimuli/Sounds/Auditory_Oddball/low_tone.wav'
target = '/home/pi/research_experiments/Experiments/Stimuli/Sounds/Auditory_Oddball/high_tone.wav'

###setup pins for triggers###
GPIO.setup([4,17,27,22,5,6,13,19],GPIO.OUT)

###Setup our function to send triggers###
###trig_type is either 's' or 'r'###
###trig_num must be between 1-15###
def pi2trig(trig_num):
    
    pi_pins = [4,17,27,22,5,6,13,19]
    
    bin_num = list(reversed(bin(trig_num)[2:]))
    
    while len(bin_num) < len(pi_pins):
        bin_num.insert(len(bin_num)+1,str(0))
    
    trig_pins = []
    
    trig_pos = 0
    
    for i_trig in range(len(pi_pins)):
        if bin_num[i_trig] == '1':
            trig_pins.insert(trig_pos,pi_pins[i_trig])
            trig_pos = trig_pos + 1
    
    return trig_pins

###setup variables to record times###
vid_time  = []
trig_time   = []
trig_type = []
delay_length  = []

###set triggers to 0###
GPIO.output(pi2trig(255),0)

###define the number of trials, and tones per trial###
trials = 20
low_rate = 0.8
high_rate = 0.2
low_tone = numpy.zeros(int(trials*low_rate))
high_tone = numpy.ones(int(trials*high_rate))
low_tone_list = low_tone.tolist()
high_tone_list = high_tone.tolist()
tones = low_tone_list + high_tone_list
shuffle(tones)

###wait to start experiment###
key_pressed = 0
pygame.event.clear()
while key_pressed == 0:
    event = pygame.event.wait()
    if event.type == pygame.QUIT:
        pygame.quit()
        sys.exit()
    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_SPACE:
            key_pressed = 1

vid_start = time.time()
timestamp = local_clock()
outlet.push_sample([3], timestamp)
GPIO.output(pi2trig(3),1)
time.sleep(1)
GPIO.output(pi2trig(3),0)

for i_tone in range(len(tones)):
    ###wait for a random amount of time between tones###
    delay = ((randint(0,500))*0.001)+1.00
    delay_length.append(delay)
    if tones[i_tone] == 0:#low tone
        pygame.mixer.music.load(standard)
        trig_type.append(1)
    elif tones[i_tone] == 1:#high tone
        pygame.mixer.music.load(target)
        trig_type.append(2)
    ###playback tone and send trigger###
    trig_time.append(time.time() - vid_start)
    timestamp = local_clock()
    outlet.push_sample([1], timestamp)
    trig_time.append(time.time() - vid_start)
    GPIO.output(pi2trig(tones[i_tone]+1),1)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() == True:
        continue
    ###wait for a random amount of time and set the trigger back to zero###
    GPIO.output(pi2trig(255),0)
    time.sleep(delay)

###show the end screen###
timestamp = local_clock()
outlet.push_sample([4], timestamp)
GPIO.output(pi2trig(4),1)
time.sleep(0.5)
pygame.mouse.set_visible(0)
GPIO.output(pi2trig(4),0)

###save times###
while os.path.isfile("/home/pi/research_experiments/Experiments/" + exp_loc + "/Data/" + device + "/LSL_Trial_Information/" + partnum + "_" + filename + ".csv") == True:
    if int(partnum) >=10:
        partnum = "0" + str(int(partnum) + 1)
    else:
        partnum = "00" + str(int(partnum) + 1)

filename_part = ("/home/pi/research_experiments/Experiments/" + exp_loc + "/Data/" + device + "/LSL_Trial_Information/" + partnum + "_" + filename + ".csv")

the_list = [date, trig_type,trig_time,delay_length]
df_list = pd.DataFrame({i:pd.Series(value) for i, value in enumerate(the_list)})
df_list.columns = ['Date','Trigger_Type','Trigger_Onset_Time','Trial_Delay']
df_list.to_csv(filename_part)

pygame.display.quit()
pygame.quit()
GPIO.cleanup()

if os.path.isfile("/home/pi/research_experiments/Stop_EEG2.csv") == True:   
    time.sleep(5)
    os.remove("/home/pi/research_experiments/Stop_EEG2.csv")
    time.sleep(5)
    os.remove("/home/pi/research_experiments/Stop_EEG1.csv")
