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
    return np.array(StartIndices), np.array(EndIndices), Gradients

def ButterLowpass(data, cutoff, samplerate, order=5):
    nyq = 0.5 * samplerate
    normal_cutoff = cutoff / nyq
    b, a = sp.butter(order, normal_cutoff, btype='low', analog=False)
    return sp.filtfilt(b, a, data)

def FindCSV():
    files = os.listdir()
    return [name for name in files if name.endswith('.csv')]

# load data from csv and filter
def GetData(file):
    data = list(csv.reader(open(file, newline='')))
    Names = {
        file: data[6][1:]
    }
    ColumnNames = data[6][1:]
    Raw = np.array(data[7:])[:,1:].astype(np.float)
    
    # Number of colums in csv
    nColumns = Raw.shape[1]
    nRows = Raw.shape[0]
    Measurement = np.empty((nColumns, nRows))
    # Clean the data for noise at 0.8 Hz and higher
    for i in range(nColumns):
        ph = np.reshape(Raw[:,i], (nRows))
        Measurement[i] = ButterLowpass(ph, 0.8, 12.5, order=3)
    
    return ColumnNames, Measurement

def CalculateAverages(Measurement):
    # Find highest value in measurements
    # HighestIndex = np.where(Measurement == np.amax(Measurement))[0]
    
    Start, End = FindPeaksV6(Measurement[0], 13, width=50)
    # Start and End should be of the same length, and 8
    if(Start.size != End.size or End.size != AppliedLoads.size * 2):
        raise ValueError

    nAverages = int(len(End) / 2)
    Averages = np.empty((Measurement.shape[0], nAverages))
    for Column in range(Measurement.shape[0]):
        avg = np.zeros(nAverages)
        for SectionIndex in range(0, len(End) - 1, 2):
            avg[int(SectionIndex / 2)] = np.average(Measurement[Column, End[SectionIndex]:Start[SectionIndex + 1]])
        # Calculate relation to load (um*m-1*g-1)
        Averages[Column] = avg
    return Averages

def CalculateRelations(Averages, References):
    Relations = np.zeros(len(Averages))
    for i in range(len(Averages)):
        Relations[i] = np.average(np.divide(Averages[i], References))
    return Relations

def Calc2DForceVector(RelationX, RelationY, Measured):
    # use only 2 of the three relations for linear system solving
    a = np.array([[RelationX[0], RelationY[0]], [RelationX[1], RelationY[1]]])
    b = np.array([Measured[0], Measured[1]])
    vector = np.linalg.solve(a, b)
    return vector

def PlotMeasurements(Data, ColNames, StartPeaks, EndPeaks, Gradients):
    Plots = len(Data)
    Rows = 3
    Columns = int((Plots) / Rows + 0.99)
    BaseValue = Rows * 100 + Columns * 10
    fig = plt.figure()
    fig.suptitle('Measurements')
    for index in range(Plots):
        sfig = plt.subplot((BaseValue + index + 1))
        for i in range(Data[index].shape[0]):
            sfig.plot(Data[index][i], label=ColNames[index][i])
        sfig.plot(Gradients[index], label='Gradient of {}'.format(ColNames[index][0]))
        
        for peak in StartPeaks[index]:
            sfig.axvline(x=peak, color='g')
        for peak in EndPeaks[index]:
            sfig.axvline(x=peak, color='r')
        
        sfig.set_ylabel('Relative stretch (um/m)')
        sfig.set_title(csvs[index])
        sfig.legend()
        sfig.grid()

def PlotAverages(Data, Xaxis, ColNames, PlotNames):
    Plots = len(Data)
    Rows = 3

    fig = plt.figure()
    fig.suptitle('Relation between load and change in length (um*m-1*g-1)')
    for index in range(Plots):
        PlotIndex = (Plots * 100 + 10 + index + 1)
        sfig = plt.subplot(PlotIndex)
        for i in range(Data[index].shape[0]):
            sfig.plot(Xaxis, Data[index][i], label=ColNames[index][i])
            # sfig.bar(Xaxis.astype(np.str), Data[index][i], label=ColNames[index][i])
        # sfig.plot(data[index][0], label=ColNames[index][0])
        # sfig.plot(Gradients[index], label='Gradient of {}'.format(ColNames[index][0]))
        # for peak in StartPeaks[index]:
        #     sfig.axvline(x=peak, color='g')
        # for peak in EndPeaks[index]:
        #     sfig.axvline(x=peak, color='r')
        # sfig.set_ylabel('Relative stretch (um/m)')
        sfig.set_xlabel('Applied load (g)', labelpad=2)
        sfig.set_ylabel('Relative variation in length (um/m)')
        sfig.set_title(PlotNames[index], loc='left')
        sfig.legend()
        sfig.grid()

