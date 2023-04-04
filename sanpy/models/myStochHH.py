"""
StochasticHH_ObjectOriented.py
Author: Alan Leggitt
5-11-2012

This code is a re-implementation of Matlab code written by Joshua Goldwyn. The original Matlab code can be found at
http://faculty.washington.edu/etsb/tutorials.html

This version runs best using the Enthought Python Distribution 7.2
www.enthought.com

For more information, contact Alan Leggitt at alan.leggitt@ucsf.edu

see:
    https://senselab.med.yale.edu/modeldb/showModel.cshtml?model=144499&file=/StochasticHH/README.html
"""

# from __future__ import division
from datetime import datetime
from numpy import *
from pylab import *
from scipy import linalg

import pandas as pd

# Define global variables
C = 1  # Capacitance (muF /cm**2)
gNa = 120  # Maximimal Na conductance (mS/cm**2)
ENa = 120  # Na reversal potential (mV)
gK = 36  # Maximal K conductance (mS/cm**2)
EK = -12  # K reversal potential (mV)
gL = 0.3  # Leak conductance (mS/cm**2)
EL = 10.6  # Leak reversal potential (mV)

#
# gNa = 120 # Maximimal Na conductance (mS/cm**2)
# gK = 30


class Neuron(object):
    """
    A class for modeling a neuron using the Hodgkin Huxely model and adding noise terms

    Parameters
    ----------
    timeArray - array of times
    inputCurrent - an array of input current values, must be the same length as time
    noiseSTD - the standard deviation of the noise
    area - the area of the neuron
    noiseModel - model for the input noise
        ODE - no input noise
        Current - noise added to current input
        Subunit - noise added to subunit variables
        VClamp - voltage clamp conductance noise, Linaro et al model
        FoxLuSystemSize - system size conductance noise, Fox and Lu model
        MarkovChain - Markov Chain model

    Functions
    ---------
    solveStochasticModel - solve the Hodgkin Huxley model using the noise model
    plotVoltage - plot the voltage vs. time
    plotChannelFractions - plot fractions of both ion channel types vs. time

    """

    def __init__(
        self,
        timeArray=None,
        inputCurrent=None,
        area=None,
        noiseSTD=None,
        noiseModel=None,
    ):
        # Set default values
        if timeArray is None:
            print("Using default time vector")
            timeArray = arange(0, 100.01, 0.01)
        if inputCurrent is None:
            print("Using default input current")
            inputCurrent = zeros(len(timeArray))
            for i, t in enumerate(timeArray):
                if 5 <= t <= 15:
                    inputCurrent[i] = 10  # uA/cm2
        if area is None:
            print("Using default area")
            area = 100
        if noiseSTD is None:
            print("Using default noise standard deviation")
            noiseSTD = 10
        if noiseModel is None:
            print("Using no noise model")
            noiseModel = "ODE"
        # Store data as class attributes
        self.timeArray = timeArray
        self.inputCurrent = inputCurrent
        self.area = area
        self.noiseSTD = noiseSTD
        self.noiseModel = noiseModel

    def __call__(self):
        self.solveStochasticModel()
        self.plotVoltage()
        self.plotChannelFractions()

    def solveStochasticModel(self, gK=36):
        # Unload inputs from class attributes
        t = self.timeArray
        inputCurrent = self.inputCurrent
        area = self.area
        noiseSTD = self.noiseSTD
        noiseModel = self.noiseModel

        # Initialize quantities needed to run solver
        dt = t[1] - t[0]  # time step size
        nt = len(t)  # total number of time steps
        nt1 = nt - 1  # at which to solve

        # Initialize output arrays
        voltageArray = zeros((nt))
        NaFractionArray = zeros((nt))
        KFractionArray = zeros((nt))
        mSubunitArray = zeros((nt))
        hSubunitArray = zeros((nt))
        nSubunitArray = zeros((nt))
        NaFluctuationArray = zeros((nt))
        KFluctuationArray = zeros((nt))

        # Initial Values
        t0 = t[0]  # time
        V = voltageArray[0]  # voltage
        m = alpham(V) / (alpham(V) + betam(V))  # m subunit
        h = alphah(V) / (alphah(V) + betah(V))  # h subunit
        n = alphan(V) / (alphan(V) + betan(V))  # n subunit
        NaFraction = m**3 * h  # fraction of open Na channels
        KFraction = n**4  # fraction of open K channels
        NNa = round(area * 60)  # number of Na channels
        NK = round(area * 18)  # number of K channels

        # Determine Which Noise Model and Do Some Necessary Setup
        if noiseModel == "Current":  # Current noise
            VNoise = noiseSTD * randn(nt1)
        else:
            VNoise = zeros((nt1))

        # Subunit Noise (FL Model)
        if noiseModel == "Subunit":
            # Imposing bounds on argument of sqrt functions, not directly altering dynamics of the subunits
            mNoise = (
                lambda V, m: sqrt((alpham(V) * (1 - m) + betam(V) * m) / NNa) * randn()
            )
            hNoise = (
                lambda V, h: sqrt((alphah(V) * (1 - h) + betah(V) * h) / NNa) * randn()
            )
            nNoise = (
                lambda V, n: sqrt((alphan(V) * (1 - n) + betan(V) * n) / NK) * randn()
            )
        else:
            mNoise = lambda V, m: 0
            hNoise = lambda V, h: 0
            nNoise = lambda V, n: 0

        # Conductance Noise (Linaro et al Voltage Clamp)
        if noiseModel == "VClamp":
            ConductanceNoise = 1
            NaWeiner = randn(nt1, 7)
            KWeiner = randn(nt1, 4)
            NaNoise = 0  # Initialize
            KNoise = 0  # Initialize
            taum = lambda V: 1 / (alpham(V) + betam(V))
            tauh = lambda V: 1 / (alphah(V) + betah(V))
            denomNa = (
                lambda V: NNa
                * (alphah(V) + betah(V)) ** 2
                * (alpham(V) + betam(V)) ** 6
            )
            TauNa = lambda V: array(
                (
                    taum(V),
                    taum(V) / 2,
                    taum(V) / 3,
                    tauh(V),
                    taum(V) * tauh(V) / (taum(V) + tauh(V)),
                    taum(V) * tauh(V) / (taum(V) + 2 * tauh(V)),
                    taum(V) * tauh(V) / (taum(V) + 3 * tauh(V)),
                )
            )
            CovNa = lambda V: array(
                (
                    3 * alphah(V) ** 2 * alpham(V) ** 5 * betam(V),
                    3 * alphah(V) ** 2 * alpham(V) ** 4 * betam(V) ** 2,
                    alphah(V) ** 2 * alpham(V) ** 3 * betam(V) ** 3,
                    alphah(V) * betah(V) * alpham(V) ** 6,
                    3 * alphah(V) * betah(V) * alpham(V) ** 5 * betam(V),
                    3 * alphah(V) * betah(V) * alpham(V) ** 4 * betam(V) ** 2,
                    alphah(V) * betah(V) * alpham(V) ** 3 * betam(V) ** 3,
                )
            ) / denomNa(V)
            taun = lambda V: 1 / (alphan(V) + betan(V))
            TauK = lambda V: taun(V) / array((1, 2, 3, 4))
            CovK = lambda V: array(
                (
                    4 * alphan(V) ** 7 * betan(V),
                    4 * alphan(V) ** 6 * betan(V) ** 2,
                    4 * alphan(V) ** 5 * betan(V) ** 3,
                    4 * alphan(V) ** 4 * betan(V) ** 4,
                )
            ) / (NK * (alphan(V) + betan(V)) ** 8)

            SigmaNa = lambda V: sqrt(2 * CovNa(V) / TauNa(V))
            SigmaK = lambda V: sqrt(2 * CovK(V) / TauK(V))

        # Conductance Noise (FL Channel Model)
        if noiseModel == "FoxLuSystemSize":
            NaHat = zeros((8))  # Initial values set to 0
            KHat = zeros((5))  # Initial values set to 0
            NaNoise = randn(8, nt1)
            KNoise = randn(5, nt1)

            # Drift Na
            ANa = lambda V: array(
                (
                    (-3 * alpham(V) - alphah(V), betam(V), 0, 0, betah(V), 0, 0, 0),
                    (
                        3 * alpham(V),
                        -2 * alpham(V) - betam(V) - alphah(V),
                        2 * betam(V),
                        0,
                        0,
                        betah(V),
                        0,
                        0,
                    ),
                    (
                        0,
                        2 * alpham(V),
                        -alpham(V) - 2 * betam(V) - alphah(V),
                        3 * betam(V),
                        0,
                        0,
                        betah(V),
                        0,
                    ),
                    (0, 0, alpham(V), -3 * betam(V) - alphah(V), 0, 0, 0, betah(V)),
                    (alphah(V), 0, 0, 0, -3 * alpham(V) - betah(V), betam(V), 0, 0),
                    (
                        0,
                        alphah(V),
                        0,
                        0,
                        3 * alpham(V),
                        -2 * alpham(V) - betam(V) - betah(V),
                        2 * betam(V),
                        0,
                    ),
                    (
                        0,
                        0,
                        alphah(V),
                        0,
                        0,
                        2 * alpham(V),
                        -alpham(V) - 2 * betam(V) - betah(V),
                        3 * betam(V),
                    ),
                    (0, 0, 0, alphah(V), 0, 0, alpham(V), -3 * betam(V) - betah(V)),
                )
            )

            # Drift K
            AK = lambda V: array(
                (
                    (-4 * alphan(V), betan(V), 0, 0, 0),
                    (4 * alphan(V), -3 * alphan(V) - betan(V), 0, 0, 0),
                    (0, 3 * alphan(V), -2 * alphan(V) - 2 * betan(V), 3 * betan(V), 0),
                    (0, 0, 2 * alphan(V), -alphan(V) - 3 * betan(V), 4 * betan(V)),
                    (0, 0, 0, alphan(V), -4 * betan(V)),
                )
            )

            # Diffusion Na : Defined in a function below

            # Diffusion K
            def DK(V, X):
                return (
                    1
                    / NK
                    * array(
                        (
                            (
                                4 * alphan(V) * X[0] + betan(V) * X[1],
                                -(4 * alphan(V) * X[0] + betan(V) * X[1]),
                                0,
                                0,
                                0,
                            ),
                            (
                                -(4 * alphan(V) * X[0] + betan(V) * X[1]),
                                (
                                    4 * alphan(V) * X[1]
                                    + (3 * alphan(V) + betan(V)) * X[1]
                                    + 2 * betan(V) * X[2]
                                ),
                                -(2 * betan(V) * X[2] + 3 * alphan(V) * X[1]),
                                0,
                                0,
                            ),
                            (
                                0,
                                -(2 * betan(V) * X[2] + 3 * alphan(V) * X[1]),
                                (
                                    3 * alphan(V) * X[1]
                                    + (2 * alphan(V) + 2 * betan(V)) * X[2]
                                    + 3 * betan(V) * X[3]
                                ),
                                -(3 * betan(V) * X[3] + 2 * alphan(V) * X[2]),
                                0,
                            ),
                            (
                                0,
                                0,
                                -(3 * betan(V) * X[3] + 2 * alphan(V) * X[2]),
                                (
                                    2 * alphan(V) * X[2]
                                    + (alphan(V) + 3 * betan(V)) * X[3]
                                    + 4 * betan(V) * X[4]
                                ),
                                -(4 * betan(V) * X[4] + alphan(V) * X[3]),
                            ),
                            (
                                0,
                                0,
                                0,
                                -(4 * betan(V) * X[4] + alphan(V) * X[3]),
                                (alphan(V) * X[3] + 4 * betan(V) * X[4]),
                            ),
                        )
                    )
                )

            # Take Matrix square roots numerically using SVD
            SNa = lambda V, Y, NNa: mysqrtm(DNa(V, Y, NNa))
            SK = lambda V, X: mysqrtm(DK(V, X))

        # Markov chain
        if noiseModel == "MarkovChain":
            MCNa = zeros((4, 2))
            # Initialize channel states
            MCNa[0, 0] = floor(NNa * (1 - m) ** 3 * (1 - h))
            MCNa[1, 0] = floor(NNa * 3 * (1 - m) ** 2 * m * (1 - h))
            MCNa[2, 0] = floor(NNa * 3 * (1 - m) ** 1 * m**2 * (1 - h))
            MCNa[3, 0] = floor(NNa * (1 - m) * m**3 * (1 - h))
            MCNa[0, 1] = floor(NNa * (1 - m) ** 3 * (h))
            MCNa[1, 1] = floor(NNa * 3 * (1 - m) ** 2 * m * (h))
            MCNa[2, 1] = floor(NNa * 3 * (1 - m) ** 1 * m**2 * (h))
            MCNa[3, 1] = NNa - sum(sum(MCNa))
            MCK = zeros(5)
            MCK[0] = floor(NK * (1 - n) ** 4)
            MCK[1] = floor(NK * 4 * n * (1 - n) ** 3)
            MCK[2] = floor(NK * 6 * n**2 * (1 - n) ** 2)
            MCK[3] = floor(NK * 4 * n**3 * (1 - n))
            MCK[4] = NK - sum(MCK)

        """
        HERE IS THE SOLVER
        USING EULER FOR ODEs,
        EULER-MARUYAMA FOR SDEs,
        and GILLESPIE FOR MARKOV CHAIN
        """

        for i in range(1, nt):
            # Input Current
            I = inputCurrent[i - 1]

            # Update subunits
            # Noise terms are non-zero for Subunit Noise model
            m += dt * (alpham(V) * (1 - m) - betam(V) * m) + mNoise(V, m) * sqrt(
                dt
            )  # shifted to i-1 in function
            h += dt * (alphah(V) * (1 - h) - betah(V) * h) + hNoise(V, h) * sqrt(dt)
            n += dt * (alphan(V) * (1 - n) - betan(V) * n) + nNoise(V, n) * sqrt(dt)

            # Enforce boundary conditions (only necessary for subunit noise model)
            m = max(0, min(1, m))
            h = max(0, min(1, h))
            n = max(0, min(1, n))

            # Update Fluctuations if using conductance noise model
            if noiseModel == "VClamp":  # Voltage Clamp (Linaro et al)
                NaNoise = (
                    NaNoise
                    + dt * (-NaNoise / TauNa(V))
                    + sqrt(dt) * (SigmaNa(V) * NaWeiner[i - 1, :])
                )
                KNoise = (
                    KNoise
                    + dt * (-KNoise / TauK(V))
                    + sqrt(dt) * (SigmaK(V) * KWeiner[i - 1, :])
                )
                NaFluctuation = sum(NaNoise)
                KFluctuation = sum(KNoise)
            elif noiseModel == "FoxLuSystemSize":  # System Size (Fox and Lu)
                NaBar = array(
                    (
                        (1 - m) ** 3 * (1 - h),
                        3 * (1 - m) ** 2 * m * (1 - h),
                        3 * (1 - m) * m**2 * (1 - h),
                        m**3 * (1 - h),
                        (1 - m) ** 3 * h,
                        3 * (1 - m) ** 2 * m * h,
                        3 * (1 - m) * m**2 * h,
                        m**3 * h,
                    )
                )
                KBar = array(
                    (
                        (1 - n) ** 4,
                        4 * n * (1 - n) ** 3,
                        6 * n**2 * (1 - n) ** 2,
                        4 * n**3 * (1 - n),
                        n**4,
                    )
                )
                NaHat += dt * dot(ANa(V), NaHat) + sqrt(dt) * dot(
                    SNa(V, NaBar, NNa), NaNoise[:, i - 1]
                )
                KHat += dt * dot(AK(V), KHat) + sqrt(dt) * dot(
                    SK(V, KBar), KNoise[:, i - 1]
                )
                NaFluctuation = NaHat[-1]
                KFluctuation = KHat[-1]

            else:
                NaFluctuation = 0
                KFluctuation = 0

            # Compute Fraction of open channels
            if noiseModel == "MarkovChain":
                MCNa, MCK = MarkovChainFraction(V, MCNa, MCK, t0, dt)
                NaFraction = MCNa[3, 1] / NNa
                KFraction = MCK[4] / NK
            else:
                # Note: Impose bounds on fractions to avoid <0 or >1 in dV/dt equation, this doesn't directly alter the dynamics of the subunits or channels
                NaFraction = max(
                    0, min(append(m**3 * h + NaFluctuation, 1))
                )  # Fluctuations are non-zero for Conductance Noise Models
                KFraction = max(0, min(append(n**4 + KFluctuation, 1)))

            # Update Voltage
            Vrhs = (
                -gNa * (NaFraction) * (V - ENa)
                - gK * (KFraction) * (V - EK)
                - gL * (V - EL)
                + I
            ) / C
            V += (
                dt * Vrhs + sqrt(dt) * VNoise[i - 1] / C
            )  # VNoise is non-zero for Current Noise Model

            # Save Outputs
            voltageArray[i] = V
            NaFractionArray[i] = NaFraction
            KFractionArray[i] = KFraction
            mSubunitArray[i] = m
            hSubunitArray[i] = h
            nSubunitArray[i] = n
            NaFluctuationArray[i] = NaFluctuation
            KFluctuationArray[i] = KFluctuation

        # End loop over time for SDE solver
        self.voltageArray = voltageArray
        self.NaFractionArray = NaFractionArray
        self.KFractionArray = KFractionArray
        self.mSubunitArray = mSubunitArray
        self.nSubunitArray = nSubunitArray
        self.NaFluctuationArray = NaFluctuationArray
        self.KFluctuationArray = KFluctuationArray

    def plotVoltage(self, ax=None, lineStyle="k"):
        t = self.timeArray
        V = self.voltageArray
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.set_xlabel("Time (ms)")
            ax.set_ylabel("Voltage (mV)")

        ax.plot(t, V, lineStyle)
        show()

    def plotChannelFractions(self, ax=None, NaLineStyle="b", KLineStyle="g"):
        t = self.timeArray
        Na = self.NaFractionArray
        K = self.KFractionArray
        if ax is None:
            fig = plt.figure()
            ax = fig.add_subplot(111)
            ax.set_xlabel("Time (ms)")
            ax.set_ylabel("Mean Open Fraction")
        ax.plot(t, Na, NaLineStyle)
        ax.plot(t, K, KLineStyle)
        show()


