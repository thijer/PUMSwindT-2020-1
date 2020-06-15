import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatch
import csv
import os
import scipy.signal as sp
import re

# Settings
# Plot vector graphs with both the calculated vector and what the calculated vector should be
PLOTVECTORS = True
# plot the vectors for each load in AppliedLoads if true, otherwise the vector will be mean
PLOTVECTORDETAILS = True

# plot the graphs from the X and Y files
PLOTCHARACTERISTICS = False

# ONLYPLOTMEASUREMENTS = True
ONLYPLOTMEASUREMENTS = False
# plot filtered measurements
PLOTMEASURMENTS = True
# plot gradients (derivative) of the measurements
PLOTGRADIENTS = True
# Plot lines at the indices where the FindPeaks algorithm thinks a change in value starts and ends
PLOTHELPLINES = True

# Plot the average values for each load
PLOTAVERAGES = True

# The unit used in AppliedLoads. Can be mass (g, kg), force (N, Nm), or rabbits. For display only
LOADUNIT = 'Nm'

def Constrain(val, minv, maxv):
    return min(maxv, max(val, minv))

def FindPeaksV6(data: np.ndarray, Threshold, width=60):
    size = len(data)
    StartIndices = []
    EndIndices = []
    Gradients = np.gradient(data)
    FallingToggle = False
    RisingToggle = False
    Hysteresis = Threshold * 0.05
    for index in range(size - width):
        PeakArea = np.sum(Gradients[index:index + width])
        
        if(PeakArea > Threshold and not RisingToggle and not FallingToggle):
            # Start rising area
            StartIndices.append(index)
            RisingToggle = True
        elif(not PeakArea > Hysteresis and RisingToggle):
            #  End rising area
            EndIndices.append(index)
            RisingToggle = False
        if(PeakArea < -Threshold and not FallingToggle and not RisingToggle):
            # Start falling area
            StartIndices.append(index)
            FallingToggle = True
        elif(not PeakArea < -Hysteresis and FallingToggle):
            # End falling area
            EndIndices.append(index)
            FallingToggle = False
    return Gradients, np.array(StartIndices), np.array(EndIndices)

def ButterLowpass(data, cutoff, samplerate, order=5):
    nyq = 0.5 * samplerate
    normal_cutoff = cutoff / nyq
    b, a = sp.butter(order, normal_cutoff, btype='low', analog=False)
    return sp.filtfilt(b, a, data)

# load data from csv and filter
def GetData(file):
    data = list(csv.reader(open(file, newline='')))
    ph = data[6][1:]
    ColNames = []
    for ColumnName in ph:
        ColNames.append(ColumnName[2:-1])
    Names = {
        file: ColNames
    }
    Raw = np.array(data[7:])[:,1:].astype(np.float)
    
    # Number of colums in csv
    nColumns = Raw.shape[1]
    nRows = Raw.shape[0]
    Measurement = np.empty((nColumns, nRows))
    # Clean the data for noise at 0.8 Hz and higher
    for i in range(nColumns):
        ph = np.reshape(Raw[:,i], (nRows))
        Measurement[i] = ButterLowpass(ph, 0.8, 12.5, order=3)
    
    return Names, Measurement

def GetAverageIndices(Measurement):
    # Find highest value in measurements
    HighestIndex = np.where(Measurement == np.amax(Measurement))[0][0]
    
    Gradients, Start, End = FindPeaksV6(Measurement[HighestIndex], 13, width=50)
    # Start and End should be of the same length, and 8
    if(Start.size != End.size):
        raise ValueError
    # if(End.size != AppliedLoads.size * 2):
        # raise ValueError
    return Gradients, Start, End
    
