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
import itertools

datadir = sys.argv[1] #'/home/juliana/Documents/dtest/'
combo_flag = sys.argv[2]
special_combo = False
if combo_flag==1:
    special_combo = True

files = os.listdir(datadir)
files = sorted([f for f in files if os.path.splitext(f)[1] == '.pkl'], reverse=True) # most recent

# animal = fname.split('_')[0]
# date = fname.split('_')[1]
# tstamp = fname.split('_')[2]

fig = plt.figure()

session_times = sorted(set([f.split('_')[1]+'_'+f.split('_')[2] for f in files]), reverse=True)
# curr_session = [f for f in files if session_times[0] in f]
sidx = 0
E = dict()
for s in session_times:
    E[s] = dict()
    print s
    sidx += 1
    curr_session = [f for f in files if s in f]
    for fname in curr_session:
        f = open(os.path.join(datadir, fname), 'rb')
        if 'params' in fname:
            print "Getting params..."
            # E[s]['params'] = pkl.load(f)
            # print E[s]['params']
            E[s]['params'] = []
            while 1:
                try:
                    E[s]['params'].append(pkl.load(f))
                # except TypeError:
                #     print "bad pickle"
                #     break
                except EOFError:
                    break
                # except:
                #     break
            # f.close()
        else:
            E[s]['evs'] = []
            while 1:
                try:
                    E[s]['evs'].append(pkl.load(f))
                # except TypeError:
                #     print "bad pickle"
                #     break
                except EOFError:
                    break
                # except:
                #     break
            # f.close()

# Do this dumb adjustment to combine sessions with the same parameter:
if special_combo:
    sorted_sessions = sorted(E.keys())
    E['combo'] = dict()
    E['combo']['evs'] = list(itertools.chain.from_iterable([E[sorted_sessions[1]]['evs'], E[sorted_sessions[2]]['evs']]))
    E['combo']['params'] = E[sorted_sessions[1]]['params']

    use_these = [sorted_sessions[0], 'combo']
else:
    use_these = sorted(E.keys())

print use_these   

plots = dict()
cidx = 0
for k in use_these:

    cidx += 1
    # plots[k] = dict()

    evs = E[k]['evs']
    params = E[k]['params'][0]
    if k=='combo':
        fname = sorted_sessions[1]
        strt_secs = params['start_time']
        end_secs = E[sorted_sessions[2]]['params']['end_time'] # combine 2 "sessions" then need end time of 2nd session

        fmt = '%Y%m%d_%H%M%S'
        t_start = time.strftime(fmt, time.localtime(strt_secs))
        t_end = time.strftime(fmt, time.localtime(end_secs))

    else:
        fname = k

        # time.localtime(min(trigger_times))
        strt_secs  = params['start_time'] #int(sevs[0]['time'].split('_')[1][0:4])
        end_secs = params['end_time'] #int(curr_session[0].split('_')[2][0:4])

        fmt = '%Y%m%d_%H%M%S'
        t_start = time.strftime(fmt, time.localtime(strt_secs))
        t_end = time.strftime(fmt, time.localtime(end_secs))


    print fname
    # print params['counts']

    animal = os.path.split(os.path.split(datadir)[0])[1] #fname.split('_')[0]
    date = fname.split('_')[0] #fname.split('_')[1]
    tstamp = fname.split('_')[1] #fname.split('_')[2]


    sensor_keys = set([i.keys()[0] for i in evs])
    print sensor_keys
    events = dict()
    for key in sensor_keys:
        events[key] = [i[key] for i in evs if key in i.keys()]

    # trigger_evs = events['output'] # trigger events
    # sensor_evs = evs['sensor'] # sensor events
    if events: 
        plots[k] = dict()

        n_triggers_detected = len([t['time'] for t in events['trigger'] if t['index']==params['ext_trigger'] and t['value']])
        n_sensors_detected = len([t['time'] for t in events['sensor'] if t['index']==params['target_port_channel'] and t['value'] > params['lick_threshold']])

        target_vals = [(i['time'], i['value']) for i in events['sensor'] if i['index']==params['target_port_channel']]
        distractor_vals = [(i['time'], i['value']) for i in events['sensor'] if i['index']==params['distractor_port_channel']]

        trigger_times = [i['time'] for i in events['trigger'] if i['index']==params['ext_trigger'] and i['value'] ]


        # # time.localtime(min(trigger_times))
        # strt_secs  = params['start_time'] #int(sevs[0]['time'].split('_')[1][0:4])
        # end_secs = params['end_time'] #int(curr_session[0].split('_')[2][0:4])

        # fmt = '%Y%m%d_%H%M%S'
        # t_start = time.strftime(fmt, time.localtime(strt_secs))
        # t_end = time.strftime(fmt, time.localtime(end_secs))

        taxis = np.linspace(strt_secs, end_secs, num=len(target_vals), endpoint=True)
        daxis = np.linspace(strt_secs, end_secs, num=len(distractor_vals), endpoint=True)

        # print sidx

        plots[k]['trigger_times'] = trigger_times
        plots[k]['target_vals'] = target_vals
        plots[k]['taxis'] = taxis
        plots[k]['distractor_vals'] = distractor_vals
        plots[k]['daxis'] = daxis
        plots[k]['start_time'] = strt_secs
        plots[k]['end_time'] = end_secs
    else:
        continue