"""

Define the helper functions used in code
-----------------------------
Subunit kinetics (Hodgkin and Huxley parameters)

"""


def alpham(V):
    out = 0.1 * (25 - V) / (exp((25 - V) / 10) - 1)
    return out


def betam(V):
    out = 4 * exp(-V / 18)
    return out


def alphah(V):
    out = 0.07 * exp(-V / 20)
    return out


def betah(V):
    out = 1 / (exp((30 - V) / 10) + 1)
    return out


def alphan(V):
    out = 0.01 * (10 - V) / (exp((10 - V) / 10) - 1)
    return out


def betan(V):
    out = 0.125 * exp(-V / 80)
    return out


# Computing matrix square roots with SVD
def mysqrtm(D):
    u, s, v = linalg.svd(D)
    S = u * sqrt(s) * v
    return S


# Diffusion matrix for Na
def DNa(V, Y, N):
    D = zeros((8, 8))
    y00 = Y[0]
    y10 = Y[1]
    y20 = Y[2]
    y30 = Y[3]
    y01 = Y[4]
    y11 = Y[5]
    y21 = Y[6]
    y31 = Y[7]

    D[0, 0] = (3 * alpham(V) + alphah(V)) * y00 + betam(V) * y10 + betah(V) * y01
    D[0, 1] = -3 * alpham(V) * y00 - betam(V) * y10
    D[0, 2] = 0
    D[0, 3] = 0
    D[0, 4] = -(alphah(V) * y00 + betah(V) * y01)
    D[0, 5] = 0
    D[0, 6] = 0
    D[0, 7] = 0

    D[1, 0] = D[0, 1]
    D[1, 1] = (
        (betam(V) + 2 * alpham(V)) * y10
        + 2 * betam(V) * y20
        + 3 * alpham(V) * y00
        + alphah(V) * y10
        + betah(V) * y11
    )
    D[1, 2] = -(2 * alpham(V) * y10 + 2 * betam(V) * y20)
    D[1, 3] = 0
    D[1, 4] = 0
    D[1, 5] = -(alphah(V) * y10 + betah(V) * y11)
    D[1, 6] = 0
    D[1, 7] = 0

    D[2, 0] = D[0, 2]
    D[2, 1] = D[1, 2]
    D[2, 2] = (
        (2 * betam(V) + alpham(V)) * y20
        + 3 * betam(V) * y30
        + 2 * alpham(V) * y10
        + alphah(V) * y20
        + betah(V) * y21
    )
    D[2, 3] = -(alpham(V) * y20 + 3 * betam(V) * y30)
    D[2, 4] = 0
    D[2, 5] = 0
    D[2, 6] = -(alphah(V) * y20 + betah(V) * y21)
    D[2, 7] = 0

    D[3, 0] = D[0, 3]
    D[3, 1] = D[1, 3]
    D[3, 2] = D[2, 3]
    D[3, 3] = 3 * betam(V) * y30 + alpham(V) * y20 + alphah(V) * y30 + betah(V) * y31
    D[3, 4] = 0
    D[3, 5] = 0
    D[3, 6] = 0
    D[3, 7] = -(alphah(V) * y30 + betah(V) * y31)

    D[4, 0] = D[0, 4]
    D[4, 1] = D[1, 4]
    D[4, 2] = D[2, 4]
    D[4, 3] = D[3, 4]
    D[4, 4] = 3 * alpham(V) * y01 + betam(V) * y11 + betah(V) * y01 + alphah(V) * y00
    D[4, 5] = -(3 * alpham(V) * y01 + betam(V) * y11)
    D[4, 6] = 0
    D[4, 7] = 0

    D[5, 0] = D[0, 5]
    D[5, 1] = D[1, 5]
    D[5, 2] = D[2, 5]
    D[5, 3] = D[3, 5]
    D[5, 4] = D[4, 5]
    D[5, 5] = (
        (betam(V) + 2 * alpham(V)) * y11
        + 2 * betam(V) * y21
        + 3 * alpham(V) * y01
        + betah(V) * y11
        + alphah(V) * y10
    )
    D[5, 6] = -(2 * alpham(V) * y11 + 2 * betam(V) * y21)
    D[5, 7] = 0

    D[6, 0] = D[0, 6]
    D[6, 1] = D[1, 6]
    D[6, 2] = D[2, 6]
    D[6, 3] = D[3, 6]
    D[6, 4] = D[4, 6]
    D[6, 5] = D[5, 6]
    D[6, 6] = (
        (2 * betam(V) + alpham(V)) * y21
        + 3 * betam(V) * y31
        + 2 * alpham(V) * y11
        + betah(V) * y21
        + alphah(V) * y20
    )
    D[6, 7] = -(alpham(V) * y21 + 3 * betam(V) * y31)

    D[7, 0] = D[0, 7]
    D[7, 1] = D[1, 7]
    D[7, 2] = D[2, 7]
    D[7, 3] = D[3, 7]
    D[7, 4] = D[4, 7]
    D[7, 5] = D[5, 7]
    D[7, 6] = D[6, 7]
    D[7, 7] = 3 * betam(V) * y31 + alpham(V) * y21 + betah(V) * y31 + alphah(V) * y30

    D = D / (N)
    return D


