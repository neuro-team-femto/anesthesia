# coding=utf-8
import sys
import os
import glob
import csv
# import codecs
import datetime
import random
from psychopy import prefs
prefs.general['audioLib'] = ['pyo']
from psychopy import visual,event,core,gui
from fractions import Fraction
import pyaudio
import wave
import scipy.io.wavfile as wav
import numpy as np
from math import ceil, floor
import shutil
import pyxid2

def generate_trial_files(condition = 'music', subject_number=1, n_blocks=3, n_stims=400, n_stims_total=1200, deviant_proportion=0.2, initial_standards=10, minimum_standard = 1):
# generates n_block trial files per subject
# each block contains n_stim trials, randomized from folder which name is inferred from subject_number
# returns an array of n_block file names

    condition_folder = PARAMS[condition]['folder']

    # glob all deviants and all standards files in stim folder
    stim_folder = root_path+'/sounds/%s'%(condition_folder)

    deviant_files = ['sounds/%s/'%(condition_folder)+os.path.basename(x) for x in glob.glob(stim_folder+'/*_rough.wav')]
    n_deviants = len(deviant_files) 
    print('deviants:'+ str(deviant_files))

    standard_files = ['sounds/%s/'%(condition_folder)+os.path.basename(x) for x in glob.glob(stim_folder+'/*_neutral.wav')]
    n_standards = len(standard_files) 
    print('standards:'+str(standard_files))

    # generate list of deviants containing of n_total_stims * deviant_proportion stims
    deviant_file_list = np.random.choice(deviant_files, floor(n_stims_total*deviant_proportion))
    print('deviant list:'+str(deviant_file_list))
    
    # generate list of standards of same size as deviant_list
    standard_file_list = np.random.choice(standard_files, len(deviant_file_list))
    print('standard list:'+str(standard_file_list))
    
    # generate list of trials, with the constraint that each deviant is preceded by at least one standard
    stim_list = [ [std,dev] for std,dev in zip(standard_file_list,deviant_file_list) ] 
    print('pairs:'+str(stim_list))
   
    # add the rest of standards (with the exception of the first initial_standards, to be added later)
    n_trials_so_far = len([trial for trial_pair in stim_list for trial in trial_pair])
    if (n_stims_total > n_trials_so_far + initial_standards): 
        stim_list += [ [std] for std in np.random.choice(standard_file_list, n_stims_total - n_trials_so_far - initial_standards) ] 
    print('w/ end:'+str(stim_list))

    # shuffle
    random.shuffle(stim_list)
    
    # add beginning initial_standards
    stim_list = [ [std] for std in np.random.choice(standard_file_list, initial_standards) ] + stim_list
    print('w/begin:'+str(stim_list))

    # flatten
    stim_list = [trial for trial_pair in stim_list for trial in trial_pair]
    print('flatten:'+str(stim_list))
    
    # write trials by blocks of n_stims
    trial_files = []
    for block,block_num in blockify(stim_list, n_stims): 
        trial_file = root_path+'/trials/%s/trials_subj%d'%(condition_folder,subject_number) + '_condition_' +condition + '_block' + str(block_num+1) + '_' + date.strftime('%y%m%d_%H.%M')+'.csv'
        print('generate trial file '+trial_file)
        trial_files.append(trial_file)
        with open(trial_file, 'w+', newline='') as file :
            # write header
            writer = csv.writer(file)
            writer.writerow(['Stimulus'])
            # write trials of the block
            for item in block: 
                writer.writerow([item])
    return trial_files
        