def CalculateAveragesV2(Start, End, Measurement):
    if(Start.size != End.size):
        raise ValueError('arrays with peakindices are not equal to eachother: {} - {}'.format(Start.size, End.size))
    if(End.size > AppliedLoads.size * 2):
        raise ValueError('arrays with peakindices are not equal to 2 times the array containing the applied loads: {} - {}'.format(Start.size, AppliedLoads.size))
    
    nAverages = int(len(End) / 2)
    Averages = np.empty((Measurement.shape[0], nAverages))
    for Column in range(Measurement.shape[0]):
        avg = np.zeros(nAverages)
        for SectionIndex in range(0, len(End) - 1, 2):
            avg[int(SectionIndex / 2)] = np.average(Measurement[Column, End[SectionIndex]:Start[SectionIndex + 1]])
        # Calculate relation to load (um*m-1*g-1)
        Averages[Column] = avg
    return Averages

def CalculateAverages(Measurement):
    # Find highest value in measurements
    # HighestIndex = np.where(Measurement == np.amax(Measurement))[0]
    
    Start, End, Gradients = FindPeaksV6(Measurement[0], 13, width=50)
    # Start and End should be of the same length, and 8
    if(Start.size != End.size):
        raise ValueError
    # if(End.size != AppliedLoads.size * 2):
        # raise ValueError
    
    nAverages = int(len(End) / 2)
    Averages = np.empty((Measurement.shape[0], nAverages))
    for Column in range(Measurement.shape[0]):
        avg = np.zeros(nAverages)
        for SectionIndex in range(0, len(End) - 1, 2):
            avg[int(SectionIndex / 2)] = np.average(Measurement[Column, End[SectionIndex]:Start[SectionIndex + 1]])
        # Calculate relation to load (um*m-1*g-1)
        Averages[Column] = avg
    return Averages, Gradients, Start, End

def CalculateRelations(Averages, References):
    Relations = np.zeros(len(Averages))
    for i in range(len(Averages)):
        Relations[i] = np.average(np.divide(Averages[i], References))
    return Relations

def Calc2DForceVector(RelationX, RelationY, Measured):
    # use only 2 (x,y) of the three relations (x,y,z) for linear system solving
    a = np.array([[RelationX[0], RelationY[0]], [RelationX[1], RelationY[1]]])
    b = np.array([Measured[0], Measured[1]])
    vector = np.linalg.solve(a, b)
    return vector

def PlotMeasurements(Data, Names, Gradients=None, StartPeaks=None, EndPeaks=None):
    Plots = len(Data)
    Rows = Constrain(Plots, 0, 3)
    Columns = int((Plots) / Rows + 0.99)
    BaseValue = Rows * 100 + Columns * 10
    Toggle = True
    fig = plt.figure()
    fig.suptitle('Measurements')
    for index in range(Plots):
        PlotName = list(Names[index].keys())[0]
        ColNames = list(Names[index].values())[0]

        sfig = plt.subplot((BaseValue + index + 1))
        for i in range(Data[index].shape[0]):
            sfig.plot(Data[index][i], label=ColNames[i])
        
        if(PLOTGRADIENTS and Gradients != None):
            sfig.plot(Gradients[index], label='Gradients')
        
        if(PLOTHELPLINES and StartPeaks != None and EndPeaks != None):
            for peak in StartPeaks[index]:
                sfig.axvline(x=peak, color='g')
            for peak in EndPeaks[index]:
                sfig.axvline(x=peak, color='r')
        if(Toggle):
            sfig.set_ylabel('Relative stretch (um/m)')
            sfig.set_xlabel('Sample (12.5 Hz)', labelpad=2)
            sfig.legend()
            Toggle = False
        sfig.set_title(PlotName, loc='left')
        sfig.grid()

