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
			params = pkl.load(f)
		else:
			evs =pkl.load(f)

trigger_evs = evs['output'] # trigger events
sensor_evs = evs['sensor'] # sensor events

n_triggers_detected = len([t['time'] for t in trigger_evs if t['index']==params['ext_trigger'] and t['value']])
n_target_licks = max([i[1] for i in params['counters']['n_targets']])
n_distractor_licks = max([i[1] for i in params['counters']['n_distractors']])
n_licking_both = max([i[1] for i in params['counters']['n_both']])


if not len(n_target_licks) == len(n_triggers_detected):
	print "N target licks and N rewarded triggers do not match!"
	print "N target licks: %i, N triggers %i." % (n_target_licks, n_triggers_detected)

target_vals = [(i['time'], i['value']) for i in sensor_evs if i['index']==params['target_port_channel']]
distractor_vals = [(i['time'], i['value']) for i in sensor_evs if i['index']==params['distractor_port_channel']]

trigger_times = [i['time'] for i in trigger_evs if i['index']==params['ext_trigger'] and i['value'] ]

# plt.plot([i[0] for i in target_vals], [i[1] for i in target_vals], 'r*', label='target')
# plt.plot([i[0] for i in distractor_vals], [i[1] for i in distractor_vals], 'go', label='distractor')

strt  = params['start_time'] #int(sevs[0]['time'].split('_')[1][0:4])
end = params['end_time'] #int(curr_session[0].split('_')[2][0:4])

taxis = range((end-strt)+1)
# rel_targ_times = [(1-(i[0]/end))*len(taxis) for i in target_vals]
y1 = np.where(i[0])

[np.where(taxis == min(taxis, key=lambda x: abs(float(x) - i[0]))) for i in target_vals]


plt.plot(np.linspace(strt, end, len(sevs), endpoint=True), [i[1] for i in target_vals], 'r*', label='target')
plt.plot([i[0] for i in distractor_vals], [i[1] for i in distractor_vals], 'go', label='distractor')
plt.xlabel('time (ms)')
plt.ylabel('sensor value')
plt.title('time spent licking each port')
plt.legend()
plt.show()