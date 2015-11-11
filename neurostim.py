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

parser = optparse.OptionParser()
parser.add_option('-m', '--mode', type='choice', action="store", dest="mode", default="naked", choices=['naked', 'mworks', 'pulsepal'])
parser.add_option('-P', '--program', action="store_true", dest="program", default=False, help="program pulse generator only (must be in 'pulsepal' mode)")
parser.add_option('-S', '--save', action="store_true", dest="save_data", default=False, help="save data")
parser.add_option('-O', '--output-path', action="store", dest="output_path", default="/tmp/data", help="data output path")
parser.add_option('-i', '--id', action="store", dest="animalID", default="test", help="subject ID")

parser.add_option('-c', '--channel', action="append", default=[],  dest="channel_nums", help="output channels for stimulation, e.g., '-c1'")
parser.add_option('-t', '--thresh', action="store", dest="threshold", default="500", help="lick sensor threshold value")
parser.add_option('-l', '--lick-port', action="store", dest="lick_port", default="1", help="left (1) or right(2) lickport")

parser.add_option('-p', '--oneport', action="store_true", dest="one_port", default=False, help="one or two-port task?")
parser.add_option('-s', '--sound', action="store_true", dest="play_tones", default=False, help="play reward and punish tones?")

(options, args) = parser.parse_args()
mode = options.mode
program = options.program
if program:
    mode='pulsepal' # override incorrect mode setting  
play_tones = options.play_tones

output_path = options.output_path
animalID = options.animalID
save = options.save_data
one_port = options.one_port

# ==============================================================================
# STIMULATION PARAMETERS: EDIT THESE TO CHANGE STIM PARAMS FOR A SESSION
# ==============================================================================
n_pulses = 8                # num of pulses for reward
pulse_width = .700        # ms: phase1Duration = pulse_width/1000. (s)
pulse_voltage = 1.        # V: phase1Voltage # 100uA/V
frequency = 90.          # Hz: interPulseInterval in (s) = time bw pulses
phasic = 2.               # n phases (i.e, biphasic or monophasic)

train_duration = n_pulses * (((pulse_width/1000.) * phasic) + 1./frequency)
# ==============================================================================


# ==============================================================================
# Experiment Parameters: Relevant experiment info (channels, triggers, etc.)
# ==============================================================================
channel_nums = options.channel_nums             # which PulsePal channel for stim output
channel_nums = [int(i) for i in channel_nums]   
channels = np.zeros(4)
for i in channel_nums:                          # 0-indexify and turn ON specified channels
    channels[i-1] = 1
channels = [int(i) for i in channels]           # turn into ints for soft-triggering
print "Channel nums: ", channel_nums            # print which channels being used
print "Channel status: ", channels              # channels ON or OFF

threshold = float(options.threshold)            # value of Phidget sensor channel that counts as "licking"
lick_port = int(options.lick_port)              # reward for licking specified port (currently, just reward)
ext_trigger = 0                                 # D.O. channel on phidget (connect to Trigger Ch 1 on PulsePal)

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

if play_tones:
    success_tone = pyglet.media.load('./stimuli/sounds/NRsuccess.wav', streaming=False)
    fail_tone = pyglet.media.load('./stimuli/sounds/failure_DZ.wav', streaming=False)

timeout_time = 5


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


# ==============================================================================
# MODE SPECIFIC ACTIONS:
# ==============================================================================

# ========== MWorks stuff ==========
if mode=='mworks':

    # Only need client call-backs (make sure .xml with server-side conduit is already running)
    # This mode does not use Phidgets or PulsePal, but rather triggers stimulation thru MW software

    sys.path.append('/Library/Application Support/MWorks/Scripting/Python')
    import mworks.conduit

    def say_hello(mevt):
        # print "called"
        if mevt.value:
            print "MWorks connection is G2G!"
            g2g.append(1)
        else:
            # print "Waiting for MW...."
            g2g.append(0)

        return g2g

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
    #     client.register_callback_for_name('hello_world', say_hello)

    print "LET'S DO IT!!!"
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
        # print("InterfaceKit %i: Sensor %i: %i" % (source.getSerialNum(), e.index, e.value))
        if ((e.index==target_port) or (e.index==distractor_port)) and (e.value >=threshold):
            # print "DETECTED: %i, %i" % (e.index, e.value)
            # sensor_events.append({'index':e.index, 'value':e.value,'time':time.time()})
            if save:
                pkl.dump({'sensor': {'index':e.index, 'value':e.value,'time':time.time()}}, fn_evs)
            else:
                print "LICK: %i, %i" % (e.index, e.value)
            # print sensor_events

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