#     fig.add_subplot(1,len(use_these),cidx)

#     plt.plot(trigger_times, np.ones(len(trigger_times))*1000, 'r|', markersize=30, markeredgewidth=2, alpha=0.2, label='trigger')

#     plt.plot(taxis, [i[1] for i in target_vals], 'co',  markersize=5, label='target')
#     plt.plot(daxis, [i[1] for i in distractor_vals], 'ko', markersize=5, label='distractor', alpha = 0.5)

#     plt.xlabel('time (ms)')
#     plt.ylabel('sensor value')
#     plt.suptitle('time spent licking')
#     plt.title('%i pulses | %i us | %i uA @ %i Hz' % (params['n_pulses'], params['pulse_width']*1000, params['pulse_voltage']*100, params['frequency']))
#     plt.legend()
#     # plt.show()

# plt.show()

# imname = animal + '_' + date + '_' + tstamp + '.png'
# basedir = os.path.split(os.path.split(datadir)[0])[0]
# figdir = os.path.join(basedir, 'figures')
# print figdir
# print imname
# if not os.path.exists(figdir):
#     os.mkdir(figdir)
# fig.savefig(figdir + '/' +  imname)
# print figdir + '/' + imname


# fig = plt.figure()
# cidx = 0
# session_names = ['session1', 'session2']
# for k in plots.keys():

#     cidx += 1

#     fig.add_subplot(1,len(plots.keys()), cidx)
#     n, bins, patches = plt.hist([[i[1] for i in plots[k]['target_vals']], [i[1] for i in plots[k]['distractor_vals']]], 20, histtype='bar',
#                                 color=['red', 'black'],
#                                 label=['target', 'distractor'])

#     plt.title(session_names[cidx-1])

# plt.legend()
# plt.show()

# imname = animal + '_' + date + '_' + tstamp + '_histogram' + '.png'
# basedir = os.path.split(os.path.split(datadir)[0])[0]
# figdir = os.path.join(basedir, 'figures')
# print figdir
# print imname
# if not os.path.exists(figdir):
#     os.mkdir(figdir)
# fig.savefig(figdir + '/' +  imname)
# print figdir + '/' + imname


# TRYIN SOME PLOTLY:
import plotly.plotly as py
import plotly.graph_objs as go
import plotly.tools as tls

title = animal + '_' + date

session_names = ['session1', 'session2']

color_target = 'rgb(231,41,138)'  # a nice fuchsia
color_distractor = 'rgb(230,171,2)'     # a nice yellow

splts = range(1,3)


# TITLES (main and subplots):
title = "<b>Counts of Licking: </b>"+animal + "_" + date  # plot's title

