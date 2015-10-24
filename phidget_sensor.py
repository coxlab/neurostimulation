#! /usr/env/python

'''
# 
# Script to run from command line to control PulsePal & Phidgets.
# 
# run "python phidget_sensor.py"
#
# Three modes of operating:
# a.  "naked" (PulsePal + Phidget only) 
# b.  "MWorks"  (Listen to MWorks to control PulsePal via Phidget)
# c.  "trigger" (Use external trigger, e.g,. intan, to trigger PulsePal)
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

parser = optparse.OptionParser()
parser.add_option('--mode', action="store", dest="mode", default="naked", help="naked, MWorks, or trigger")

parser.add_option('--ch', action="store", dest="channel_num", default="1", help="output channel for stimulation")
parser.add_option('--thresh', action="store", dest="threshold", default="800", help="lick sensor threshold value")
parser.add_option('--lick-port', action="store", dest="lick_port", default="1", help="left (1) or right(2) lickport")

(options, args) = parser.parse_args()
mode = options.mode

# Phidget specific imports
from Phidgets.PhidgetException import *
from Phidgets.Events.Events import *
# from Phidgets.Devices.InterfaceKit import *
from Phidgets.Devices import *
from Phidgets.Phidget import PhidgetLogLevel
from Phidgets.Manager import Manager

# PulsePal imports
import imp
scriptpath = '/Repositories/PulsePal/Python/PulsePal.py'
sys.path.append(os.path.abspath(scriptpath))
from os.path import expanduser
home = expanduser("~")
path_to_file = home + scriptpath
imp.load_source('PulsePal', path_to_file)
from PulsePal import PulsePalObject # Import PulsePalObject

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

# def interfaceKitSensorChanged(e):
#     source = e.device
#     # print("InterfaceKit %i: Sensor %i: %i" % (source.getSerialNum(), e.index, e.value))
#     return (e.index, e.value)

# def interfaceKitOutputChanged(e):
#     source = e.device
#     # print("InterfaceKit %i: Output %i: %s" % (source.getSerialNum(), e.index, e.state))

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

# ========= Experiment Parameters ==========   

pulse_port = '/dev/ttyACM0' # port for PulsePal

n_pulses = 8                # num of pulses for reward
pulse_width = 2.            # ms: phase1Duration = pulse_width/1000. (s)
pulse_voltage = 5.           # V: phase1Voltage (set output channel 2 to use 7V pulses)
frequency = 25.             # Hz: interPulseInterval = 1./frequency (s), i.e,. time bw pulses

# parser = optparse.OptionParser()
# parser.add_option('--ch', action="store", dest="channel_num", default="1", help="output channel for stimulation")
# parser.add_option('--thresh', action="store", dest="threshold", default="800", help="lick sensor threshold value")
# parser.add_option('--lick-port', action="store", dest="lick_port", default="1", help="left (1) or right(2) lickport")

# (options, args) = parser.parse_args()

channel_num = int(options.channel_num)  # which channel will be the output channel from PulsePal during stim
threshold = float(options.threshold)    # value of Phidget sensor channel that counts as "licking"
lick_port = int(options.lick_port)      # reward for licking LEFT or RIGHT port (currently, just reward)

port_names = ["LEFT", "RIGHT"]
if lick_port==1:
    target_port = 5 # LEFT PORT
else:
    target_port = 7 # RIGHT PORT

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
    # device.setOnOutputChangeHandler(interfaceKitOutputChanged)
    # device.setOnSensorChangeHandler(interfaceKitSensorChanged)
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

# ========== Initialize PulsePal ==========

# Initalize PulsePal
pulse = PulsePalObject() # Create a new instance of a PulsePal object
pulse.connect(pulse_port) # Connect to PulsePal on port COM4 (open port, handshake and receive firmware version)
print(pulse.firmwareVersion) # Print firmware version to the console

# ========== Set PulsePal Settings ==========

channels = np.zeros(4)
channels[channel_num-1] = 1
# channels = [int(i) for i in channels]

print "Output channels: %s" % str(channels)
print "Target port: %s (channel %i)" % (port_names[lick_port - 1], target_port)
print "|------------|----------------|-------------|-----------|"
print "|- N pulses -|- plulse width -|- frequency -|- voltage -|"
print "|------------|----------------|-------------|-----------|"
print "|-        %i -|-     %2.3f ms -|-  %2.2f Hz -|-  %2.2f V -|" % (n_pulses, pulse_width, frequency, pulse_voltage)

pulse.isBiphasic[channel_num] = 1 # parameter arrays are 5 elements long. Use [1] for output channel 1. 
pulse.customTrainID[channel_num] = 0 # set to 0 for parametric (non custom train 1 or 2)

if pulse.isBiphasic[channel_num] == 1:
    phasic = 2
else:
    phasic = 1
train_duration = n_pulses * (((pulse_width/1000.) * phasic) + 1./frequency)
print "Train duration: %f sec" % train_duration
print "Biphasic pulses: %i" % pulse.isBiphasic[channel_num]
print "Press Enter to CONTINUE..."
chr = sys.stdin.read(1)

print "Parameters accepted! Continuing... [ctrl+C to Quit]"
pulse.setDisplay("Starting! :)", "STIM on CH %i" % channel_num)

pulse.interPhaseInterval[channel_num] = 0. # time between pos and neg pulse for biphasic # min seems to be 0.01s
pulse.interPulseInterval[1:5] = [1./frequency]*4 # time between biphasic pulses
pulse.phase1Voltage[channel_num] = pulse_voltage # (set output channel x to use 7V pulses)
pulse.phase1Duration[channel_num] = pulse_width/1000.
# pulse.restingVoltage[1:5] = [0]*4 #= #0
# pulse.phase2Voltage[channel_num] = -1*pulse_voltage # this gets auto-set if isBiphasic
pulse.phase2Duration[channel_num] = pulse_width/1000.

pulse.pulseTrainDuration[channel_num] =  train_duration # 0.01 # channel#, train duration (sec)
pulse.pulseTrainDelay[channel_num] = 0. #(0s - 3600s, 0.0001s resolution, 0.00001s precision)

pulse.burstDuration[channel_num] = 0 #(2*pulse_width) / 1000. #1./frequency.
# pulse.interBurstInterval[channel_num] = 1./frequency

# pulse.triggerMode = 0
# pulse.linkTriggerChannel1[1:5] = [0]*4

pulse.syncAllParams() # This call is critical to update PulsePal object settings from last session...!

# ========== DO STUFF ==========

try:
    try:
        while True:


            # poll the sensors:
            target_port_val = device.getSensorValue(target_port);
            # two = device.getSensorValue(lick_port2)

            if target_port_val > threshold:
                # trigger pulse
                pulse.triggerOutputChannels(channels[0], channels[1], channels[2], channels[3]) # Soft-trigger output channels 1, 2 and 4
                pulse.setDisplay("Channel 1", "ZAP!!!")
                print pulse.phase1Voltage, pulse.phase2Voltage
                time.sleep(5)
                pulse.setDisplay("Channel 1", "done!!!")

    except KeyboardInterrupt:
        pass

except PhidgetException as e:
    print "Phidget Exception %i: %s" % (e.code, e.details)
    exit(1)



print("Press Enter to quit....")

chr = sys.stdin.read(1)

print("Closing...")

# Close Phidget
try:
    device.closePhidget()
except PhidgetException as e:
    LocalErrorCatcher(e)

print("Done.")
# exit(0)

# Disconnect PulsePal
pulse.disconnect() # Sends a termination byte + closes the serial port. PulsePal stores current params to EEPROM.