def PlotAverages(Data, Xaxis, Names):
    global LOADUNIT
    # HighestIndex = np.where(Measurement == np.amax(Measurement))[0]
    
    Plots = len(Data)
    Rows = min(len(Data), 3)
    Columns = int(Plots / Rows + 0.99)
    BaseValue = Rows * 100 + Columns * 10
    RoundedXAxis = np.round(Xaxis, 2)
    fig = plt.figure()
    fig.suptitle('Relation between load and change in length (um*m-1*{}-1), for each load applied to the blade'.format(LOADUNIT))
    for index in range(Plots):
        PlotName = list(Names[index].keys())[0]
        ColNames = list(Names[index].values())[0]
        
        # ph = np.amax(np.abs(Data[index]), axis=1)
        # First = np.argsort(ph)
        # colors = ['b', 'g', 'orange']
        PlotIndex = (BaseValue + index + 1)
        sfig = plt.subplot(PlotIndex)
        for i in range(Data[index].shape[0]):
            sfig.plot(RoundedXAxis.astype(np.str)[0:Data[index].shape[1]], Data[index][i], '.-', label=ColNames[i])
            # sfig.bar(Xaxis.astype(np.str), Data[index][First[-(i+1)]], label=ColNames[First[-(i+1)]], color=colors[First[-(i+1)]])
        sfig.set_xlabel('Applied load ({})'.format(LOADUNIT), labelpad=2)
        sfig.set_ylabel('Relative variation in length (um/m)')
        sfig.set_title(PlotName, loc='left')
        sfig.legend()
        sfig.grid()

def PlotVectors(RealPolarVectors, CalculatedPolarVectors, RealCarthesianVectors, CalculatedCarthesianVectors, References, Errors=None):
    global LOADUNIT
    fig = plt.figure()
    fig.suptitle('Calculated force vector vs applied force vector @ {}°'.format(RealPolarVectors[0, 1]))

    Plots = len(RealPolarVectors)
    Rows = int(np.sqrt(Plots) + 0.99)
    Columns = int((Plots) / Rows + 0.99)
    BaseValue = Columns * 100 + Rows * 10
    
    for index in range(Plots):
        PlotIndex = (BaseValue + index + 1)
        sfig = plt.subplot(PlotIndex)
        origin = [0,0]
        RealVector = sfig.quiver(origin, origin, RealCarthesianVectors[index, 0], RealCarthesianVectors[index, 1], color='r', angles='xy', scale_units='xy', scale=1)
        CalcVector = sfig.quiver(origin, origin, CalculatedCarthesianVectors[index, 0], CalculatedCarthesianVectors[index, 1], color='g', angles='xy', scale_units='xy', scale=1)
        ErrorEntry = mpatch.Patch()
        sfig.set_xlim(-References[index], References[index])
        sfig.set_ylim(-References[index], References[index])
        if(Errors is not None):
            sfig.legend(
                [
                    RealVector,
                    CalcVector,
                    ErrorEntry
                ],
                [
                    'Real load: {}{} @ {}°'.format(round(RealPolarVectors[index, 0], 2), LOADUNIT, RealPolarVectors[index, 1]),
                    'Calculated: {}{} @ {}°'.format(round(CalculatedPolarVectors[index, 0], 2), LOADUNIT, round(CalculatedPolarVectors[index, 1], 2)),
                    'Error: {}{} @ {}%'.format(round(Errors[index, 0], 2), '%', round(Errors[index, 1], 2))
                ],
                loc='lower left'
            )
        else:
            sfig.legend(
                [
                    'Real load: {}{} @ {}°'.format(RealPolarVectors[index, 0], LOADUNIT, RealPolarVectors[index, 1]),
                    'Calculated: {}{} @ {}°'.format(CalculatedPolarVectors[index, 0], LOADUNIT, CalculatedPolarVectors[index, 1])
                ],
                loc='lower left'
            )
        # for i in range(X.size):
        #     sfig.vlines(X[i], 0, Y[i])
        #     sfig.hlines(Y[i], 0, X[i])
        sfig.grid()
        sfig.set_title(str(round(References[index], 2)) + LOADUNIT, loc='left')
        sfig.set_xlabel('X component ({})'.format(LOADUNIT), labelpad=2)
        sfig.set_ylabel('Y component ({})'.format(LOADUNIT), labelpad=2)
        
        
    # sfig = plt.subplot(BaseValue + Plots + 1)
    # sfig.text(0, 0.5, 'Red = Real load ({})\nGreen = Calculated ({})'.format(LOADUNIT, LOADUNIT))
    # sfig.axis('off')

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