# # Make 'title' annotation object
# anno_title = go.Annotation(
#     text=title,    # set plot's title
#     xref='paper',  # use paper coordinates
#     yref='paper',  #   for both x and y coords
#     x=0,        # x and y position 
#     y=1.2,        #   in norm. coord.     
#     font=go.Font(size=22),  # text font size
#     showarrow=False,       # no arrow (default is True)
#     bgcolor='#F5F3F2',     # light grey background color
#     bordercolor='#FFFFFF', # white borders
#     borderwidth=1,         # set border width
#     borderpad=22           # set border-text space
# )

# # Define an annotation-generation function, for subplot titles
# def make_anno_splt(text, yref):
#     return go.Annotation(
#         text=text,   # set subplot title
#         xref='x1',     # (!) subplot share the same x-axis
#         yref=yref,     # (!) ref on y-axis
#         x=8,            # set x position ' 
#         xanchor='left', #   and anchor
#         y=y_range[1],   # set y position
#         yanchor='top',  #   and anchor
#         font=go.Font(size=14),  # text font size
#         showarrow=False,       # no arrow (default is True)
#         bgcolor='#F5F3F2',     # light grey background color
#         bordercolor='#FFFFFF', # white borders
#         borderwidth=1,         # set border width
#         borderpad=5           # set border-text space
#     )


# # Define dictionary of axis style options
axis_style = dict(
    zeroline=False,       # remove thick zero line
    showgrid=True,        # show grid lines (not default on bar/histogram)
    gridcolor='#FFFFFF',  # white grid lines
    ticks='outside',      # draw ticks outside axes 
    ticklen=8,            # tick length
    tickwidth=1.5         #   and width
)

# Make layout object
layout = go.Layout(
    barmode='group',  # (!) overlay barmode
    title=title,        # set plot title
    xaxis=go.XAxis(
        axis_style,               # style options
        # title='<b>Grade [%]</b>'  # x-axis title
    ),
    yaxis=go.YAxis(
        axis_style,               # sytle options
        # title='<b>Count</b>'      # y-axis title 
    ),
    legend=go.Legend(
        x=0,
        y=1   # legend at upper left corner of plot
    ),
    plot_bgcolor='#EFECEA'   # set plot color to grey

)

x1_axis_style = dict(
    zeroline=False,       # remove thick zero line
    showgrid=True,        # show grid lines (not default on bar/histogram)
    gridcolor='#FFFFFF',  # white grid lines
    ticks='outside',      # draw ticks outside axes 
    ticklen=8,            # tick length
    tickwidth=1.5,         #   and width
    type='category',
    anchor='y'
)

x2_axis_style = dict(
    zeroline=False,       # remove thick zero line
    showgrid=True,        # show grid lines (not default on bar/histogram)
    gridcolor='#FFFFFF',  # white grid lines
    ticks='outside',      # draw ticks outside axes 
    ticklen=8,            # tick length
    tickwidth=1.5,         #   and width
    type='date',
    anchor='y2'
)


trace1 = go.Bar(
    x=session_names,
    y=[len(plots[k]['target_vals']) for k in plots.keys()],
    name='targets',
    marker=go.Marker(color=color_target),     # set bar color
    xaxis="x{}".format(1),  # (!) plot on 'splt' x-axis
    yaxis="y{}".format(1),  # (!) plot on 'splt' y-axis
    showlegend=1   # (!) show only 2 traces in legend
)
trace2 = go.Bar(
    x=session_names,
    y=[len(plots[k]['distractor_vals']) for k in plots.keys()],
    name='distractors',
    marker=go.Marker(color=color_distractor),     # set bar color
    xaxis="x{}".format(1),  # (!) plot on 'splt' x-axis
    yaxis="y{}".format(1),  # (!) plot on 'splt' y-axis
    showlegend=1   # (!) show only 2 traces in legend
)

T_all_the_data = np.array(list(itertools.chain.from_iterable([plots[k]['target_vals'] for k in plots.keys()])))
D_all_the_data = np.array(list(itertools.chain.from_iterable([plots[k]['distractor_vals'] for k in plots.keys()])) )
time_points_all = [plots[sorted(plots.keys())[0]]['start_time'], plots[sorted(plots.keys())[-1]]['end_time']] # in MIN