# Markov chain
def MarkovChainFraction(V, NaStateIn, KStateIn, t, dt):
    tswitch = t
    Nastate = NaStateIn
    Kstate = KStateIn
    # Update Channel States
    while tswitch < (t + dt):
        rate = zeros((28))
        # Determine which state switches by partitioning total rate into its 28 components
        rate[0] = 3 * alpham(V) * Nastate[0, 0]
        rate[1] = rate[0] + 2 * alpham(V) * Nastate[1, 0]
        rate[2] = rate[1] + 1 * alpham(V) * Nastate[2, 0]
        rate[3] = rate[2] + 3 * betam(V) * Nastate[3, 0]
        rate[4] = rate[3] + 2 * betam(V) * Nastate[2, 0]
        rate[5] = rate[4] + 1 * betam(V) * Nastate[1, 0]
        rate[6] = rate[5] + alphah(V) * Nastate[0, 0]
        rate[7] = rate[6] + alphah(V) * Nastate[1, 0]
        rate[8] = rate[7] + alphah(V) * Nastate[2, 0]
        rate[9] = rate[8] + alphah(V) * Nastate[3, 0]
        rate[10] = rate[9] + betah(V) * Nastate[0, 1]
        rate[11] = rate[10] + betah(V) * Nastate[1, 1]
        rate[12] = rate[11] + betah(V) * Nastate[2, 1]
        rate[13] = rate[12] + betah(V) * Nastate[3, 1]
        rate[14] = rate[13] + 3 * alpham(V) * Nastate[0, 1]
        rate[15] = rate[14] + 2 * alpham(V) * Nastate[1, 1]
        rate[16] = rate[15] + 1 * alpham(V) * Nastate[2, 1]
        rate[17] = rate[16] + 3 * betam(V) * Nastate[3, 1]
        rate[18] = rate[17] + 2 * betam(V) * Nastate[2, 1]
        rate[19] = rate[18] + 1 * betam(V) * Nastate[1, 1]
        rate[20] = rate[19] + 4 * alphan(V) * Kstate[0]
        rate[21] = rate[20] + 3 * alphan(V) * Kstate[1]
        rate[22] = rate[21] + 2 * alphan(V) * Kstate[2]
        rate[23] = rate[22] + 1 * alphan(V) * Kstate[3]
        rate[24] = rate[23] + 4 * betan(V) * Kstate[4]
        rate[25] = rate[24] + 3 * betan(V) * Kstate[3]
        rate[26] = rate[25] + 2 * betan(V) * Kstate[2]
        rate[27] = rate[26] + 1 * betan(V) * Kstate[1]

        # Total Transition Rate
        totalrate = rate[27]

        # Exponential Waiting Time Distribution
        tupdate = -log(rand()) / totalrate

        # Time of Next Switching Event (Exp Rand Var)
        tswitch = tswitch + tupdate

        if tswitch < (t + dt):
            # Scaled Uniform RV to determine which state to switch
            r = totalrate * rand()

            if r < rate[0]:
                Nastate[0, 0] = Nastate[0, 0] - 1
                Nastate[1, 0] = Nastate[1, 0] + 1
            elif r < rate[1]:
                Nastate[1, 0] = Nastate[1, 0] - 1
                Nastate[2, 0] = Nastate[2, 0] + 1
            elif r < rate[2]:
                Nastate[2, 0] = Nastate[2, 0] - 1
                Nastate[3, 0] = Nastate[3, 0] + 1
            elif r < rate[3]:
                Nastate[3, 0] = Nastate[3, 0] - 1
                Nastate[2, 0] = Nastate[2, 0] + 1
            elif r < rate[4]:
                Nastate[2, 0] = Nastate[2, 0] - 1
                Nastate[1, 0] = Nastate[1, 0] + 1
            elif r < rate[5]:
                Nastate[1, 0] = Nastate[1, 0] - 1
                Nastate[0, 0] = Nastate[0, 0] + 1
            elif r < rate[6]:
                Nastate[0, 0] = Nastate[0, 0] - 1
                Nastate[0, 1] = Nastate[0, 1] + 1
            elif r < rate[7]:
                Nastate[1, 0] = Nastate[1, 0] - 1
                Nastate[1, 1] = Nastate[1, 1] + 1
            elif r < rate[8]:
                Nastate[2, 0] = Nastate[2, 0] - 1
                Nastate[2, 1] = Nastate[2, 1] + 1
            elif r < rate[9]:
                Nastate[3, 0] = Nastate[3, 0] - 1
                Nastate[3, 1] = Nastate[3, 1] + 1
            elif r < rate[10]:
                Nastate[0, 1] = Nastate[0, 1] - 1
                Nastate[0, 0] = Nastate[0, 0] + 1
            elif r < rate[11]:
                Nastate[1, 1] = Nastate[1, 1] - 1
                Nastate[1, 0] = Nastate[1, 0] + 1
            elif r < rate[12]:
                Nastate[2, 1] = Nastate[2, 1] - 1
                Nastate[2, 0] = Nastate[2, 0] + 1
            elif r < rate[13]:
                Nastate[3, 1] = Nastate[3, 1] - 1
                Nastate[3, 0] = Nastate[3, 0] + 1
            elif r < rate[14]:
                Nastate[0, 1] = Nastate[0, 1] - 1
                Nastate[1, 1] = Nastate[1, 1] + 1
            elif r < rate[15]:
                Nastate[1, 1] = Nastate[1, 1] - 1
                Nastate[2, 1] = Nastate[2, 1] + 1
            elif r < rate[16]:
                Nastate[2, 1] = Nastate[2, 1] - 1
                Nastate[3, 1] = Nastate[3, 1] + 1
            elif r < rate[17]:
                Nastate[3, 1] = Nastate[3, 1] - 1
                Nastate[2, 1] = Nastate[2, 1] + 1
            elif r < rate[18]:
                Nastate[2, 1] = Nastate[2, 1] - 1
                Nastate[1, 1] = Nastate[1, 1] + 1
            elif r < rate[19]:
                Nastate[1, 1] = Nastate[1, 1] - 1
                Nastate[0, 1] = Nastate[0, 1] + 1
            elif r < rate[20]:
                Kstate[0] = Kstate[0] - 1
                Kstate[1] = Kstate[1] + 1
            elif r < rate[21]:
                Kstate[1] = Kstate[1] - 1
                Kstate[2] = Kstate[2] + 1
            elif r < rate[22]:
                Kstate[2] = Kstate[2] - 1
                Kstate[3] = Kstate[3] + 1
            elif r < rate[23]:
                Kstate[3] = Kstate[3] - 1
                Kstate[4] = Kstate[4] + 1
            elif r < rate[24]:
                Kstate[4] = Kstate[4] - 1
                Kstate[3] = Kstate[3] + 1
            elif r < rate[25]:
                Kstate[3] = Kstate[3] - 1
                Kstate[2] = Kstate[2] + 1
            elif r < rate[26]:
                Kstate[2] = Kstate[2] - 1
                Kstate[1] = Kstate[1] + 1
            else:
                Kstate[1] = Kstate[1] - 1
                Kstate[0] = Kstate[0] + 1

    NaStateOut = Nastate
    KStateOut = Kstate

    return NaStateOut, KStateOut