def PlotVectors(CarthesianVectors, Magn, Angl, Errors, MaxValues):
    fig = plt.figure()
    fig.suptitle('Vectors')
    Plots = len(CarthesianVectors)
    Rows = 3
    Columns = int((Plots + 1) / Rows + 0.99)
    BaseValue = Columns * 100 + Rows * 10
    
    for index in range(Plots):
        PlotIndex = (BaseValue + index + 1)
        sfig = plt.subplot(PlotIndex)
        origin = [0,0]
        colors = ['r', 'g']
        for i in range(CarthesianVectors.shape[1]):
            X = CarthesianVectors[index, i, 0]
            Y = CarthesianVectors[index, i, 1]
            sfig.quiver(origin, origin, X, Y, color=colors[i], angles='xy', scale_units='xy', scale=1)
            
        sfig.set_xlim(-MaxValues[index], MaxValues[index])
        sfig.set_ylim(-MaxValues[index], MaxValues[index])
        sfig.legend(
            [
                'Real load: {}g @ {}°'.format(Magn[index, 0], Angl[index, 0]),
                'Calculated: {}g @ {}°'.format(Magn[index, 1], Angl[index, 1])
            ],
            loc='lower left'
        )
        # for i in range(X.size):
        #     sfig.vlines(X[i], 0, Y[i])
        #     sfig.hlines(Y[i], 0, X[i])
        sfig.grid()
        
        sfig.set_title(str(MaxValues[index]) + 'g')
        
    sfig = plt.subplot(BaseValue + Plots + 1)
    sfig.text(0, 0.5, 'Red = Real load (g)\nGreen = Calculated (g)')
    sfig.axis('off')

def CarthesianToPolar2D(carts: np.ndarray):
    if(carts.shape[1] != 2):
        raise ValueError('Input coordinate array has incorrect shape.')
    carts = np.reshape(carts, (carts.shape[0] * carts.shape[1], carts.shape[2]))
    set1, set2 = carts[:,0], carts[:,1]
    ph = np.array([set1 ** 2, set2 ** 2])
    ph2 = np.sum(ph, axis=0)
    Magn = np.sqrt(ph2)
    Angl = np.rad2deg(np.arccos(np.divide(set1, Magn)))
    # Polars = np.zeros((carts.shape[0], 2, 2))
    return np.reshape(Magn, (int(Magn.shape[0] / 2), 2)), np.reshape(Angl, (int(Angl.shape[0] / 2), 2))


AppliedLoads = np.array([624, 1124, 1624, 2124, 2624, 3124, 3624, 4124])

def Main():
    ColNames = []
    Data = []
    RelationX = None
    RelationY = None
    AverageXY = None
    csvs = FindCSV()
    for item in csvs:
        ColumnNames, Measurement = GetData(item)
        ColNames.append(ColumnNames)
        # Data.append(Measurement)
        if('XY' in item):
            AverageXY = CalculateAverages(Measurement)
            Data.append(AverageXY)
        elif('Y' in item):
            Average = CalculateAverages(Measurement)
            Data.append(Average)
            RelationY = CalculateRelations(Average, AppliedLoads)
        elif('X' in item):
            Average = CalculateAverages(Measurement)
            Data.append(Average)
            RelationX = CalculateRelations(Average, AppliedLoads)
    CalculatedForceVector = Calc2DForceVector(RelationX, RelationY, AverageXY[:,7])
    
    # Validate relations. Compare a known force vector to the calculated value
    # input parameters here
    angle = 45 # degrees
    # LoadIndex = 7 # which load is applied for reference, choose index from AppliedLoads array
    radians = np.deg2rad(angle)
    Errors = np.zeros((AverageXY.shape[1], 2))
    CarthesianVectors = np.zeros((AverageXY.shape[1], 2, 2))
    for LoadIndex in range(AverageXY.shape[1]):
        RealForceVector = [AppliedLoads[LoadIndex] * np.cos(radians), AppliedLoads[LoadIndex] * np.sin(radians)]
        CalculatedForceVector = Calc2DForceVector(RelationX, RelationY, AverageXY[:, LoadIndex])
        Errors[LoadIndex] = np.array([CalculatedForceVector[0] - RealForceVector[0], CalculatedForceVector[1] - RealForceVector[1]])
        CarthesianVectors[LoadIndex] = np.array([RealForceVector, CalculatedForceVector])
    Magn, Angl = CarthesianToPolar2D(CarthesianVectors)
    PlotVectors(CarthesianVectors, Magn, Angl, Errors, AppliedLoads)
    PlotAverages(Data, AppliedLoads, ColNames, csvs)

    plt.show()

if __name__ == '__main__':
    Main()