if T_all_the_data.any() and D_all_the_data.any():
    y_range = [min([T_all_the_data.min(), D_all_the_data.min()]), max([T_all_the_data.max(), D_all_the_data.max()])]
else:
    y_range = [0, 10]


# # Define an annotation-generation function, for subplot titles
# def make_anno_splt(text, xref):
#     return go.Annotation(
#         text=text,   # set subplot title
#         xref= xref, #paper', #'x1',     # (!) subplot share the same x-axis
#         yref= 'y1', #paper',     # (!) ref on y-axis
#         x=0,            # set x position ' 
#         xanchor='top', #   and anchor
#         y=y_range[1],   # set y position
#         yanchor='top',  #   and anchor
#         font=go.Font(size=14),  # text font size
#         showarrow=False,       # no arrow (default is True)
#         bgcolor='#F5F3F2',     # light grey background color
#         bordercolor='#FFFFFF', # white borders
#         borderwidth=1,         # set border width
#         borderpad=5           # set border-text space
#     )


binsize = 15
t = np.linspace(time_points_all[0], time_points_all[1], binsize, endpoint=True)
nbins = round(t[2]-t[1])
# bins = np.linspace(time_points_all[0], time_points_all[1], num=nbins, endpoint=True)

trace3 = go.Histogram(
    x=[i[0] for i in T_all_the_data], #[time.strftime(fmt, time.localtime(i[0])) for i in T_all_the_data], 
    name='targets',
    opacity=0.5,
    autobinx=False,
    xbins=dict(
        start=time_points_all[0], #time.strftime(fmt, time.localtime(time_points_all[0])),
        end=time_points_all[1], #time.strftime(fmt, time.localtime(time_points_all[1])), #time_points_all[1],
        size=binsize
    ),
    # nbinsx = nbins,
    marker=go.Marker(color=color_target),     # set bar color
    xaxis="x{}".format(2),  # (!) plot on 'splt' x-axis
    yaxis="y{}".format(2),  # (!) plot on 'splt' y-axis
    showlegend=1   # (!) show only 2 traces in legend

)
trace4 = go.Histogram(
    x=[i[0] for i in D_all_the_data], #[time.strftime(fmt, time.localtime(i[0])) for i in T_all_the_data], #[i[0] for i in D_all_the_data],
    name='distractors',
    opacity=0.5,
    autobinx=False,
    xbins=dict(
        start=time_points_all[0], #time.strftime(fmt, time.localtime(time_points_all[0])), #time_points_all[0],
        end=time_points_all[1], #time.strftime(fmt, time.localtime(time_points_all[1])), #time_points_all[1],
        size=binsize # n minute bins
    ),
    # nbinsx = nbins,
    marker=go.Marker(color=color_distractor),     # set bar color
    xaxis="x{}".format(2),  # (!) plot on 'splt' x-axis
    yaxis="y{}".format(2),  # (!) plot on 'splt' y-axis
    showlegend=1   # (!) show only 2 traces in legend
)


fig = tls.make_subplots(rows=1, cols=2, start_cell='bottom-left', subplot_titles=('Licks by Session', 'Breakdown by %i min bins' % binsize))

fig['data'] = [trace1, trace2, trace3, trace4]

# Update x and y axis of all subplots:
fig['layout'].update(
    {'xaxis{}'.format(splt): axis_style for splt in splts}
)
fig['layout'].update(
    {'yaxis{}'.format(splt): axis_style for splt in splts}
)

fig['layout'].update(
    {'xaxis{}'.format(1): x1_axis_style}
)

fig['layout'].update(
    {'xaxis{}'.format(2): x2_axis_style}
)

# # Make Annotations object
# annotations = go.Annotations(
#     # [anno_title] +
#     [make_anno_splt(splt_title[splt], "y{}".format(splt)) for splt in splts]
# )

