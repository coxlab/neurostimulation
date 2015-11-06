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

# animal = fname.split('_')[0]
# date = fname.split('_')[1]
# tstamp = fname.split('_')[2]

session_times = sorted(set([f.split('_')[1]+'_'+f.split('_')[2] for f in files]), reverse=True)
# curr_session = [f for f in files if session_times[0] in f]
for s in session_times:
    curr_session = [f for f in files if s in f]
    for fname in curr_session:
        f = open(os.path.join(datadir, fname), 'rb')
        evs = []
        if 'params' in fname:
            params = pkl.load(f)
        else:
            while 1:
                try:
                    evs.append(pkl.load(f))
                except EOFError:
                    break

    fname = curr_session[0]

    animal = fname.split('_')[0]
    date = fname.split('_')[1]
    tstamp = fname.split('_')[2]


    sensor_keys = set([i.keys()[0] for i in evs])
    events = dict()
    for key in sensor_keys:
        events[key] = [i[key] for i in evs if key in i.keys()]



    # trigger_evs = events['output'] # trigger events
    # sensor_evs = evs['sensor'] # sensor events

    n_triggers_detected = len([t['time'] for t in events['trigger'] if t['index']==params['ext_trigger'] and t['value']])
    n_sensors_detected = len([t['time'] for t in events['sensor'] if t['index']==params['target_port_channel'] and t['value'] > params['lick_threshold']])

    target_counts = max([i[1] for i in events['counts'][0]['n_targets']])           # this counts EACH lick
    # distractor_counts = max([i[1] for i in events['counts'][0]['n_distractors']])    # " "
    # both_counts = max([i[1] for i in params['counts'][0]['n_both']])


    # if not len(n_sensors_detected) == len(n_triggers_detected):
    #     print "N target licks and N triggers do not match!"
    #     print "N target licks: %i, N triggers %i." % (n_target_licks, n_triggers_detected)

    target_vals = [(i['time'], i['value']) for i in events['sensor'] if i['index']==params['target_port_channel']]
    # distractor_vals = [(i['time'], i['value']) for i in events['sensor'] if i['index']==params['distractor_port_channel']]

    trigger_times = [i['time'] for i in events['trigger'] if i['index']==params['ext_trigger'] and i['value'] ]


    # time.localtime(min(trigger_times))
    strt_secs  = params['start_time'] #int(sevs[0]['time'].split('_')[1][0:4])
    end_secs = params['end_time'] #int(curr_session[0].split('_')[2][0:4])

    fmt = '%Y%m%d_%H%M%S'
    t_start = time.strftime(fmt, time.localtime(strt_secs))
    t_end = time.strftime(fmt, time.localtime(end_secs))

    # taxis = np.linspace(strt, end, num=len(target_vals), endpoint=True)
    # # daxis = np.linspace(strt, end, num=len(distractor_vals), endpoint=True)

    # plt.plot(taxis, [i[1] for i in target_vals], 'r*', label='target')
    # # plt.plot(daxis, [i[1] for i in distractor_vals], 'go', label='distractor')

    fig = plt.figure()

    plt.plot([i[0] for i in target_vals], [i[1] for i in target_vals], 'co', markersize = 3, label='lick')
    plt.plot(trigger_times, np.ones(len(trigger_times))*1000, 'r|', markersize=30, markeredgewidth=2, alpha=0.5, label='trigger')

    plt.xlabel('time (ms)')
    plt.ylabel('sensor value')
    plt.title('time spent licking')
    plt.legend()
    plt.show()

    imname = animal + '_' + date + '_' + tstamp + '.png'
    basedir = os.path.split(os.path.split(datadir)[0])[0]
    figdir = os.path.join(basedir, 'figures')
    if not os.path.exists(figdir):
        os.mkdir(figdir)
    fig.savefig(figdir + '/' +  imname)
    print figdir + '/' + imname
