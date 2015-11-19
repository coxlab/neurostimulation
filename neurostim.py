#! /usr/env/python

'''
# 
# Script to run from command line to control PulsePal & Phidgets.
# 
# run "python phidget_sensor.py"
#
# Three+x modes of operating:
# a.  "naked" [default] (PulsePal + Phidget only - no mworks) 
# b.  "mworks"  (Listen to MWorks to control PulsePal - no phidget)
# c.  "pulsepal" (Open and run pulsepal (programming, running, etc.)
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
import thread
import pyglet
import itertools

# ==============================================================================
# STIMULATION PARAMETERS: EDIT THESE TO CHANGE STIM PARAMS FOR A SESSION
# ==============================================================================
# Channel 1 is always smallest ('pre-reward') and triggered off of TRIG 2

pulse_width = np.array([0.1, 0.7, 0.7, 0.7])        # ms: phase1Duration = pulse_width/1000. (s)
pulse_voltage = np.array([2., 1., 1., 1.])          # V: phase1Voltage # 100uA/V
frequency = np.array([30., 100., 80., 60.])         # Hz: interPulseInterval in (s) = time bw pulses
phasic = np.array([2., 2., 2., 2.])                 # n phases (i.e, biphasic or monophasic)

train_duration = [[0.500]]                          # s: First set trigger2 train (train dur in seconds)
n_pulses_set = train_duration[0][0] * frequency[0]  # Calculate num pulses for given freq and dur

n_pulses = np.array([n_pulses_set, 8*3, 8*3, 8*3])  # s: Then, set num of pulses for reward manually for other channels

train_duration_calc = list(n_pulses[1:4] * (((pulse_width[1:4]/1000.) * phasic[1:4]) + 1./frequency[1:4]))
train_duration.append(train_duration_calc)          # s
train_duration = list(itertools.chain.from_iterable(train_duration))

# ==============================================================================
# ==============================================================================



# ==============================================================================
# RUNTIME OPTIONS: Run mode, channel programming, sound ON/OFF, save params, etc.
# ==============================================================================
parser = optparse.OptionParser()
parser.add_option('-m', '--mode', type='choice', action="store", dest="mode", default="naked", choices=['naked', 'mworks', 'pulsepal'])
parser.add_option('-P', '--program', action="store_true", dest="program", default=False, help="program pulse generator only (must be in 'pulsepal' mode)")
parser.add_option('-S', '--save', action="store_true", dest="save_data", default=False, help="save data")
parser.add_option('-O', '--output-path', action="store", dest="output_path", default="/tmp/data", help="data output path")
parser.add_option('-i', '--id', action="store", dest="animalID", default="test", help="subject ID")

parser.add_option('-C', '--channel', action="append", default=[],  dest="channel_nums", help="output channels for stimulation, e.g., '-c1'")
parser.add_option('-T', '--trigger2', action="store_true", default=False,  dest="alt_trigger", help="trigger with Trigger1 instead of 2")

parser.add_option('-t', '--thresh', action="store", dest="threshold", default="500", help="lick sensor threshold value")
parser.add_option('-l', '--lick-port', action="store", dest="lick_port", default="1", help="left (1) or right(2) lickport")

parser.add_option('-p', '--oneport', action="store_true", dest="one_port", default=False, help="one or two-port task?")
parser.add_option('-s', '--sound', action="store_true", dest="play_tones", default=False, help="play reward and/or punish tones (set feedback flag)?")
parser.add_option('-f', '--feedback', action="store_true", dest="give_feedback", default=False, help="play reward/punish tones, enforce timeouts?")
parser.add_option('-H', '--head', action="store_true", dest="sense_head", default=False, help="sense head or not?")



(options, args) = parser.parse_args()
mode = options.mode
program = options.program
if program:
    mode='pulsepal' # override incorrect mode setting
alt_trigger = options.alt_trigger

output_path = options.output_path
animalID = options.animalID
save = options.save_data

play_tones = options.play_tones
give_feedback = options.give_feedback
sense_head = options.sense_head
# ==============================================================================
# ==============================================================================



# ==============================================================================
# Experiment Parameters: Relevant experiment info (channels, triggers, etc.)
# ==============================================================================

# PulsePal info:
channel_nums = options.channel_nums             # which PulsePal channel for stim output
channel_nums = [int(i) for i in channel_nums]   # turn into INT for below
channels = np.zeros(4)
for i in channel_nums:                          # 0-indexify and turn ON specified channels
    channels[i-1] = 1
channels = [int(i) for i in channels]           # turn into ints for soft-triggering
print "Channel nums: ", channel_nums            # print which channels being used
print "Channel status: ", channels              # channels ON or OFF


# Phidget info:
threshold = float(options.threshold)            # value of Phidget sensor channel that counts as "licking"
lick_port = int(options.lick_port)              # reward for licking specified port (currently, just reward)
ext_trigger = 0                                 # D.O. channel on phidget (connect to Trigger Ch 1 on PulsePal)

one_port = options.one_port                     # otherwise, 2 (or 3) port
if one_port:
    port_names = ["CENTER"]
    target_port = 5                             # default so that Phidget Ch.5 is pump 01 (which is standard for single-port, too)
else:                                           # TWO ports (or 3?)
    port_names = ["LEFT", "RIGHT"]
    if lick_port==1:                            # lick-port num corresponds to Pump 01 or 02 (standard)
        target_port = 5                         # pump 01 = phidget ch 5 = LEFT PORT
        distractor_port = 7                     # pump 02 = phidget ch 7 = RIGHT PORT
        ignore_port = 2                         # the lick-port to ignore (distractor port is RIGHT port)
    else:                                      
        target_port = 7 # RIGHT PORT
        distractor_port = 5
        ignore_port = 1

# DO STUFF WITH HEAD SENSOR HERE:
head_channel = 4
head_threshold = 500

# Sound / Feedback info: # FIX THIS BECAUSE IT'S CONFUSING FOR SIGNALING JUST SUCCESS vs. PUNISH
if play_tones:
    success_tone = pyglet.media.load('./stimuli/sounds/NRsuccess.wav', streaming=False)
    fail_tone = pyglet.media.load('./stimuli/sounds/failure_DZ.wav', streaming=False)

timeout_time = 5
postreward_timeout_time = 3
# ==============================================================================
# ==============================================================================


# ==============================================================================
# SAVE STUFF:
# ==============================================================================
fmt = '%Y%m%d_%H%M%S%f'

if save:
    if not os.path.exists(output_path):
        os.mkdir(output_path)

    datestr = datetime.now().strftime(fmt)

    # Open write file for phidget IO events:
    fname = animalID + '_' + datestr + '_events.pkl'
    fn_evs = open(os.path.join(output_path, fname), 'wb')

    # Open write file for experiment parameters:    
    fname = animalID + '_' + datestr + '_params.pkl'
    fn_params = open(os.path.join(output_path, fname), 'wb')

    # Open write file for head sensing:    
    if sense_head:
        fname = animalID + '_' + datestr + '_head.pkl'
        fn_head = open(os.path.join(output_path, fname), 'wb')
# ==============================================================================
# ==============================================================================



# ==============================================================================
# MODE SPECIFIC ACTIONS:
# ==============================================================================

# ========== MWorks stuff ==========
if mode=='mworks':

    # Only need client call-backs (make sure .xml with server-side conduit is already running)
    # This mode does not use Phidgets or PulsePal, but rather triggers stimulation thru MW software

    sys.path.append('/Library/Application Support/MWorks/Scripting/Python')
    import mworks.conduit

    # def say_hello(mevt):
    #     g2g = []
    #     while not (1 in g2g):

    #         # print "called"
    #         if mevt.value:
    #             print "MWorks connection is ready!"
    #             g2g.append(1)
    #         else:
    #             # print "Waiting for MW...."
    #             g2g.append(0)

        # return g2g

    # # separate MW save directory?
    # mw_output_dir = '/tmp/mw_output'
    # d = os.path.dirname(mw_output_dir)
    # if not os.path.exists(d):
    #     os.mkdir(d)

    client = mworks.conduit.IPCClientConduit('server_conduit')
    client.initialize()

    # Check for listen:
    # g2g = []
    # while not (1 in g2g):
    # client.register_callback_for_name('hello_world', say_hello)

    # stop_flag = [0]
    # stim = 0
    # print "LET'S DO IT!!!"
        # print g2g



# ========== Phidget specific imports ==========
if mode == 'naked':
    from Phidgets.PhidgetException import *
    from Phidgets.Events.Events import *
    # from Phidgets.Devices.InterfaceKit import *
    from Phidgets.Devices import *
    from Phidgets.Phidget import PhidgetLogLevel
    from Phidgets.Manager import Manager

    sensor_events = []
    output_events = []


    # ========== Information Display Function ==========

    def displayDeviceInfo():
        print("|------------|----------------------------------|--------------|------------|")
        print("|- Attached -|-              Type              -|- Serial No. -|-  Version -|")
        print("|------------|----------------------------------|--------------|------------|")
        print("|- %8s -|- %30s -|- %10d -|- %8d -|" % (device.isAttached(), device.getDeviceName(), device.getSerialNum(), device.getDeviceVersion()))
        print("|------------|----------------------------------|--------------|------------|")
        print("Number of Digital Inputs: %i" % (device.getInputCount()))
        print("Number of Digital Outputs: %i" % (device.getOutputCount()))
        print("Number of Sensor Inputs: %i" % (device.getSensorCount()))

    # ========== Event Handling Functions ==========

    def interfaceKitAttached(e):
        attached = e.device
        print("InterfaceKit %i Attached!" % (attached.getSerialNum()))

    def interfaceKitDetached(e):
        detached = e.device
        print("InterfaceKit %i Detached!" % (detached.getSerialNum()))

    def interfaceKitError(e):
        try:
            source = e.device
            print("InterfaceKit %i: Phidget Error %i: %s" % (source.getSerialNum(), e.eCode, e.description))
        except PhidgetException as e:
            print("Phidget Exception %i: %s" % (e.code, e.details))

    # def interfaceKitInputChanged(e):
    #     source = e.device
    #     print("InterfaceKit %i: Input %i: %s" % (source.getSerialNum(), e.index, e.state))

    def interfaceKitSensorChanged(e):
        source = e.device
        if ((e.index==target_port) or (e.index==distractor_port)) and (e.value >=threshold):
            if save:
                pkl.dump({'sensor': {'index':e.index, 'value':e.value,'time':time.time()}}, fn_evs)
            else:
                print "LICK: %i, %i" % (e.index, e.value)

        if sense_head:
            if e.index==head_channel:
                if save:
                    pkl.dump({'sensor': {'index':e.index, 'value':e.value,'time':time.time()}}, fn_evs)
                else:
                    print "HEAD: %i, %i" % (e.index, e.value)

    def interfaceKitOutputChanged(e):
        source = e.device
        # print("InterfaceKit %i: Output %i: %s" % (source.getSerialNum(), e.index, e.state))
        if e.index==ext_trigger:
            # output_events.append({'index':e.index, 'value':e.state, 'time':time.time()})
            if save:
                pkl.dump({'trigger': {'index':e.index, 'value':e.state,'time':time.time()}}, fn_evs)
            else:
                print "TRIGGER: %i, %i" % (e.index, e.state)

        # print output_events

    # def detectSensorThreshold(e):
    #     source = e.device
    #     # threshold = source.getSensorChangeTrigger(e.index)
    #     threshold = 500 #source.getSensorValue(e.index)
    #     if e.value > threshold:
    #     #     print("Sensor %i: %i" % (e.index, e.value))
    #     # else:
    #         print "reached threshold!!! Sensor %i: %i" % (e.index, e.value)

    # =========== Python-specific Exception Handler ==========        
            
    def LocalErrorCatcher(event):
        print("Phidget Exception: " + str(e.code) + " - " + str(e.details) + ", Exiting...")
        exit(1)

    # ========= Connect to PHIDGET ==========   

    # Create InterfaceKit object:
    try:
        device = InterfaceKit.InterfaceKit() 
    except RuntimeError as e:
        print("Runtime Error " + e.details + ", Exiting...\n")
        exit(1)

    # Hook functions above into phidget object:
    try:
        #logging example, uncomment to generate a log file
        #interfaceKit.enableLogging(PhidgetLogLevel.PHIDGET_LOG_VERBOSE, "phidgetlog.log")
        
        device.setOnAttachHandler(interfaceKitAttached)
        device.setOnDetachHandler(interfaceKitDetached)
        device.setOnErrorhandler(interfaceKitError)
        # device.setOnInputChangeHandler(interfaceKitInputChanged)
        device.setOnOutputChangeHandler(interfaceKitOutputChanged)
        device.setOnSensorChangeHandler(interfaceKitSensorChanged)
        # device.setOnSensorChangeHandler(detectSensorThreshold)

    except PhidgetException as e:
        LocalErrorCatcher(e)

    # Open phidget:
    print("Opening phidget object....")

    try:
        device.openPhidget()
    except PhidgetException as e:
        LocalErrorCatcher(e)

    # Attach to the phidget:
    print("Waiting for attach....")

    try:
        device.waitForAttach(8000)
    except PhidgetException as e:
        print "first"
        print("Phidget Exception %i: %s" % (e.code, e.details))
        try:
            "closed it"
            device.closePhidget()
        except PhidgetException as e:
            print "next"
            print("Phidget Exception %i: %s" % (e.code, e.details))
            print("Exiting....")
            exit(1)
        print "getting out..."
        print("Exiting....")
        exit(1)
    else:
        displayDeviceInfo()


# ========= Pulse Pal stuff ==========   

def use_last_settings():
    print "Using last saved settings on PulsePal."
    print "Output channels: %s" % str(channels)
    print "Target port: %s (channel %i)" % (port_names[lick_port - 1], target_port)
    print "Distractor port: %s (channel %i)" % (port_names[ignore_port - 1], distractor_port)
    print "|------------|----------------|-------------|-----------|"
    print "|- N pulses -|- plulse width -|- frequency -|- voltage -|"
    print "|------------|----------------|-------------|-----------|"
    print "|-        %i -|-     %2.3f ms -|-  %2.2f Hz -|-  %2.2f V -|" % (n_pulses, pulse_width, frequency, pulse_voltage)

    print "Train duration: %f sec" % train_duration
    print "Biphasic pulses: %s" % str(phasic)
    print "Press Enter to CONTINUE..."
    chr = sys.stdin.read(1)

    print "Parameters accepted! Continuing... [Press ENTER to Quit]"


if mode=='pulsepal':
    print "Programming PulsePal..."

    # Do this stupid thing to get PulsePal.py imported...
    import imp
    scriptpath = '/Repositories/PulsePal/Python/PulsePal.py'
    sys.path.append(os.path.abspath(scriptpath))
    from os.path import expanduser
    home = expanduser("~")
    path_to_file = home + scriptpath
    imp.load_source('PulsePal', path_to_file)
    from PulsePal import PulsePalObject # Import PulsePalObject

    if program:

        print "PULSEPAL!"
        pulse_port = '/dev/ttyACM0' # port for PulsePal

        try:        
            # ========== Initialize PulsePal ==========

            pulse = PulsePalObject()                                # Create a new instance of a PulsePal object
            try:
                pulse.connect(pulse_port)                           # Connect to PulsePal on port COM4 (open port, handshake and receive firmware version)
            except OSError:
                pulse_port = '/dev/ttyACM1'                         # port for PulsePal
                pulse.connect(pulse_port)

            print(pulse.firmwareVersion)                            # Print firmware version to the console

            # ========== Set PulsePal Settings ==========

            print "Output channels: %s" % str(channels)
            print "Target port: %s (channel %i)" % (port_names[lick_port - 1], target_port)
            print "Distractor port: %s (channel %i)" % (port_names[ignore_port - 1], distractor_port)
            # print "|------------|----------------|-------------|-----------|"
            # print "|- N pulses -|- plulse width -|- frequency -|- voltage -|"
            # print "|------------|----------------|-------------|-----------|"
            # print "|-        %i -|-     %2.3f ms -|-  %2.2f Hz -|-  %2.2f V -|" % (n_pulses, pulse_width, frequency, pulse_voltage)

            pulse.linkTriggerChannel1[0:5] = [1]*5
            pulse.linkTriggerChannel2[0:5] = [1]*5
            for c in channel_nums:

                print "CHANNEL %i" % c
                print "|------------|----------------|-------------|-----------|"
                print "|- N pulses -|- plulse width -|- frequency -|- voltage -|"
                print "|------------|----------------|-------------|-----------|"
                print "|-        %i -|-     %2.3f ms -|-  %2.2f Hz -|-  %2.2f V -|" % (n_pulses[c-1], pulse_width[c-1], frequency[c-1], pulse_voltage[c-1])


                # print c
                pulse.isBiphasic[c] = 1                             # parameter arrays are 5 elements long. Use [1] for output channel 1. 
                pulse.customTrainID[c] = 0                          # set to 0 for parametric (non custom train 1 or 2)

                pulse.interPhaseInterval[c] = 0.                    # time between pos and neg pulse for biphasic # min seems to be 0.01s
                pulse.interPulseInterval[c] = 1./frequency[c-1]          # time between biphasic pulses
                pulse.phase1Voltage[c] = pulse_voltage[c-1]              # (set output channel x to use 7V pulses)
                pulse.phase2Voltage[c] = -1*pulse_voltage[c-1]           # (set output channel x to use 7V pulses)
                pulse.phase1Duration[c] = pulse_width[c-1]/1000.
                pulse.phase2Duration[c] = pulse_width[c-1]/1000.
                pulse.restingVoltage[c] = 0.

                pulse.pulseTrainDuration[c] = train_duration[c-1]        # train duration (sec)
                pulse.pulseTrainDelay[c] = 0.                       #(0s - 3600s, 0.0001s resolution, 0.00001s precision)

                pulse.burstDuration[c] = 0
                print c
                if alt_trigger and c==1:
                    pulse.linkTriggerChannel1[c] = 1
                    pulse.linkTriggerChannel2[c] = 0
                else:
                    pulse.linkTriggerChannel1[c] = 0
                    pulse.linkTriggerChannel2[c] = 1

                print "Train duration: %f sec" % train_duration[c-1]
                print "Biphasic pulses: %s" % str(pulse.isBiphasic)

            pulse.triggerMode[1] = 0                                # Trigger1 or Trigger 2: (0 = normal, 1 = toggle, 2 = pulse gated)
            pulse.triggerMode[2] = 0
            print "Link Trigg1: ", pulse.linkTriggerChannel1
            print "Link Trigg2: ", pulse.linkTriggerChannel2
            pulse.syncAllParams()                                   # This call is critical to update PulsePal object settings from last session...!

            # print "Train duration: %f sec" % train_duration[c-1]
            # print "Biphasic pulses: %s" % str(pulse.isBiphasic)
            print "Press Enter to CONTINUE..."
            chr = sys.stdin.read(1)

            print "Parameters accepted! Continuing... [Press ENTER to Quit]"
            pulse.setDisplay("Starting! :)", "STIM on CH %s" % str([i for i in channel_nums if i]))

        except NameError, e:
            print e
            print "If trying to reprogram PulsePal, mode must also be 'pulsepal' -- try again."
            exit(1)

    else:
        # print "Using last saved settings on PulsePal."
        # print "Output channels: %s" % str(channels)
        # print "Target port: %s (channel %i)" % (port_names[lick_port - 1], target_port)
        # print "Distractor port: %s (channel %i)" % (port_names[ignore_port - 1], distractor_port)
        # print "|------------|----------------|-------------|-----------|"
        # print "|- N pulses -|- plulse width -|- frequency -|- voltage -|"
        # print "|------------|----------------|-------------|-----------|"
        # print "|-        %i -|-     %2.3f ms -|-  %2.2f Hz -|-  %2.2f V -|" % (n_pulses, pulse_width, frequency, pulse_voltage)

        # print "Train duration: %f sec" % train_duration
        # print "Biphasic pulses: %s" % str(phasic)
        # print "Press Enter to CONTINUE..."
        # chr = sys.stdin.read(1)

        # print "Parameters accepted! Continuing... [Press ENTER to Quit]"
        use_last_settings()

else:
    # print "Using last saved settings on PulsePal."
    # print "Output channels: %s" % str(channels)
    # print "Target port: %s (channel %i)" % (port_names[lick_port - 1], target_port)
    # print "Distractor port: %s (channel %i)" % (port_names[ignore_port - 1], distractor_port)
    # print "|------------|----------------|-------------|-----------|"
    # print "|- N pulses -|- plulse width -|- frequency -|- voltage -|"
    # print "|------------|----------------|-------------|-----------|"
    # print "|-        %i -|-     %2.3f ms -|-  %2.2f Hz -|-  %2.2f V -|" % (n_pulses, pulse_width, frequency, pulse_voltage)

    # print "Train duration: %f sec" % train_duration
    # print "Biphasic pulses: %s" % str(phasic)
    # print "Press Enter to CONTINUE..."
    # chr = sys.stdin.read(1)
    
    # print "Parameters accepted! Continuing... [Press ENTER to Quit]"
    use_last_settings()


# ========== DO STUFF ==========

def input_thread(L):
    # This is a dumb func for usnig Enter as a graceful exit mechanism...
    raw_input()
    L.append(None)

    
def trigger_stim():

    L = []
    thread.start_new_thread(input_thread, (L,))

    while True:
        target_port_val = device.getSensorValue(target_port)                            # Poll the sensors.
        distractor_port_val = device.getSensorValue(distractor_port)

        if sense_head:
            head_val = device.getSensorValue(head_channel)
            head_in = head_val <= head_threshold
        else:
            head_in = True

        if one_port:                                                                    # IF SINGLE PORT TASK...

            if (target_port_val >= threshold) and head_in:                              # If target port licked:
                if mode=='pulsepal':                                                    # Soft-trigger channels.
                    pulse.triggerOutputChannels(channels[0], channels[1], channels[2], channels[3])
                    pulse.setDisplay("Channel 1", "ZAP!!!")
                    pulse.setDisplay("Channel 1", "done!!!")
                else:                                   
                    device.setOutputState(ext_trigger, True)                            # OR, Ext tRIGGER all channels.
                    time.sleep(train_duration)                                          # Wait until train is done
                    device.setOutputState(ext_trigger, False)                           # Turn trigger output state off

                global nt 
                nt += 1                                                                 # Increment dummy counter...
                D['n_targets'].append((time.time(), nt))

        else:                                                                           # ELSE, TWO+ PORT TASK...

            if (target_port_val >= threshold) and (distractor_port_val < threshold)\
                    and head_in:                                                        # If TARGET port licked:

                if play_tones:
                    success_tone.play()                                                 # Play tones.
                if mode=='pulsepal':                                                    # Soft-trigger channels.
                    pulse.triggerOutputChannels(channels[0], channels[1], channels[2], channels[3])
                    pulse.setDisplay("Channel 1", "ZAP!!!")
                    pulse.setDisplay("Channel 1", "done!!!")
                else:
                    device.setOutputState(ext_trigger, True)                            # OR, Ext tRIGGER all channels.
                    time.sleep(train_duration)                                          # Wait until train is done
                    device.setOutputState(ext_trigger, False)                           # Turn trigger output state off
                global nt                                                               # Increment dummy counter...
                nt += 1
                D['n_targets'].append((time.time(), nt))

            elif (distractor_port_val >= threshold) and (target_port_val < threshold)\
                    and head_in:                                                        # If DISTRACTOR port licked:

                if give_feedback and play_tones:                                        # Force time out [and play sound]
                    print "In TIMEOUT for %i seconds." % timeout_time
                    now = time.time()
                    while time.time() - now <= timeout_time:
                        if play_tones:
                            fail_tone.play()
                            time.sleep(0.2)

                global nd                                                               # Increment dummy counter...
                nd += 1
                D['n_distractors'].append((time.time(), nd))

            elif (distractor_port_val >= threshold) and (target_port_val >= threshold)\
                    and head_in:                                                        # If BOTH ports licked:

                if give_feedback and play_tones:                                        # Force time out [and play sound]
                    now = time.time()
                    print "In TIMEOUT for %i seconds." % timeout_time
                    while time.time() - now <= timeout_time:
                        if play_tones:
                            fail_tone.play()
                            time.sleep(0.2)

                global nb                                                               # Increment dummy counter...
                nb += 1
                D['n_both'].append((time.time(), nb))

        if L:                                                                           # GTFO.
            print "Exiting loop..."
            break


# ========== DO STUFF FOR MW MODE ==========

def trigger_mw():

    ML = []
    thread.start_new_thread(input_thread, (ML,))

    client.register_callback_for_name('#state_system_mode', handle_state_mode)
    client.register_callback_for_name('stim_trigger', send_trigger)

    while not (0 in state_system_mode or 1 in state_system_mode):

        if stim:
            print "TRIGGER!"
            # device.setOutputState(ext_trigger, True)    # trigger once
            # time.sleep(train_duration)                  # wait until train is done
            # device.setOutputState(ext_trigger, False)   # turn off
            global nt
            nt += 1
            D['n_targets'].append((time.time(), nt))

        if ML: 
            print "Exiting MW loop..."
            break

    print "STATE MODES: ", state_system_mode

    client.finalize()


def handle_state_mode(mevt):
    state_system_mode.append(mevt.value)
    return state_system_mode


def send_trigger(mevt):
    global stim
    stim = mevt.value
    return stim


def save_data(data, fn):
    print "Trying to save..."
    pkl.dump(data, fn)
    print "save successful: %s" % fn


def initiate_variables():
    
    # data counters:
    D = dict()
    D['n_targets'] = []
    D['n_distractors'] = []
    D['n_both'] = []

    # session parameters:
    parameters = dict()
    strt_time = time.time()
    parameters['lick_threshold'] = threshold
    parameters['mode'] = mode
    parameters['sound'] = play_tones
    parameters['feedback'] = give_feedback
    parameters['head'] = sense_head

    parameters['ext_trigger'] = ext_trigger
    parameters['target_port'] = port_names[lick_port-1]
    parameters['target_port_channel'] = target_port
    parameters['distractor_port'] = port_names[ignore_port-1]
    parameters['distractor_port_channel'] = distractor_port
    parameters['n_pulses'] = n_pulses
    parameters['pulse_width'] = pulse_width
    parameters['pulse_voltage'] = pulse_voltage
    parameters['frequency'] = frequency
    parameters['start_time'] = strt_time

    return D, parameters


if __name__ == '__main__':

    D, parameters = initiate_variables()
    nt = 0
    nd = 0
    nb = 0

    if program:
        print "Re-programming successful"

    elif mode=='mworks':
        try:
            print "Entering MW mode - listening for callbacks..."
            state_system_mode = []
            stim = 0
            trigger_mw()
        except RuntimeError as e:
            print "Runtime Error: %s" % (e)
            print "Is MWorks protocol running?"
            if save:
                print "Phidget error detected, will try to save data..."
                parameters['counts'] = D
                parameters['end_time'] = time.time()
                save_data(parameters, fn_params)
            exit(1)

    else: # mode is "naked" otherwise...
        try:
            print "Starting session."
            trigger_stim()
        except PhidgetException as e:
            print "Phidget Exception %i: %s" % (e.code, e.details)
            if save:
                print "Phidget error detected, will try to save data..."
                parameters['counts'] = D
                parameters['end_time'] = time.time()
                save_data(parameters, fn_params)
            exit(1)

    print("Press Enter to SAVE & GTFO")
    chr = sys.stdin.read(1)

    # Close Phidget
    if mode=='naked':
        try:
            print "Closing Phidget..."
            device.closePhidget()
        except PhidgetException as e:
            LocalErrorCatcher(e)

    # Disconnect PulsePal
    if program:
        print "Disconnecting PulsePal..."
        pulse.disconnect() # Sends a termination byte + closes the serial port. PulsePal stores current params to EEPROM.

    if save:
        print "saving..."
        parameters['counts'] = D #counts
        parameters['end_time'] = time.time()
        pkl.dump(parameters, fn_params)
        print parameters
        print "DATA SAVED..."

        print("Closing datafiles...")
        fn_params.close()
        fn_evs.close()
        if sense_head:
            fn_head.close()
        print "closed data file"


    print("Done.")
    exit(0)