# # Link 'annotations' to Annotations object
# fig['layout'].update(annotations=annotations)



# Set barmode, plot title, global font, plot background and legend
fig['layout'].update(
    # barmode='overlay',  # (!) overlay barmode
    title=title,        # plot title
    legend=go.Legend(
        x=100,  # outside plotting area to the right
        y=1     # top of plotting area 
    ),
    plot_bgcolor='#EFECEA' # set plot color to grey
)

plot_url = py.plot(fig)

print(fig.to_string())  # print figure object in human-friendly form


# fig['layout'].update(
#     xaxis = dict(
#         ticktext = [time.strftime(fmt, time.localtime(i)) for i in tickvals]
#         # tickvals = [ 0, 1, 2, 3, 4, 5 ]
#     )
#     )


# # Define a trace-generating function (returns a Histogram object)
# def make_trace(splt, x, name, color):
#     return go.Histogram(
#         x=x,                      # distribution to be plotted
#         # histnorm=histnorms[splt], # (!) histogram normalization
#         name="<b>{}</b>".format(name),  # label for legend/hover text
#         opacity=0.5,                   # partly transparent bars
#         marker=go.Marker(color=color),     # set bar color
#         showlegend=showlegends[splt],   # (!) show only 2 traces in legend
#         xaxis="x{}".format(splt),  # (!) plot on 'splt' x-axis
#         yaxis="y{}".format(splt),  # (!) plot on 'splt' y-axis
#     )

# # List of subplot [1],[2],[3],[4] labels
# splts = range(1, 5)

# # Define a dictionary of flags setting which trace appeats on the legend
# #   (values of 'showlegend' key in each trace object)
# showlegends = {
#     1: True,
#     2: False,
#     3: False,
#     4: False
# }


# fig = tls.make_subplots(rows=1, cols=2, start_cell='bottom-left')

# data1 = [trace1, trace2]
# data2 = [trace3, trace4]

# fig['data'] = go.Data(
#     [[trace1], [trace2]] + [[trace3], [trace4]]
# )

# # fig['data'] = go.Data(
# #     [make_trace(splt, [i[0] for i in T_all_the_data], 'targets', color_target) for splt in splts] +
# #     [make_trace(splt, [i[0] for i in D_all_the_data], 'distractors', color_distractor) for splt in splts]
# # )


# # LAYOUT:
# title='test'


# # (a) Update x and y axis of all subplots
# #     using the axis_style dictionary defined in subsection 4.1
# fig['layout'].update(
#     {'xaxis{}'.format(splt): axis_style for splt in splts}
# )
# fig['layout'].update(
#     {'yaxis{}'.format(splt): axis_style for splt in splts[0:2]}
# )

# # (d) Set barmode, plot title, global font, plot background and legend
# fig['layout'].update(
#     barmode='overlay',  # (!) overlay barmode
#     title=title,        # plot title
#     legend=go.Legend(
#         x=100,  # outside plotting area to the right
#         y=1     # top of plotting area 
#     ),
#     plot_bgcolor='#EFECEA' # set plot color to grey
# )

# plot_url = py.plot(fig, filename=imname)





# fig = tools.make_subplots(rows=1, cols=2)
# fig['data'] = go.Data([trace3, trace4],
#                     [trace1, trace2])

# fig['data'] += [trace1, trace2]
# fig['data'] += [trace3, trace4] #[Scatter(x=[1,2,3], y=[2,1,2], xaxis='x2', yaxis='y2')]

# # trace1 = go.Scatter(
# #     x=[1, 2, 3],
# #     y=[4, 5, 6]
# # )
# # trace2 = go.Scatter(
# #     x=[20, 30, 40],
# #     y=[50, 60, 70],
# # )

# fig = tools.make_subplots(rows=1, cols=2)

# fig.append_trace([trace1, trace2], 1, 1)
# fig.append_trace([trace3, trace4], 1, 2)

# fig['layout'].update(height=600, width=600, title='i <3 subplots')
# plot_url = py.plot(fig, filename=imname)