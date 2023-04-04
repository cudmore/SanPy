"""
This will generate a model, run it, and save a csv with (s, mV)

See:
https://github.com/MichaelClerx/myokit/blob/main/examples/1-1-simulating-an-action-potential.ipynb
"""
import numpy as np
import pandas as pd

import myokit
import myokit.lib.markov as markov

# modelFile = 'clancy-1999.mmt'
modelFile = "sanpy/models/tentusscher-2006.mmt"
model, protocol, script = myokit.load(modelFile)

print("protocol:", protocol)
"""
# Level  Start    Length   Period   Multiplier
1.0      50.0     0.5      1000.0   0
"""

# duration in ms
mySimDur = 30000

# create a new protocol
if 1:
    protocol = myokit.Protocol()

    level = 1.0
    duration = 0.5

    level = 0.5
    duration = 1.5

    # 0 is the mean of the normal distribution you are choosing from
    # 1 is the standard deviation of the normal distribution
    # 100 is the number of elements you get in array noise
    startTimes = np.linspace(0, mySimDur, 20)
    # startNoise = np.random.normal(0,1,20)
    startTimes = [x + abs(np.random.normal(500, 500, 1)) for x in startTimes]
    print("startTimes:", startTimes)
    for start in startTimes:
        protocol.schedule(level, start, duration, period=0, multiplier=0)


sim = myokit.Simulation(model, protocol)

# by default simulation run return variable time step
# this is not compatible with 'real- recordings
log_interval = 0.1  # default is None, units are ms ???
d = sim.run(mySimDur, log_interval=log_interval)

import matplotlib.pyplot as plt

plt.figure()
plt.plot(d["engine.time"], d["membrane.V"])
plt.show()

saveFile = "tentusscher.csv"
df = pd.DataFrame(columns=["s", "mV"])
timeSec = [x / 1000 for x in d["engine.time"]]

# TODO: Timesteps are not constant! This trips up my analysis
if 0:
    tmpDiff = np.diff(d["engine.time"])
    plt.plot(tmpDiff)
    plt.show()

df["s"] = timeSec
df["mV"] = d["membrane.V"]
print("saving:", saveFile)
print(df.head())
print(df.tail())
df.to_csv(saveFile, index=False)
