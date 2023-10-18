#Importing pandas for excel-style data manipulation
#import pandas as pd
#import os
#argv checks command line arguments
#from sys import argv
#Importing streamlit for data visualization (drawing to localhost)
import streamlit as st
#Importing numpy to create x and y sine values.
import numpy as np
#Importing pyplot to make the plots
import matplotlib.pyplot as plt

#Best tutorial: https://www.youtube.com/watch?v=Sb0A9i6d320 Turn An Excel Sheet Into An Interactive Dashboard Using Python (Streamlit)

@st.cache_data
def GenerateSineWave(name, amplitude, frequencyHz, xRange):
    x = np.linspace(0, xRange, 1000)
    y = amplitude * np.sin(2 * np.pi * frequencyHz * x)
    return x, y, name

@st.cache_data
def GenerateMarkPoints(amplitude, frequencyHz, xRange, markFrequency):
    markX = np.linspace(0, xRange, int(xRange*markFrequency + 1))
    markY = amplitude * np.sin(2 * np.pi * frequencyHz * markX)

    #Apply a threshold to round small values to 0
    threshold = 1e-6
    markY[abs(markY) < threshold] = 0

    return markX, markY

#@st.cache Caching this causes issues for some reason
@st.cache_data
def PlotSineWaves(waves, markPoints): #Places dots to mark where a sample was taken givne a markFrequency
    fig, ax = plt.subplots()
    for i in range(len(waves)):
        #Plot the sine wave
        ax.plot(waves[i][0], waves[i][1], label=waves[i][2])
        #Create markings to show where samples were taken
        ax.scatter(markPoints[0], markPoints[1], color='red')

    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Amplitude')
    ax.tick_params(axis='x', labelrotation=45)
    fig.legend(loc='upper left')
    return fig

st.set_page_config(layout='wide', page_icon='∿', page_title='Aliasing Demo')
st.title("Aliasing Visualized")
st.write("Created by Adam Garsha '26")
st.write("Inspired by MEEN 260 lecture 10-11-2023")

signalFrequency = st.slider("Frequency of Signal (Hz)", -10, 10, 5, 1)
samplingFrequency = st.slider("Sampling Frequency (Hz)", 1, 10, 5, 1)

Fa = signalFrequency/samplingFrequency
print(Fa)
if (Fa > 0):
    Fa -= int(Fa+0.5)
else:
    Fa -= int(Fa-0.5)
if (Fa == 0.5 or Fa == -0.5):
    Fa = 0
print(Fa)
reconstructedFrequency = Fa * samplingFrequency

signalWave = GenerateSineWave("Signal", 1, signalFrequency, 2)
reconstructedWave = GenerateSineWave("Reconstructed", 1, reconstructedFrequency, 2)

markPoints = GenerateMarkPoints(1, signalFrequency, 2, samplingFrequency)
#st.write('Data', portfolioDf)

#Separating graphs into columns
left_col, right_col = st.columns(2)

left_col.pyplot(PlotSineWaves([signalWave], markPoints))
right_col.pyplot(PlotSineWaves([reconstructedWave], markPoints))