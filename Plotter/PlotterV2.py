import numpy as np
import matplotlib.pyplot as plt
import csv
import os
import glob
import scipy.signal as sp

def FindPeaksV1(data, threshold, width=15):
    size = len(data)
    indices = []
    Prevtracker = False
    for index in range(size - width):
        if(data[index + width] - data[index] > threshold):
            Prevtracker = True
        elif(Prevtracker):
            indices.append(index + width)
            Prevtracker = False
        elif(data[index] - data[index + width] > threshold):
            Prevtracker = True
        elif(Prevtracker):
            indices.append(index)
            Prevtracker = False
    return np.array(indices)

def FindPeaksV2(data, threshold, width=40):
    size = len(data)
    indices = []
    LastIndex = 0
    for index in range(size - width):
        if(data[index + width] - data[index] > threshold and not index <= LastIndex < index + width + width):
            LastIndex = index + width + width
            indices.append(LastIndex)
        if(data[index] - data[index + width] > threshold and not index <= LastIndex < index + width + width):
            LastIndex = index + width + width
            indices.append(index)
    return np.array(indices)

def FindPeaksV3(data: np.ndarray, threshold, width=40):
    size = len(data)
    indices = []
    Gradients = np.gradient(data)
    Toggle = False
    for index in range(size - width):
        workingset = Gradients[index:index + width]
        # workingset = workingset / np.average(workingset)
        Max = np.max(np.absolute(workingset))
        PeakArea = Max < threshold
        if(PeakArea and not Toggle):
            # Found the start of the peak range
            Toggle = True
        if(not PeakArea and Toggle):
            # Found the end of the peak range
            if(abs(data[index]) > 10):
                # Peak area
                indices.append(index)
            else:
                # Zero area
                indices.append(index + width)
            Toggle = False
    return np.array(indices)

def FindPeaksV4(data: np.ndarray, threshold, width=40):
    size = len(data)
    indices = []
    Gradients = np.gradient(data)
    FallingToggle = False
    RisingToggle = False

    for index in range(size - width):
        PeakArea = np.sum(Gradients[index:index + width])
        if(PeakArea > threshold):
            # Start rising area
            RisingToggle = True
        elif(not PeakArea > threshold and RisingToggle):
            #  End rising area
            indices.append(index + width)
            RisingToggle = False
        if(PeakArea < -threshold and not FallingToggle):
            # Start falling area
            indices.append(index)
            FallingToggle = True
        elif(not PeakArea < -threshold):
            # End falling area
            FallingToggle = False
    return np.array(indices)

def FindPeaksV5(data: np.ndarray, threshold, width=60):
    size = len(data)
    StartIndices = []
    EndIndices = []
    Gradients = np.gradient(data)
    FallingToggle = False
    RisingToggle = False

    for index in range(size - width):
        PeakArea = np.sum(Gradients[index:index + width])
        
        if(PeakArea > threshold and not RisingToggle):
            # Start rising area
            StartIndices.append(index)
            RisingToggle = True
        elif(not PeakArea > threshold and RisingToggle):
            #  End rising area
            EndIndices.append(index + width)
            RisingToggle = False
        if(PeakArea < -threshold and not FallingToggle):
            # Start falling area
            StartIndices.append(index)
            FallingToggle = True
        elif(not PeakArea < -threshold and FallingToggle):
            # End falling area
            EndIndices.append(index + width)
            FallingToggle = False
    return np.array(StartIndices), np.array(EndIndices)