def blockify(x,n_stims):
    # generator to cut a signal into non-overlapping frames
    # returns all complete frames, but a last frame with any trailing samples
    for i in range(len(x)//n_stims):
        start = n_stims*i
        end=n_stims*(i+1)
        yield (x[start:end],i)
    if (end < len(x)): 
        yield (x[end:len(x)],i+1)  
    
def read_trials(trial_file): 
# read all trials in a block of trial, stored as a CSV trial file
    with open(trial_file, 'r') as fid:
        reader = csv.reader(fid)
        trials = list(reader)
    trials = [''.join(trial) for trial in trials]
    return trials[1:] #trim header

def generate_result_file(condition, subject_number):
    
    condition_folder = PARAMS[condition]['folder']

    result_file = root_path+'results/%s/results_subj%d'%(condition_folder,subject_number)+ '_condition_' +condition +'_'+date.strftime('%y%m%d_%H.%M')+'.csv'        
    result_headers = ['subject_number','sex','age','handedness','date','condition','block_number','trial_number','sound_file','stim_type','stim_marker_code']
    with open(result_file, 'w+') as file:
        writer = csv.writer(file)
        writer.writerow(result_headers)
    return result_file

def show_text_and_wait(file_name = None, message = None):
    event.clearEvents()
    if message is None:
        #with codecs.open (file_name, 'r', 'utf-8') as file :
        with open (file_name, 'r') as file :
            message = file.read()
    text_object = visual.TextStim(win, text = message, color = 'white')
    text_object.height = 0.1
    text_object.draw()
    win.flip()
    while True :
        if len(event.getKeys()) > 0: 
            core.wait(0.2)
            break
        event.clearEvents()
        core.wait(0.2)
        text_object.draw()
        win.flip()
        
def show_fixation_cross(file_name = None, message = '+', color = 'deepskyblue'):
    event.clearEvents()
    text_object = visual.TextStim(win, text = message, color = color)
    text_object.height = 0.2
    text_object.draw()
    win.flip()

def play_sound(sound):
    #play sound
    audio = pyaudio.PyAudio()
#        sr,wave = wav.read(fileName)
    wf = wave.open(sound)
    def play_audio_callback(in_data, frame_count, time_info,status):
        data = wf.readframes(frame_count)
        return (data, pyaudio.paContinue)
    #define data stream for playing audio and start it
    output_stream = audio.open(format   = audio.get_format_from_width(wf.getsampwidth())
                         , channels     = wf.getnchannels()
                         , rate         = wf.getframerate()
                         , output       = True
                         , stream_callback = play_audio_callback
                    )
    output_stream.start_stream()
    while output_stream.is_active():
        core.wait(0.01)
        continue 


###########################################################################################
###      DEFINE HOW MANY TRIALS IN HOW MANY BLOCKS 
###      
###########################################################################################

root_path = './' 
N_STIMS_TOTAL = 25 # total nb of stimuli (dev + std)
DEVIANT_PROPORTION = 0.2
N_BLOCKS = 1
INITIAL_STANDARDS = 5
ISI = .6 # in sec
JITTER = .05 # in sec.

VOICE_PARAMS = {'condition':'voice',
               'fixation_cross_color':'deepskyblue',
               'folder':'voice'}

MUSIC_PARAMS = {'condition':'music',
               'fixation_cross_color':'green',
               'folder':'music'}

PARAMS = {'voice':VOICE_PARAMS,
            'music':MUSIC_PARAMS}

###########################################################################################


# get participant nb, age, sex 
subject_info = {u'number':1, u'age':20, u'sex': u'f/m', u'handedness':'right', u'condition': u'voice/music'}
dlg = gui.DlgFromDict(subject_info, title=u'Own-name')
if dlg.OK:
    subject_number = subject_info[u'number']
    subject_age = subject_info[u'age']
    subject_sex = subject_info[u'sex']  
    subject_handedness = subject_info[u'handedness'] 
    condition = subject_info[u'condition']
else:
    core.quit() #the user hit cancel so exit
date = datetime.datetime.now()
time = core.Clock()

# retrieve condition parameters
if not condition in PARAMS:
    raise AssertionError("Can't find condition: "+condition)
params = PARAMS[condition]

# create psychopy black window where to show instructions
win = visual.Window(np.array([1920,1080]),fullscr=False,color='black', units='norm')

# generate data files
result_file = generate_result_file(condition, subject_number) # renvoie 1 filename en csv
n_stims = round(N_STIMS_TOTAL/N_BLOCKS) # nb trials per block
trial_files = generate_trial_files(condition=condition,
                                                subject_number=subject_number,
                                                n_blocks=N_BLOCKS,
                                                n_stims=round(N_STIMS_TOTAL/N_BLOCKS),
                                                n_stims_total=N_STIMS_TOTAL,
                                                deviant_proportion=DEVIANT_PROPORTION,
                                                initial_standards=INITIAL_STANDARDS) 

print('trials:'+str(trial_files))

# start_experiment 
show_text_and_wait(file_name=root_path+'intro.txt')
trial_count = 0
n_blocks = len(trial_files)
for block_count, trial_file in enumerate(trial_files):

    show_fixation_cross(message='+', color=params['fixation_cross_color'])
    
    block_trials = read_trials(trial_file)
        
    for trial in block_trials:
        row = [subject_number, subject_age, subject_sex, subject_handedness, date, condition, block_count+1, trial_count+1]
        sound = root_path+trial   
        
        # find stim stype         
        if 'neutral' in trial:
            stim_type = 'standard'
        else:
            stim_type = 'deviant'        
        
        # play sound
        print('file: %s:'%sound)  
        play_sound(sound)
        
        # wait ISI
        core.wait(ISI+random.uniform(-JITTER, JITTER))            
        
        # log trial in result_file
        with open(result_file, 'a') as file:
            writer = csv.writer(file,lineterminator='\n')
            result = row + [trial,stim_type]
            writer.writerow(result)
            
        trial_count += 1
        
    # pause at the end of subsequent blocks 
    if block_count < n_blocks-1: 
        show_text_and_wait(message = "Vous avez fait "+str(Fraction(block_count+1, n_blocks))+ " de l'experience. \n Nous vous proposons de faire une pause. \n\n (Veuillez attendre l'experimentateur pour reprendre l'experience).")      
        
        
#End of experiment
show_text_and_wait(root_path+'end.txt')

# Close Python
win.close()
core.quit()
sys.exit()