# ========== PulsePal imports ==========
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

        # n_pulses = 8                # num of pulses for reward
        # pulse_width = 2.            # ms: phase1Duration = pulse_width/1000. (s)
        # pulse_voltage = 5.           # V: phase1Voltage (set output channel 2 to use 7V pulses)
        # frequency = 25.             # Hz: interPulseInterval = 1./frequency (s), i.e,. time bw pulses

        try:        
            # ========== Initialize PulsePal ==========

            pulse = PulsePalObject() # Create a new instance of a PulsePal object
            try:
                pulse.connect(pulse_port) # Connect to PulsePal on port COM4 (open port, handshake and receive firmware version)
            except OSError:
                pulse_port = '/dev/ttyACM1' # port for PulsePal
                pulse.connect(pulse_port)

            print(pulse.firmwareVersion) # Print firmware version to the console

            # ========== Set PulsePal Settings ==========

            # channels = np.zeros(4)
            # channels[channel_num-1] = 1

            print "Output channels: %s" % str(channels)
            print "Target port: %s (channel %i)" % (port_names[lick_port - 1], target_port)
            print "Distractor port: %s (channel %i)" % (port_names[ignore_port - 1], distractor_port)
            print "|------------|----------------|-------------|-----------|"
            print "|- N pulses -|- plulse width -|- frequency -|- voltage -|"
            print "|------------|----------------|-------------|-----------|"
            print "|-        %i -|-     %2.3f ms -|-  %2.2f Hz -|-  %2.2f V -|" % (n_pulses, pulse_width, frequency, pulse_voltage)

            for c in channel_nums:
                print c
                pulse.isBiphasic[c] = 1 # parameter arrays are 5 elements long. Use [1] for output channel 1. 
                pulse.customTrainID[c] = 0 # set to 0 for parametric (non custom train 1 or 2)

                pulse.interPhaseInterval[c] = 0.          # time between pos and neg pulse for biphasic # min seems to be 0.01s
                pulse.interPulseInterval[c] = 1./frequency    # time between biphasic pulses
                pulse.phase1Voltage[c] = pulse_voltage    # (set output channel x to use 7V pulses)
                pulse.phase2Voltage[c] = -1*pulse_voltage    # (set output channel x to use 7V pulses)
                pulse.phase1Duration[c] = pulse_width/1000.
                pulse.phase2Duration[c] = pulse_width/1000.
                pulse.restingVoltage[c] = 0.

                pulse.pulseTrainDuration[c] = train_duration # 0.01 # channel#, train duration (sec)
                pulse.pulseTrainDelay[c] = 0. #(0s - 3600s, 0.0001s resolution, 0.00001s precision)

                pulse.burstDuration[c] = 0 #(2*pulse_width) / 1000. #1./frequency.
                # pulse.interBurstInterval[channel_num] = 1./frequency

                # pulse.triggerMode[c] = 0                      # (0 = normal, 1 = toggle, 2 = pulse gated)
                pulse.linkTriggerChannel1[c] = 1

            pulse.triggerMode[1] = 0                            # (0 = normal, 1 = toggle, 2 = pulse gated)

            pulse.syncAllParams() # This call is critical to update PulsePal object settings from last session...!

            # if pulse.isBiphasic[channel_num] == 1:
            #     phasic = 2
            # else:
            #     phasic = 1
            # train_duration = n_pulses * (((pulse_width/1000.) * phasic) + 1./frequency)

            print "Train duration: %f sec" % train_duration
            print "Biphasic pulses: %s" % str(pulse.isBiphasic)
            print "Press Enter to CONTINUE..."
            chr = sys.stdin.read(1)

            print "Parameters accepted! Continuing... [ctrl+C to Quit]"
            pulse.setDisplay("Starting! :)", "STIM on CH %s" % str([i for i in channels if i]))

            # pulse.interPhaseInterval[1:5] = channels*0.          # time between pos and neg pulse for biphasic # min seems to be 0.01s
            # pulse.interPulseInterval[1:5] = [1./frequency]*4    # time between biphasic pulses
            # pulse.phase1Voltage[1:5] = channels*pulse_voltage    # (set output channel x to use 7V pulses)
            # pulse.phase2Voltage[1:5] = channels*pulse_voltage    # (set output channel x to use 7V pulses)
            # pulse.phase1Duration[1:5] = channels*(pulse_width/1000.)
            # pulse.phase2Duration[1:5] = channels*(pulse_width/1000.)

            # pulse.pulseTrainDuration[1:5] =  channels*train_duration # 0.01 # channel#, train duration (sec)
            # pulse.pulseTrainDelay[1:5] = channels*0. #(0s - 3600s, 0.0001s resolution, 0.00001s precision)

            # pulse.burstDuration[1:5] = channels*0 #(2*pulse_width) / 1000. #1./frequency.
            # # pulse.interBurstInterval[channel_num] = 1./frequency

            # pulse.triggerMode[1:5] = channels*0                      # (0 = normal, 1 = toggle, 2 = pulse gated)
            # pulse.linkTriggerChannel1[1:5] = channels*1
            # pulse.linkTriggerChannel1[1] = 1

            # pulse.syncAllParams() # This call is critical to update PulsePal object settings from last session...!

        except NameError, e:
            print e
            print "If trying to reprogram PulsePal, mode must also be 'pulsepal' -- try again."
            exit(1)

    else:
        print "Using last saved settings on PulsePal."
        print "Output channels: %s" % str(channels)
        print "Target port: %s (channel %i)" % (port_names[lick_port - 1], target_port)
        print "Distractor port: %s (channel %i)" % (port_names[ignore_port - 1], distractor_port)
        print "|------------|----------------|-------------|-----------|"
        print "|- N pulses -|- plulse width -|- frequency -|- voltage -|"
        print "|------------|----------------|-------------|-----------|"
        print "|-        %i -|-     %2.3f ms -|-  %2.2f Hz -|-  %2.2f V -|" % (n_pulses, pulse_width, frequency, pulse_voltage)

        print "Press Enter to CONTINUE..."
        chr = sys.stdin.read(1)

        print "Parameters accepted! Continuing... [ctrl+C to Quit]"