def CartToPolar(carts: np.ndarray):
    if(len(carts.shape) > 1):
        raise ValueError('Function expects array in shape (2), instead got array in shape {}'.format(carts.shape))
    # X = carts[0], Y = carts[2]
    Magn = np.sqrt(carts[0] ** 2 + carts[1] ** 2)
    Angl = (np.rad2deg(np.arctan2(carts[1], carts[0])) + 360) % 360
    return np.array([Magn, Angl])

# Array containing the mass values of the loads applied to the blade (g).
AppliedLoads = np.array([624, 1124, 1624, 2124, 2624, 3124, 3624, 4124])
# convert grams to newtonmeter at 1 meter grip distance
AppliedLoads = (AppliedLoads / 1000) * 9.807 * 1

def Main():
    print('Welcome to the plotter.')
    
    # Buffers containing all data for plotting purposes
    Names = []
    Measurements = []
    Averages = []
    Angles = []
    Gradients = []
    StartPeaks = []
    EndPeaks = []
    StartRisingPeaks = []
    EndRisingPeaks = []
    StartFallingPeaks = []
    EndFallingPeaks = []
    
    # Find csv files
    files = os.listdir()
    Xfiles = [name for name in files if re.match('X-DEG[0-9][0-9][0-9]\.csv', name)]
    Yfiles = [name for name in files if re.match('Y-DEG[0-9][0-9][0-9]\.csv', name)]
    Angles = [name for name in files if re.match('XY-DEG[0-9][0-9][0-9]-[0-9]\.csv', name)]
    
    # if(len(Xfiles) != 1 or len(Yfiles) != 1):
    #     raise Exception('Only 1 csv per pure X/Y behaviour is allowed')
    
    # Process X values (0/180°)
    # Only 1 csv file for pure 0° characteristics should be provided. This program will select the first and ignore the rest, regardless of quality
    Xfiles = Xfiles[0]
    NamesX, MeasurementX = GetData(Xfiles)
    # Find highest value in measurements
    HighestIndex = np.where(MeasurementX == np.amax(MeasurementX))[0][0]
    GradientX, StartX, EndX = FindPeaksV6(MeasurementX[HighestIndex], 16, width=40)
    
    if(not ONLYPLOTMEASUREMENTS):
        AverageX = CalculateAveragesV2(StartX, EndX, MeasurementX)
        RelationX = CalculateRelations(AverageX, AppliedLoads)
        if(PLOTCHARACTERISTICS): Averages.append(AverageX)
        del AverageX
    
    if(PLOTCHARACTERISTICS):
        # Add to plotbuffers
        Names.append(NamesX)
        Measurements.append(MeasurementX)
        Gradients.append(GradientX)
        StartPeaks.append(StartX)
        EndPeaks.append(EndX)
    # Free memory
    del MeasurementX, NamesX, GradientX, StartX, EndX

    # Process Y values (90/270°)
    # Only 1 csv file for pure 90° characteristics should be provided. This program will select the first and ignore the rest, regardless of quality
    Yfiles = Yfiles[0]
    NamesY, MeasurementY = GetData(Yfiles)
    HighestIndex = np.where(MeasurementY == np.amax(MeasurementY))[0][0]
    GradientY, StartY, EndY = FindPeaksV6(MeasurementY[HighestIndex], 13, width=40)
    if(not ONLYPLOTMEASUREMENTS):
        AverageY = CalculateAveragesV2(StartY, EndY, MeasurementY)
        RelationY = CalculateRelations(AverageY, AppliedLoads)
        if(PLOTCHARACTERISTICS): Averages.append(AverageY)
        del AverageY
    
    if(PLOTCHARACTERISTICS):
        # Add to plotbuffers
        Names.append(NamesY)
        Measurements.append(MeasurementY)
        Gradients.append(GradientY)
        StartPeaks.append(StartY)
        EndPeaks.append(EndY)
    # Free more memory
    del MeasurementY, NamesY, GradientY, StartY, EndY
    
    # Process all csvs which values are not at in X (0\180°) or Y (90/270°) direction.
    for item in Angles:
        # Get angle from filename
        Angle = float(item[6:-6])
        Radians = np.deg2rad(Angle)
        
        AngledNames, Measurement = GetData(item)
        HighestIndex = np.where(Measurement == np.amax(Measurement))[0][0]
        Gradient, Start, End = FindPeaksV6(Measurement[HighestIndex], 20, width=40)
        
        # add to plotbuffers
        Names.append(AngledNames)
        Measurements.append(Measurement)
        Gradients.append(Gradient)
        StartPeaks.append(Start)
        EndPeaks.append(End)

        if(not ONLYPLOTMEASUREMENTS):
            Average = CalculateAveragesV2(Start, End, Measurement)
            
            ERR = np.zeros((Average.shape[1], 2))
            RPV = np.zeros((Average.shape[1], 2)) # RealPolarVectors
            CPV = np.zeros((Average.shape[1], 2)) # CalculatedPolarVectors
            RCV = np.zeros((Average.shape[1], 2)) # RealCarthesianVectors
            CCV = np.zeros((Average.shape[1], 2)) # CalculatedCarthesianVectors
            
            # Calculate for each load in the AppliedLoads array the force vector
            for LoadIndex in range(Average.shape[1]):
                # transform known polar force vector (AppliedLoads[LoadIndex] @ Angle) to a carthesian vector (x,y)
                RCV[LoadIndex] = [AppliedLoads[LoadIndex] * np.cos(Radians), AppliedLoads[LoadIndex] * np.sin(Radians)]
                # Calculate force vector using the previously defined relations of X and Y, and the average values measured by the strain gages at a certain load
                CCV[LoadIndex] = Calc2DForceVector(RelationX, RelationY, Average[:, LoadIndex])
                
                # add both real and calculated polar force vectors to array
                CPV[LoadIndex] = CartToPolar(CCV[LoadIndex])
                RPV[LoadIndex] = np.array([AppliedLoads[LoadIndex], Angle])

                ERR[LoadIndex] = np.array([(CPV[LoadIndex, 0] / RPV[LoadIndex, 0]) * 100 - 100, (CPV[LoadIndex, 1] / RPV[LoadIndex, 1]) * 100 - 100])
                
            Averages.append(Average)
            
            if(PLOTVECTORS):
                if(PLOTVECTORDETAILS):
                    PlotVectors(RPV, CPV, RCV, CCV, AppliedLoads, ERR)
                
                else:
                    AL = np.reshape(AppliedLoads, (1, AppliedLoads.shape[0]))
                    
                    RPVA = np.mean(RPV, axis=0) # RealPolarVectors average
                    CPVA = np.mean(CPV, axis=0) # CalculatedPolarVectors average
                    RCVA = np.mean(RCV, axis=0) # RealCarthesianVectors average
                    CCVA = np.mean(CCV, axis=0) # CalculatedCarthesianVectors average
                    ALA = np.mean(AL, axis=1) # AL average
                    EA = np.mean(ERR, axis=0) # ERR average
                    
                    RPVA = np.reshape(RPVA, (1, RPVA.shape[0]))
                    CPVA = np.reshape(CPVA, (1, CPVA.shape[0]))
                    RCVA = np.reshape(RCVA, (1, RCVA.shape[0]))
                    CCVA = np.reshape(CCVA, (1, CCVA.shape[0]))
                    # ALA = np.reshape(ALA, (1, ALA.shape[0]))
                    EA = np.reshape(EA, (1, EA.shape[0]))
                    
                    PlotVectors(RPVA, CPVA, RCVA, CCVA, ALA, EA)
    if(PLOTMEASURMENTS):
        PlotMeasurements(Measurements, Names, Gradients, StartPeaks, EndPeaks)
    
    if(PLOTAVERAGES and not ONLYPLOTMEASUREMENTS):
        PlotAverages(Averages, AppliedLoads, Names)
    
    plt.show()

if __name__ == '__main__':
    Main()
