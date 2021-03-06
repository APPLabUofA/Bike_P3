import time
import os

###create a dummy display for pygame###
os.environ['SDL_VIDEODRIVER'] = 'dummy'

import sys
from random import randint
from random import shuffle
from datetime import datetime
import numpy as np
import pandas as pd
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

### setup pin for Camera Sync LED
GPIO.setup(18,GPIO.OUT)

###setup pin for push button###
pin = 26
GPIO.setup(pin,GPIO.IN,pull_up_down=GPIO.PUD_UP)

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

def GoPro_LED_Flash(flash_num):
    for flash in range(flash_num):
        GPIO.output(18,GPIO.HIGH)
        GPIO.output(pi2trig(9),1)
        time.sleep(0.1)
        GPIO.output(pi2trig(255),0)
        time.sleep(0.1)
        
###setup variables to record times###
vid_time  = []
trig_time   = []
trig_type = []
delay_length  = []
resp_time = []

###set triggers to 0###
GPIO.output(pi2trig(255),0)

###define the number of trials, and tones per trial###
trials = 250
low_rate = 0.8
high_rate = 0.2
low_tone = np.zeros(int(trials*low_rate))
high_tone = np.ones(int(trials*high_rate))
low_tone_list = low_tone.tolist()
high_tone_list = high_tone.tolist()
tones = low_tone_list + high_tone_list
shuffle(tones)

###wait for button press to start experiment###
pygame.mixer.music.load('/home/pi/Experiments/Sounds/ready.wav')
timestamp = local_clock()
outlet.push_sample([7], timestamp)
GPIO.output(pi2trig(7),1)
pygame.mixer.music.play()
while pygame.mixer.music.get_busy() == True:
    continue
time.sleep(1)
GPIO.output(pi2trig(255),0)
GPIO.wait_for_edge(26,GPIO.RISING)
time.sleep(1)
GPIO.wait_for_edge(26,GPIO.RISING)
time.sleep(1)
GPIO.wait_for_edge(26,GPIO.RISING)

vid_start = time.time()
timestamp = local_clock()
outlet.push_sample([5], timestamp)
GPIO.output(pi2trig(5),1)
time.sleep(0.5)
GPIO.output(pi2trig(255),0)
time.sleep(0.5)


GoPro_LED_Flash(10)
for i_tone in range(len(tones)):
    ###wait for a random amount of time between tones###
    delay = ((randint(0,500))*0.001)+1.49
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
    GPIO.output(pi2trig(int(tones[i_tone])+1),1)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy() == True:
        continue
    ###wait for a random amount of time and set the trigger back to zero###
    GPIO.output(pi2trig(255),0)
    ###now try and get a response###
    start_resp = time.time()
    edge_detect = GPIO.wait_for_edge(pin,GPIO.RISING, timeout = int(delay * 1000))
    if edge_detect is not None:  
        resp = time.time() - start_resp
        resp_time.append(resp)
        GPIO.output(pi2trig(int(tones[i_tone])+3),1)
        time.sleep(delay - resp)
    else:
        resp_time.append(0)
    time.sleep(0.005)
    GPIO.output(pi2trig(255),0)
    time.sleep(0.005)
    
GoPro_LED_Flash(10)
###show the end screen###
timestamp = local_clock()
outlet.push_sample([6], timestamp)
GPIO.output(pi2trig(6),1)
time.sleep(0.5)
GPIO.output(pi2trig(255),0)
time.sleep(0.5)

###save times###
while os.path.isfile("/home/pi/research_experiments/Experiments/" + exp_loc + "/Data/" + device + "/Trial_Information/" + partnum + "_" + filename + ".csv") == True:
    if int(partnum) >=10:
        partnum = "0" + str(int(partnum) + 1)
    else:
        partnum = "00" + str(int(partnum) + 1)

filename_part = ("/home/pi/research_experiments/Experiments/" + exp_loc + "/Data/" + device + "/Trial_Information/" + partnum + "_" + filename + ".csv")

the_list = [date, trig_type,trig_time,delay_length,resp_time]
df_list = pd.DataFrame({i:pd.Series(value) for i, value in enumerate(the_list)})
df_list.columns = ['Date','Trigger_Type','Trigger_Onset_Time','Trial_Delay','Response_Time']
df_list.to_csv(filename_part)

pygame.mixer.music.load('/home/pi/Experiments/Sounds/shut_down.wav')
timestamp = local_clock()
outlet.push_sample([8], timestamp)
GPIO.output(pi2trig(8),1)
pygame.mixer.music.play()
while pygame.mixer.music.get_busy() == True:
    continue

GPIO.output(pi2trig(255),0)
pygame.display.quit()
pygame.quit()
GPIO.cleanup()

if os.path.isfile("/home/pi/research_experiments/Stop_EEG2.csv") == True:   
    time.sleep(5)
    os.remove("/home/pi/research_experiments/Stop_EEG2.csv")
    time.sleep(5)
    os.remove("/home/pi/research_experiments/Stop_EEG1.csv")
