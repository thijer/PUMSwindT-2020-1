import numpy as np
import matplotlib.pyplot as plt
import csv
import os
import glob
import scipy.signal as sp



ColNames = []
data = []

def FindCSV():
    files = os.listdir()
    return [name for name in files if name.endswith('.csv')]

def Main():
    csvs = FindCSV()
    for item in csvs:
        file = list(csv.reader(open(item, newline='')))
        ColNames.append(file[6][1:])
        ph = np.array(file[7:])[:,1:].astype(np.float)
        data.append(ph)
        
    Plots = len(data)
    Columns = 3
    Rows = int(Plots / Columns + 0.99)
    
    fig = plt.figure()
    fig.suptitle('Measurements')
    for index in range(Plots):
        PlotIndex = (Columns * 100 + Rows * 10 + index + 1)
        sfig = plt.subplot(PlotIndex)
        for i in range(data[index].shape[1]):
            sfig.plot(data[index][:,i], label=ColNames[index][i])
        sfig.set_ylabel('Relative stretch (um/m)')
        sfig.set_title(csvs[index])
        sfig.legend()
        sfig.grid()
    
    plt.show()
        

    
if __name__ == '__main__':
    Main()