else:
    print "Using last saved settings on PulsePal."
    print "Output channels: %s" % str(channels)
    print "Target port: %s (channel %i)" % (port_names[lick_port - 1], target_port)
    print "Distractor port: %s (channel %i)" % (port_names[ignore_port - 1], distractor_port)
    print "|------------|----------------|-------------|-----------|"
    print "|- N pulses -|- plulse width -|- frequency -|- voltage -|"
    print "|------------|----------------|-------------|-----------|"
    print "|-        %i -|-     %2.3f ms -|-  %2.2f Hz -|-  %2.2f V -|" % (n_pulses, pulse_width, frequency, pulse_voltage)

    print "Press Enter to CONTINUE..."
    chr = sys.stdin.read(1)

    print "Parameters accepted! Continuing... [ctrl+C to Quit]"


# ========== DO STUFF ==========

def input_thread(L):
    # This is a dumb func for usnig Enter as a graceful exit mechanism...
    raw_input()
    L.append(None)
    
def trigger_stim():

    L = []
    thread.start_new_thread(input_thread, (L,))

    # D = dict()
    nt = 0
    nd = 0
    nb = 0
    D['n_targets'] = []
    D['n_distractors'] = []
    D['n_both'] = []

    while True:

        # print "."

        # poll the sensors:
        if one_port:

            if (target_port_val >= threshold):

                # trigger pulse
                if mode=='pulsepal':
                    pulse.triggerOutputChannels(channels[0], channels[1], channels[2], channels[3]) # Soft-trigger output channels 1, 2 and 4
                    pulse.setDisplay("Channel 1", "ZAP!!!")
                    print pulse.phase1Voltage, pulse.phase2Voltage
                    pulse.setDisplay("Channel 1", "done!!!")
                else:
                    # print "Triggering DO channel %i" % ext_trigger
                    device.setOutputState(ext_trigger, True)    # trigger once
                    time.sleep(train_duration)                  # wait until train is done
                    device.setOutputState(ext_trigger, False)   # turn off

                nt += 1
                D['n_targets'].append((time.time(), nt))

        else:

            target_port_val = device.getSensorValue(target_port);
            distractor_port_val = device.getSensorValue(distractor_port)

            if (target_port_val >= threshold) and (distractor_port_val < threshold):

                if play_tones:
                    # play tone:
                    success_tone.play()

                # trigger pulse
                if mode=='pulsepal':
                    pulse.triggerOutputChannels(channels[0], channels[1], channels[2], channels[3]) # Soft-trigger output channels 1, 2 and 4
                    pulse.setDisplay("Channel 1", "ZAP!!!")
                    print pulse.phase1Voltage, pulse.phase2Voltage
                    pulse.setDisplay("Channel 1", "done!!!")
                else:
                    # print "Triggering DO channel %i" % ext_trigger
                    device.setOutputState(ext_trigger, True)    # trigger once
                    time.sleep(train_duration)                  # wait until train is done
                    device.setOutputState(ext_trigger, False)   # turn off

                nt += 1
                D['n_targets'].append((time.time(), nt))

            elif (distractor_port_val >= threshold) and (target_port_val < threshold):

                # force time out [and play sound]
                now = time.time()
                while time.time() - now <= timeout_time:
                    if play_tones:
                        fail_tone.play()
                        time.sleep(0.2)
                    print (time.time() - now)

                # time.sleep(5)
                nd += 1
                D['n_distractors'].append((time.time(), nd))

            elif (distractor_port_val >= threshold) and (target_port_val >= threshold):

                # force timeout? [and play sound]
                now = time.time()
                while time.time() - now <= timeout_time:
                    if play_tones:
                        fail_tone.play()
                        time.sleep(0.2)

                # time.sleep(5)
                nb += 1
                D['n_both'].append((time.time(), nb))

        if L: 
            print "Exiting loop..."
            break

    # return D