"""
End of helper function definitions
"""


def myRun2(durSec=10, amp=8, baseLineShift=-60, fs=10000, doPlot=False, gK=36):
    """
    amp (float): uA/cm2
    """

    print("  gK:", gK)
    durMs = durSec * 1000
    durMs += 0.01
    stepMs = 1 / fs * 1000 / 10  # TODO: fix trailing '/ 10'
    print(
        f"myRun2() durSec:{durSec} amp:{amp} baseLineShift:{baseLineShift} durMs:{durMs} stepMs:{stepMs}"
    )
    timeArray = arange(0, durMs, stepMs)
    inputCurrent = zeros(len(timeArray))
    startStepMs = 20
    stopStepMs = durMs - 20
    for i, t in enumerate(timeArray):
        if startStepMs <= t <= stopStepMs:
            inputCurrent[i] = amp  # 10 # uA/cm2

    noiseModel = "Subunit"  # []'Subunit', None]
    n = Neuron(timeArray=timeArray, inputCurrent=inputCurrent, noiseModel=noiseModel)
    n.solveStochasticModel(gK=gK)  # gK in [36, 30]
    n.voltageArray -= baseLineShift

    if doPlot:
        n.plotVoltage()

    return n.timeArray, n.inputCurrent, n.voltageArray


