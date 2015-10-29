#! /usr/env/python

'''
# 
# Script to run quick and dirty analysis on licking bias w/ neurostim.
# 
# data saved with phidget_sensor.py (using "naked" and no program)
#
# run "python check_licks.py"
#
# Three modes 
# a.  "naked" (PulsePal + Phidget only - no mworks) 
# b.  "mworks"  (Listen to MWorks to control PulsePal - no phidget)
# c.  "trigger" (Use external trigger, e.g,. intan, to trigger PulsePal)
# 
# x.  program PulsePal or not (if not, will run last used settings)
#
'''

# Basic imports
import os
from ctypes import *
import sys
import random
import numpy as np
import time
import optparse
from datetime import datetime
import cPickle as pkl
import pymworks
import matplotlib.pyplot as plt

datadir = sys.argv[1] #'/home/juliana/Documents/dtest/'
files = os.listdir(datadir)
files = sorted([f for f in files if os.path.splitext(f)[1] == '.pkl'], reverse=True) # most recent

session_times = sorted(set([f.split('_')[1]+'_'+f.split('_')[2] for f in files]), reverse=True)
curr_session = [f for f in files if session_times[0] in f]
for fname in curr_session:
	with open(os.path.join(datadir, fname), 'rb') as f:
		if 'params' in fname:
			data = pkl.load(f)
		else:
			evs =pkl.load(f)

tevs = evs['output'] # trigger events
sevs = evs['sensor'] # sensor events

n_triggers_detected = [t['time'] for t in tevs if t['index']==data['ext_trigger'] and t['value']]
if not len(data['n_targets']) == len(n_triggers_detected):
	print "N target licks and N rewarded triggers do not match!"

target_vals = [(int(i['time'].split('_')[1]), i['value']) for i in sevs if i['index']==data['target_port_channel']]
distractor_vals = [(int(i['time'].split('_')[1]), i['value']) for i in sevs if i['index']==data['distractor_port_channel']]

plt.plot([i[0] for i in target_vals], [i[1] for i in target_vals], 'r*--', label='target')
plt.plot([i[0] for i in distractor_vals], [i[1] for i in distractor_vals], 'go--', label='distractor')
plt.xlabel('time (ms)')
plt.ylabel('sensor value')
plt.title('time spent licking each port')
plt.legend()
plt.show()