def trigger_mw():

    def handle_state_mode(mevt):
        stop_flag.append(mevt.value)
        return stop_flag


    L = []
    thread.start_new_thread(input_thread, (L,))

    stop_flag = []
    stim = 0
    client.register_callback_for_name('stop_flag', handle_state_mode)
    client.register_callback_for_name('stim_flag', send_trigger)

    while not (1 in stop_flag):
        if stim:
            print "TRIGGER!"
            # device.setOutputState(ext_trigger, True)    # trigger once
            # time.sleep(train_duration)                  # wait until train is done
            # device.setOutputState(ext_trigger, False)   # turn off

            nt += 1

            D['n_targets'].append((time.time(), nt))

        if L: 
            print "Exiting MW loop..."
            break

# def handle_state_mode(mevt):
#     stop_flag.append(mevt.value)
#     return stop_flag


def send_trigger(mevt):
    # print "MW says to trigger..."
    # stim_flag = evt.value
    if mevt.value:
        print "MW SENDING TRIGGER"
        stim = 1
    else:
        stim = 0
    return stim


def save_data(data, fn):
    print "Trying to save..."
    pkl.dump(data, fn)
    print "save successful: %s" % fn

if __name__ == '__main__':

    # try:

    parameters = dict()

    print "Press ENTER to quit gracefully..."

    strt_time = time.time()

    parameters['lick_threshold'] = threshold
    parameters['mode'] = mode
    parameters['sound'] = play_tones
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
    # parameters['end_time'] = time.time()
    # pkl.dump(parameters, fn_params)

    if program:

        print "Re-programming successful"

    elif mode=='mworks':

        print "Entering MW mode - listening for callbacks..."
        D = dict()
        trigger_mw()

    else: # mode is "naked" otherwise...

        try:

            print "Starting session."
            # counts = trigger_stim()
            D = dict()
            trigger_stim()

        except PhidgetException as e:

            print "Phidget Exception %i: %s" % (e.code, e.details)
            if save:
                print "Phidget error detected, will try to save data..."
                parameters['counts'] = D
                parameters['end_time'] = time.time()
                save_data(parameters, fn_params)
            exit(1)

    if save:

        print "saving..."

        parameters['counts'] = D #counts
        parameters['end_time'] = time.time()
        # pkl.dump(parameters, fn_params)
        save_data(parameters, fn_params)

        print parameters

        print "DATA SAVED..."
        print("Press Enter to close")
        chr = sys.stdin.read(1)

    # except PhidgetException as e:
    #     print "Phidget Exception %i: %s" % (e.code, e.details)
    #     exit(1)

    print("Press Enter to GTFO")

    chr = sys.stdin.read(1)

    print("Closing datafiles...")
    if save:
        fn_params.close()
        fn_evs.close()
        print "closed data file"

    # Close Phidget
    if mode=='naked':
        try:
            device.closePhidget()
        except PhidgetException as e:
            LocalErrorCatcher(e)

    # Disconnect PulsePal
    if program:
        pulse.disconnect() # Sends a termination byte + closes the serial port. PulsePal stores current params to EEPROM.

    print("Done.")
    exit(0)