def myRun(doPlot=True):
    # added by robert cudmore, abb
    durMs = 500.01  # 100.01
    stepMs = 0.01
    print(f"myRun() durMs:{durMs} stepMs:{stepMs}")
    timeArray = arange(0, durMs, stepMs)
    inputCurrent = zeros(len(timeArray))
    startStepMs = 20
    stopStepMs = durMs - 20
    for i, t in enumerate(timeArray):
        if startStepMs <= t <= stopStepMs:
            inputCurrent[i] = 8  # 10 # uA/cm2

    n = Neuron(timeArray=timeArray, inputCurrent=inputCurrent, noiseModel="Subunit")
    # n()
    n.solveStochasticModel()
    n.voltageArray -= 60

    n.plotVoltage()
    # n.plotChannelFractions()

    """
    import pandas as pd
    outFile = 'hh1.csv'
    df = pd.DataFrame(columns=['s', 'mV'])
    df['s'] = n.timeArray / 1000
    df['mV'] = n.voltageArray
    print('saving outFile:', outFile)
    df.to_csv(outFile, index=False)
    """


if __name__ == "__main__":
    # works
    # myRun(doPlot=True)

    # amp 5, gK2 28
    gK1 = 36
    gK2 = 30  # 31  # 32  # 12
    amp = 4  # 5 is good # 7

    now = datetime.datetime.now()
    dateStr = now.strftime("%Y%m%d")
    timeStr = now.strftime("%H%M%S")
    saveFile = f"/Users/cudmore/Desktop/sanpy-model-data/stoch-hh-gk-{dateStr}-{timeStr}-{gK1}-{gK2}.csv"

    durSec = 1
    doPlot = False

    # run 1
    timeArray, inputCurrent, voltageArray = myRun2(
        durSec=durSec, amp=amp, baseLineShift=60, fs=10000, doPlot=doPlot, gK=gK1
    )

    # ms to seconds
    timeArray /= 1000

    print(f"saving gK:{gK1} {saveFile}")
    df = pd.DataFrame()
    df["seconds"] = timeArray
    df["mV"] = voltageArray
    # df['inputCurrent'] = inputCurrent
    df.to_csv(saveFile, index=False)

    # run 2
    timeArray, inputCurrent, voltageArray = myRun2(
        durSec=durSec, amp=amp, baseLineShift=60, fs=10000, doPlot=doPlot, gK=gK2
    )

    # ms to seconds
    timeArray /= 1000
    timeArray += durSec + (0.01 / 1000)

    print(f"saving and appending gK:{gK2} {saveFile}")
    df = pd.DataFrame()
    df["seconds"] = timeArray
    df["mV"] = voltageArray
    # df['inputCurrent'] = inputCurrent
    df.to_csv(saveFile, index=False, header=False, mode="a")