def FindPeaksV6(data: np.ndarray, threshold, width=60):
    size = len(data)
    StartIndices = []
    EndIndices = []
    Gradients = np.gradient(data)
    FallingToggle = False
    RisingToggle = False
    hysteresis = threshold * 0.05
    for index in range(size - width):
        PeakArea = np.sum(Gradients[index:index + width])
        
        if(PeakArea > threshold and not RisingToggle):
            # Start rising area
            StartIndices.append(index)
            RisingToggle = True
        elif(not PeakArea > hysteresis and RisingToggle):
            #  End rising area
            EndIndices.append(index)
            RisingToggle = False
        if(PeakArea < -threshold and not FallingToggle):
            # Start falling area
            StartIndices.append(index)
            FallingToggle = True
        elif(not PeakArea < -hysteresis and FallingToggle):
            # End falling area
            EndIndices.append(index)
            FallingToggle = False
    return np.array(StartIndices), np.array(EndIndices)

def ButterLowpass(data, cutoff, samplerate, order=5):
    nyq = 0.5 * samplerate
    normal_cutoff = cutoff / nyq
    b, a = sp.butter(order, normal_cutoff, btype='low', analog=False)
    return sp.filtfilt(b, a, data)

def FindCSV():
    files = os.listdir()
    return [name for name in files if name.endswith('.csv')]

AppliedLoads = np.array([624, 1124, 1624, 2124, 2624, 3124, 3624, 4124])

def Main():
    ColNames = []
    data = []
    StartPeaks = []
    EndPeaks = []
    Gradients = []
    Averages = []

    
    csvs = FindCSV()
    
    for item in csvs:
            
        file = list(csv.reader(open(item, newline='')))
        ColNames.append(file[6][1:])
        Raw = np.array(file[7:])[:,1:].astype(np.float)
        
        # Number of colums in csv
        nColumns = Raw.shape[1]
        nRows = Raw.shape[0]
        Measurement = np.empty((nColumns, nRows))
        for i in range(nColumns):
            ph = np.reshape(Raw[:,i], (nRows))
            Measurement[i] = ButterLowpass(ph, 0.8, 12.5, order=3)
            # Measurement[i] = ph
        
        # Calculate average values
        # Find highest value in measurements
        # np.where(Measurement == np.amax(Measurement))
        Start, End = FindPeaksV6(Measurement[0], 13, width=50)
        # Start and End should be of the same length, and 8
        # if(Start.size != End.size or End.size != AppliedLoads.size * 2):
        #     raise ValueError

        nAverages = int(len(End) / 2)
        Average = np.empty((nColumns, nAverages))
        for Column in range(nColumns):
            avg = np.zeros(nAverages)
            for SectionIndex in range(0, len(End) - 1, 2):
                avg[int(SectionIndex / 2)] = np.average(Measurement[Column, End[SectionIndex]:Start[SectionIndex + 1]])
            # Calculate relation to load (um*m-1*g-1)
            # Relation = np.average(np.divide(avg, AppliedLoads))
            Average[Column] = np.array(avg)
        
        # if(item.startswith('X') or item.startswith('Y')):
        
        Gradient = np.gradient(Measurement[0])
        Gradients.append(Gradient)
        StartPeaks.append(Start)
        EndPeaks.append(End)
        data.append(Measurement)
        Averages.append(Average)
        
    
    
    Plots = len(data)
    Rows = 3
    Columns = int((Plots) / Rows + 0.99)
    BaseValue = Rows * 100 + Columns * 10
    fig = plt.figure()
    fig.suptitle('Measurements')
    for index in range(Plots):
        sfig = plt.subplot((BaseValue + index + 1))
        for i in range(data[index].shape[0]):
            sfig.plot(data[index][i], label=ColNames[index][i])
        # sfig.plot(data[index][0], label=ColNames[index][0])
        sfig.plot(Gradients[index], label='Gradient of {}'.format(ColNames[index][0]))
        for peak in StartPeaks[index]:
            sfig.axvline(x=peak, color='g')
        for peak in EndPeaks[index]:
            sfig.axvline(x=peak, color='r')
        sfig.set_ylabel('Relative stretch (um/m)')
        sfig.set_title(csvs[index])
        sfig.legend()
        sfig.grid()
    plt.show()
        

    
if __name__ == '__main__':
    Main()

