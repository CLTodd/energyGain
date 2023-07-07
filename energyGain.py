# -*- coding: utf-8 -*-
"""
Created on Fri Jun  9 13:03:40 2023

@author: ctodd
"""

#import pdb
import matplotlib.pyplot as plt
import matplotlib.colors as mplc
import matplotlib.ticker as mticker
from mpl_toolkits.axes_grid1 import AxesGrid
import numpy as np
import seaborn as sns
import cmasher as cmr 
from timeit import default_timer
import re
from flasc.dataframe_operations import dataframe_manipulations as dfm
import pandas as pd



class energyGain():
    
    
    def __init__(self, df, dfUpstream, testTurbines=[], refTurbines=[],
                 wdCol=None, wsCol=None, 
                 defaultWindDirectionSpecs = [0,360,1],
                 defaultWindSpeedSpecs=[0,20,1], useReference=True):
        """
        testTurbines: list, turbine numbers to be considered test turbines
        refTurbines: list, turbine numbers to be considered reference turbines
        wdCol: string, name of the column in df to use for reference wind direction
            Calculates a column named "wd" if None
        wsCol: string, name of the column in df to use for reference wind speed
            Calculates a column named "ws" if None
        useReference: Boolean, wheter to compare Test turbines to Reference 
            turbines (True) or Test turbines to themselves in control mode
            versus baseline mode (False).
        """
        
        self.df = df
        self.dfLong=None
        self.dfUpstream = dfUpstream
        self.testTurbines = testTurbines
        self.referenceTurbines = refTurbines
        self.wdCol = wdCol
        self.wsCol = wsCol
        self.useReference = useReference
        
        # Set defaults
        self.defaultWindDirectionSpecs = defaultWindDirectionSpecs
        self.defaultWindSpeedSpecs = defaultWindSpeedSpecs
        
        # Set the columns to be referenced for wind speed and direction if not given   
        if self.wdCol == None:
            self.setWD() 
        if self.wsCol==None:
            self.setWS()
        
        # I don't rember why I did this
        if df is not None:
            self.__dfLonger__()
            self.allTurbines = [int(re.sub("\D+","",colname)) for colname in list(df) if re.match('^pow_\d+', colname)]
        else:
            self.allTurbines = None
            

    def setWS(self, colname=None):
        """
        Setting the column to be referenced for wind speed in none was provided
        
        """
        if colname != None:
            self.wsCol = colname
            return None
        
        # Set-difference to find the list of turbines that should be excluded from this wind speed calculation
        exc = list(set(self.allTurbines) - set(self.referenceTurbines)) # should this be changed to allow something other than reference turbines 
        # Set reference wind speed and direction for the data frame
        self.df = dfm.set_ws_by_upstream_turbines(self.df, self.dfUpstream, exclude_turbs=exc)
        self.wsCol = "ws"
        self.__dfLonger__()
        return None
    
    def setWD(self, colname=None):
        """
        Setting the column to be referenced for wind direction if none was provided
        """
        
        if colname != None:
            self.wdCol = colname
            return None
        
        self.df = dfm.set_wd_by_all_turbines(self.df)
        self.wdCol = "wd"
        self.__dfLonger__()
        return None
    
    def __dfLonger__(self):
        df = self.df
        powerColumns = ["pow_{:03.0f}".format(number) for number in self.referenceTurbines + self.testTurbines]
        keep = powerColumns + [self.wdCol, self.wsCol, "time"]
        df[keep].melt(value_vars=powerColumns,
                      value_name="power",
                      var_name="turbine", 
                      id_vars=['time', 'wd_smarteole', 'ws_smarteole'])
        df.set_index(df["time"],inplace=True, drop=True)
        self.dfLong = df
        return None
               
    def setReference(self, lst):
        self.referenceTurbines = lst
        self.__dfLonger__()
    
    def setTest(self, lst):
        self.testTurbines = lst
        self.__dfLonger__()
    
    def averagePower(self, windDirectionBin = None,
                     windSpeedBin = None, 
                     turbineList=None, controlMode="controlled",
                     verbose=False):
        """
        Average Power for a specific wind direction bin and wind speed bin.
        
        windDirectionBin: list of length 2
        windSpeedBin: list of length 2
        controlMode: string, "baseline", "controlled", or "both"
        wdToUse: string, name of the column with the reference wind direction.
            Calculates a column named "wd" if None
        wsToUse: string, name of the column with the reference wind speed.
            Calculates a column named "ws" if None
        """
        
        # Set wind direction if necessary
        if self.wdCol is None:
            self.setWD()
            
        # Set wind speed if necessary
        if self.wsCol is None:
            self.setWS()
            
        if windDirectionBin is None:
            windDirectionBin = self.defaultWindDirectionSpecs[0:2]
            
        if windSpeedBin is None:
            windSpeedBin = self.defaultWindSpeedSpecs[0:2]
        
        # Select relevant rows
        dfTemp = self.df.loc[ (self.df[self.wdCol]>= windDirectionBin[0]) &
                          (self.df[self.wdCol]< windDirectionBin[1]) &
                          (self.df[self.wsCol]>= windSpeedBin[0]) &
                          (self.df[self.wsCol]< windSpeedBin[1])
                        ]
        
        # Filter for control mode if necessary
        if controlMode != "both":
            dfTemp = dfTemp.loc[(dfTemp['control_mode']==controlMode)]
                            
        # Select only the columns that are for the desired turbines
        # This only works for up to 1000 turbines, otherwise formatting gets messed up
        powerColumns = ["pow_{:03.0f}".format(number) for number in turbineList]
        dfPower = dfTemp[powerColumns]
        
        # If the data frame is empty then this returns NaN. 
        # This is an imperfect work around imo
        if dfPower.empty:
            sadMessage = f"No observations for turbines {turbineList} in {controlMode} mode for wind directions {windDirectionBin} and wind speeds {windSpeedBin}."
            if verbose:
                print(sadMessage)
            return sadMessage
        
        avg = dfPower.mean(axis=None, skipna=True, numeric_only=True)
        
        
     
        return avg
    
    def powerRatio(self, windDirectionBin=None, windSpeedBin=None, controlMode=None, 
                   useReference = True, verbose = False):
        """
        Power ratio for a specific wind direction bin and wind speed bin. 
        
        windDirectionBin: list of length 2
        windSpeedBin: list of length 2
        controlMode: string, "baseline" or "controlled"
        wdToUse: string, name of the column with the reference wind direction.
            Calculates a column named "wd" if None
        wsToUse: string, name of the column with the reference wind speed.
            Calculates a column named "ws" if None
        useReference: Boolean, wheter to compare Test turbines to Reference 
            turbines (True) or Test turbines to themselves in control mode
            versus baseline mode (False). Used for some methods.
        """
        # Assuming valid inputs for now
        
        # Wanted to add this to give flexibility to not use the reference for 
        # one particular method, but part of me feels like this is just confusing 
        # or a bad idea. Might take it away and just always use the object attribute
        if useReference is None:
            useReference = self.useReference
        
        # Set wind speed if necessary
        if self.wsCol is None:
            self.setWS()
        
        # Set wind direction if necessary
        if self.wdCol is None:
            self.setWD()
            
        if windDirectionBin is None:
            windDirectionBin = self.defaultWindDirectionSpecs[0:2]
            
        if windSpeedBin is None:
            windSpeedBin = self.defaultWindSpeedSpecs[0:2]
        
        # Calculate Ratio
        numerator = self.averagePower(windDirectionBin, windSpeedBin,
                                      self.testTurbines, controlMode=controlMode)
        
        if useReference:
            denominator = self.averagePower(windDirectionBin, windSpeedBin,
                                            self.referenceTurbines, controlMode=controlMode)
        else:
            denominator = 1
            print("Reference turbines unused; calculating average power.")
            
        
        # If either of these are strings, 
        # there are no observations in this bin to calculate a ratio from
        if type(numerator) is str:
            sadMessage = numerator + "Can't calculate power ratio numerator (average power)."
            if verbose:
                print(sadMessage)
            return sadMessage
        
        if type(denominator) is str:
            sadMessage = denominator + "Can't calculate power ratio denominator (average power)."
            if verbose:
                print(sadMessage)
            return sadMessage
        

        return numerator/denominator

    def changeInPowerRatio(self, windDirectionBin=None, windSpeedBin=None, useReference=None, verbose=False):
        """
        Change in Power Ratio for a specific wind direction bin and wind speed bin.
        
        windDirectionBin: list of length 2
        windSpeedBin: list of length 2
        """
        if useReference is None:
            useReference = self.useReference
            
        # Set wind speed if necessary
        if self.wsCol is None:
            self.setWS()
        
        # Set wind direction if necessary
        if self.wdCol is None:
            self.setWD()
            
        if windDirectionBin is None:
            windDirectionBin = self.defaultWindDirectionSpecs[0:2]
            
        if windSpeedBin is None:
            windSpeedBin = self.defaultWindSpeedSpecs[0:2]

        if useReference:
            # Typical power ratio formula if we are using reference turbines
            control = self.powerRatio(windDirectionBin, windSpeedBin, "controlled", useReference=True)
            baseline = self.powerRatio(windDirectionBin, windSpeedBin, "baseline", useReference=True)
        else:
            control = self.powerRatio(windDirectionBin, windSpeedBin, "controlled", useReference=False)
            baseline = self.powerRatio(windDirectionBin, windSpeedBin, "baseline", useReference=False)
            
            # I think this is important so I'm printing this regardless of verbose
            FYI = "Change in power ratio is simply change in average power without reference turbines.\n"
            FYI += "Returning change in average power. If this isn't what you want, set the useReference argument to True."        
            print(FYI)
 
        # If either of these are strings, 
        # there are no observations in this bin to calculate a ratio from
        if type(control) is str:
            sadMessage = control + "Can't calculate power ratio for controlled mode."
            if verbose:
                print(sadMessage)
            return sadMessage
        
        if type(baseline) is str:
            sadMessage = baseline + "Can't calculate power ratio for baseline mode."
            if verbose:
                print(sadMessage)
            return sadMessage
        
        return control - baseline
        
    def percentPowerGain(self, windDirectionBin=None, windSpeedBin=None, useReference=None, verbose=False):
        
        """
        Percent Power Gain for a specific wind direction bin and wind speed bin.
        
        windDirectionBin: list of length 2
        windSpeedBin: list of length 2
        useReference: Boolean, wheter to compare Test turbines to Reference 
            turbines (True) or Test turbines to themselves in control mode
            versus baseline mode (False).
        """
        
        # Wanted to add this to give flexibility to not use the reference for 
        # one particular method, but part of me feels like this is just confusing 
        # or a bad idea. Might take it away and just always use the object attribute
        if useReference is None:
            useReference = self.useReference
        
        # Set wind speed if necessary
        if self.wsCol is None:
            self.setWS()
        
        # Set wind direction if necessary
        if self.wdCol is None:
            self.setWD()
        
        if windDirectionBin is None:
            windDirectionBin = self.defaultWindDirectionSpecs[0:2]
            
        if windSpeedBin is None:
            windSpeedBin = self.defaultWindSpeedSpecs[0:2]
            
        # If useReference==False, this simplifies to average power
        control = self.powerRatio(windDirectionBin, windSpeedBin, "controlled", useReference)
        baseline = self.powerRatio(windDirectionBin, windSpeedBin, "baseline", useReference)
        
        # If either of these are strings, 
        # there are no observations in this bin to calculate a ratio or average power from
        if type(control) is str:
            sadMessage = control + "Can't calculate power ratio for controlled mode."
            if verbose:
                print(sadMessage)
            return sadMessage
        
        if type(baseline) is str:
            sadMessage = baseline + "Can't calculate power ratio for baseline mode."
            if verbose:
                print(sadMessage)
            return sadMessage
        
        return (control - baseline)/baseline
    
    def binAdder(self, stepVars = "direction", windDirectionSpecs=None,
                 windSpeedSpecs=None, copy=True, df=None):
        """
        Add columns for the lower bounds of the wind condition bins to df (or a copy of df)
        
        windDirectionSpecs: list of length 3 or 2, specifications for wind direction
            bins-- [lower bound (inclusive), upper bound (exclusive), bin width].
            If direction is not in stepVars, 3rd element gets ignored if it exists.
        windSpeedSpecs: list of length 3 or 2, specifications for wind speed bins--
            [lower bound (inclusive), upper bound (exclusive), bin width]
            If speed is not in stepVars, 3rd element gets ignored if it exists.
        stepVars: string ("speed" or "direction") or list of the possible strings.
            The variable(s) you want to increment by for the wind condition bins
        copy: boolean, whether to simply return a copy of self.df (True) or to actually update self.df (False)
            Default is true because rows outside of the specs will be deleted
        """
        if windDirectionSpecs is None:
            windDirectionSpecs = self.defaultWindDirectionSpecs
            
        if windSpeedSpecs is None:
            windSpeedSpecs = self.defaultWindSpeedSpecs
            
        # Convert to list if needed
        if type(stepVars) is str:
            stepVars = list([stepVars])
        
        if df is None:
            df = self.df.copy()
        
        # Bin assignment doesn't work correctly for conditons outside these bounds 
        df = df.loc[(df[self.wdCol]>=windDirectionSpecs[0]) & (df[self.wdCol]<windDirectionSpecs[1]) &
                (df[self.wsCol]>=windSpeedSpecs[0]) & (df[self.wsCol]<windSpeedSpecs[1])]
        
        # Calculating the bins
        pd.options.mode.chained_assignment = None
        if "direction" in stepVars:
            df["directionBinLowerBound"] = (((df[self.wdCol]-windDirectionSpecs[0])//windDirectionSpecs[2])*windDirectionSpecs[2])+windDirectionSpecs[0]
        if "speed" in stepVars:
            df["speedBinLowerBound"] = (((df[self.wsCol]-windSpeedSpecs[0])//windSpeedSpecs[2])*windSpeedSpecs[2])+windSpeedSpecs[0]
        pd.options.mode.chained_assignment = 'warn'
        # Update self.df if desired
        if not copy:
            self.df = df
            
        # Return the copy with the bin columns
        return df
             
    def binAll(self, stepVars = ["direction", "speed"], windDirectionSpecs=None,
               windSpeedSpecs=None, retainControlMode=True, 
               retainTurbineLabel=True,  returnWide=True, df=None, group=True,
               filterBins=True):
        """
        windDirectionSpecs: list of length 3 or 2, specifications for wind direction
            bins-- [lower bound (inclusive), upper bound (exclusive), bin width].
            If direction is not in stepVars, 3rd element gets ignored if it exists.
        windSpeedSpecs: list of length 3 or 2, specifications for wind speed bins--
            [lower bound (inclusive), upper bound (exclusive), bin width]
            If speed is not in stepVars, 3rd element gets ignored if it exists.
        stepVars: string ("speed" or "direction") or list of the possible strings
            The variable(s) you want to increment by for the wind condition bins
        retainControlMode: boolean, whether to keep the control mode column (True) or not (False)
        """
        if windDirectionSpecs is None:
            windDirectionSpecs = self.defaultWindDirectionSpecs
            
        if windSpeedSpecs is None:
            windSpeedSpecs = self.defaultWindSpeedSpecs
        
        if type(stepVars) is str:    
            stepVars = list([stepVars])
        

        if df is None:
            df = self.binAdder(windDirectionSpecs=windDirectionSpecs,
                               windSpeedSpecs=windSpeedSpecs,
                               stepVars=stepVars)
        
        if filterBins:
            # Filter for conditions out of the bound of interest
            df = df.loc[(df[self.wdCol]>=windDirectionSpecs[0]) & (df[self.wdCol]<windDirectionSpecs[1]) &
                (df[self.wsCol]>=windSpeedSpecs[0]) & (df[self.wsCol]<windSpeedSpecs[1])]
        
        # Exclude undesirable turbines
        stepVarCols = ["{}BinLowerBound".format(var) for var in stepVars]
        powerColumns = ["pow_{:03.0f}".format(number) for number in self.referenceTurbines + self.testTurbines]     
        colsToKeep = stepVarCols[:]
        if retainControlMode:
           colsToKeep.append("control_mode")
        df = df[colsToKeep + powerColumns]
        
        # Pivot Longer
        dfLong = df.melt(id_vars=colsToKeep, value_name="power", var_name="turbine")
        
        # Convert turbine numbers from strings to integers
        dfLong["turbine"]  = dfLong["turbine"].str.removeprefix("pow_")
        dfLong["turbine"] = dfLong["turbine"].to_numpy(dtype=int)
        
        # Add turbine label column
        if retainTurbineLabel:
            labels = [(num in self.testTurbines) for num in dfLong["turbine"]]
            labels = np.where(labels, "test", "reference")
            dfLong["turbineLabel"] = labels
            colsToKeep.append("turbineLabel")
            
        if not group:
            return dfLong
        
        # Calculating average by group
        
        dfGrouped = dfLong.groupby(by=colsToKeep).agg(averagePower = pd.NamedAgg(column="power", 
                                                                                 aggfunc=np.mean),
                                                      numObvs = pd.NamedAgg(column="power", 
                                                                            aggfunc='count'))
        
        # Convert grouping index into columns for easier pivoting
        for var in colsToKeep:
            dfGrouped[var] = dfGrouped.index.get_level_values(var)
            
        # Pivot wider     
        if returnWide:
            optionalCols = list( set(colsToKeep) - set(stepVarCols))
            
            dfWide = dfGrouped.pivot(columns=optionalCols, index=stepVarCols, 
                                     values=['averagePower', 'numObvs'])
            return dfWide
        
        # Don't need these columns anymore since they are a part of the multi-index
        dfGrouped.drop(columns=colsToKeep, inplace=True)
        return dfGrouped
              
    # Fix comments later
    def computeAll(self, stepVars = ["direction", "speed"], 
                   windDirectionSpecs=None, windSpeedSpecs=None,
                   useReference=True, df=None):
        """
        Computes all the things from the slides except AEP gain

        Parameters
        ----------
        stepVars : TYPE, optional
            DESCRIPTION. The default is ["direction", "speed"].
        df : pandas data frame as returned from binAll with returnWide=True, optional
            Calls binAll if None.
        windDirectionSpecs : TYPE, optional
            DESCRIPTION. The default is None.
        windSpeedSpecs : TYPE, optional
            DESCRIPTION. The default is None.

        Returns
        -------
        df : pandas data frame
            Nicely formatted dataframe that can go directly into aepGain.
        """
        
        if windDirectionSpecs is None:
            windDirectionSpecs = self.defaultWindDirectionSpecs
            
        if windSpeedSpecs is None:
            windSpeedSpecs = self.defaultWindSpeedSpecs
            
        if type(stepVars) is str:    
            stepVars = list([stepVars])
            
        if df is None:
            df = self.binAll(stepVars = stepVars, 
                             windDirectionSpecs=windDirectionSpecs,
                             windSpeedSpecs=windSpeedSpecs,
                             df=df)
            
        
        # Sometimes the order of the labels in this tuple seem to change and I haven't figured out why. This should fix the order.
        df = df.reorder_levels([None, "turbineLabel", "control_mode"], axis=1)
                          
        if useReference:
            df["powerRatioBaseline"] = np.divide(df[('averagePower','test','baseline')], 
                                             df[('averagePower', 'reference', 'baseline')])
            df["powerRatioControl"] = np.divide(df[('averagePower', 'test', 'controlled')],
                                            df[('averagePower', 'reference', 'controlled')])
            df["totalNumObvs"] = np.nansum(np.dstack((df[('numObvs', 'test', 'controlled')],
                                                      df[('numObvs', 'reference', 'controlled')],
                                                      df[('numObvs', 'test', 'baseline')],
                                                      df[('numObvs', 'reference', 'baseline')])),
                                           axis=2)[0]
            
            
        else:
            df["powerRatioBaseline"] = df[('averagePower', 'test', 'baseline')]
            df["powerRatioControl"] = df[('averagePower', 'test', 'controlled')]
            
            
            df["totalNumObvs"] = np.nansum(np.dstack((df[('numObvs', 'test', 'controlled')],
                                                      df[('numObvs', 'test', 'baseline')])),
                                           axis=2)[0]
            
            df["totalNumObvsInclRef"] = np.nansum(np.dstack((df["totalNumObvs"],
                                                             df[('numObvs', 'reference', 'controlled')],
                                                             df[('numObvs', 'reference', 'baseline')])),
                                           axis=2)[0]
        
        # Same for both AEP methods
        N = np.nansum(df["totalNumObvs"])
        df["freq"] = df["totalNumObvs"]/N
        df["changeInPowerRatio"] = np.subtract(df['powerRatioControl'],
                                           df['powerRatioBaseline'])
        
        df["percentPowerGain"] = np.divide(df["changeInPowerRatio"],
                                       df['powerRatioControl'])
        
        # Make columns out of the indices just because it's easier to see sometimes
        stepVarCols = ["{}BinLowerBound".format(var) for var in stepVars]
        for var in stepVarCols:
            df[var] = df.index.get_level_values(var)
        
        return df
    
    # Fix comments later
    def aepGain(self, windDirectionSpecs=None,windSpeedSpecs=None,
                hours=8760, aepMethod=1, absolute=False, useReference=None,df=None):
        """
        Calculates AEP gain  

        Parameters
        ----------
        df : pandas data frame as returned by computeAll, optional
            If None, calls computeAll
        windDirectionSpecs : list, optional
            DESCRIPTION. The default is None.
        windSpeedSpecs : list, optional
            DESCRIPTION. The default is None.
        hours : float, optional
            DESCRIPTION. The default is 8760.
        aepMethod : int, optional
            DESCRIPTION. The default is 1.
        absolute : boolean, optional
            DESCRIPTION. The default is False.

        Returns
        -------
        AEP gain (float)

        """
        if windDirectionSpecs is None:
            windDirectionSpecs = self.defaultWindDirectionSpecs
            
        if windSpeedSpecs is None:
            windSpeedSpecs = self.defaultWindSpeedSpecs
            
        if useReference is None:
            useReference = self.useReference
        
        if not useReference:
            # Both methods are equivalent when reference turbines aren't used,
            aepMethod=1
            
        # Calculate nicely formatted df if needed
        if df is None:
            df = self.computeAll(stepVars=["speed","direction"],
                                 windDirectionSpecs=windDirectionSpecs,
                                 windSpeedSpecs=windSpeedSpecs,
                                 df=df,
                                 useReference = useReference)
            
        # Different AEP formulas
        if aepMethod==1:
            if useReference:
                df["aepGainContribution"] = np.multiply(np.multiply(df[('averagePower', 'test', 'baseline')],
                                                                df[('percentPowerGain', '', '')]),
                                                    df[('freq', '', '')])
            else:
                df["aepGainContribution"] = np.multiply(df["changeInPowerRatio"], df[('freq', '', '')])
    
            
            if not absolute:
                denomTerms = np.multiply(df[('averagePower', 'test', 'baseline')], df[('freq', '', '')])
            
        else:
            # Couldn't find an element-wise weighted mean, so I did this
            sumPowerRefBase = np.multiply(df[('averagePower', 'reference', 'baseline')],
                                          df[('numObvs', 'reference', 'baseline')])
            sumPowerRefcontrolled = np.multiply(df[('averagePower', 'reference', 'controlled')],
                                          df[('numObvs', 'reference', 'controlled')])
            
            sumPowerRef = np.nansum(np.dstack((sumPowerRefBase,sumPowerRefcontrolled)),2)[0]
            
            numObvsRef = np.nansum(np.dstack((df[('numObvs', 'reference', 'controlled')],df[('numObvs', 'reference', 'baseline')])),2)[0]
            
            avgPowerRef = np.divide(sumPowerRef, numObvsRef)
            
            df["aepGainContribution"] = np.multiply(np.multiply(avgPowerRef,
                                                              df[('changeInPowerRatio', '', '')]),
                                                  df[('freq', '', '')])
            if not absolute:
                denomTerms = np.multiply(np.multiply(avgPowerRef,
                                              df[('powerRatioBaseline', '', '')]),
                                  df[('freq', '', '')])
                
                
        if not absolute:
            # 'hours' here doesn't really represent hours, 
            # this is just so that our percentages are reported nicely
            hours = 100
            denom = np.nansum(denomTerms)
            df["aepGainContribution"] = df["aepGainContribution"]*(1/denom)
        
        aep = hours*np.nansum(df[('aepGainContribution', '', '')])    
        #print(aep)
        return (df, aep)
    
    def bootstrapSamples(self, B=1000, seed=None, pooled=True):
        
        start = default_timer()
        samples = np.full(B, None, dtype=pd.core.frame.DataFrame)
        
        
        prng = np.random.default_rng(seed=seed)
        
        nrow = self.df.shape[0]
        
        if pooled:
            dfPooled= self.df.sample(n=nrow*B,
                                replace=True,
                                random_state=prng)
            dfPooled.reset_index(drop=True,inplace=True)
        
            duration = default_timer() - start
            print("Sampling Time:", duration)
        
            dfPooled['repID'] = np.repeat(np.arange(0,B,1), repeats=nrow)
            return dfPooled
        
        else:
            samples = np.full(B, None, dtype=pd.core.frame.DataFrame)
            for rep in range(B):
                dfTemp = self.df.sample(n=nrow,
                                    replace=True,
                                    random_state=prng)
                dfTemp.reset_index(drop=True,inplace=True)
                samples[rep] = dfTemp
                                                                   
        
        duration = default_timer() - start
        print("Sampling Time:", duration)
            
        
        return samples
     
    # Need to completely rewrite this so that it works with computeAll
    def bootstrapEstimate(self, stepVars=["direction","speed"], 
                          windDirectionSpecs=None, windSpeedSpecs=None,
                          B=1000, seed=None, useReference=True,
                          seMultiplier=2, lowerPercentile=2.5, upperPercentile=97.5,
                          retainReps = False, diagnose=True, repsPooled=None,
                          **AEPargs):# figure out how to use kwargs here for hours, aepmethod, and absolute, etc. for metricMethod
        """
        Compute summary statistics of bootsrapped samples based on your metric of choice
        

        windDirectionSpecs: list of length 3, specifications for wind direction
            bins-- [lower bound (inclusive), upper bound (exclusive), bin width]
            Only used if nDim=2
        windSpeedSpecs: list of length 3, specifications for wind speed bins--
            [lower bound (inclusive), upper bound (exclusive), bin width]
            Only used if nDim=2
        **AEPargs: args for the AEP method
        """
        if windDirectionSpecs is None:
            windDirectionSpecs = self.defaultWindDirectionSpecs
            
        if windSpeedSpecs is None:
            windSpeedSpecs = self.defaultWindSpeedSpecs
            
        
        if type(stepVars) is str:    
            stepVars = list([stepVars])
        
        start = default_timer()
        
        # Get an array of the bootstrap samples
        if repsPooled is None:
            bootstrapDFs = self.bootstrapSamples(B=B, seed=seed)
        else:
            bootstrapDFs = repsArray
            B = bootstrapDFs.size

        
        finalCols = ['percentPowerGain', 'changeInPowerRatio']
        finalColsMultiIdx = [('percentPowerGain', '',''),
                             ('changeInPowerRatio', '','')]
            
        for var in stepVars:
            name = f'{var}BinLowerBound'
            finalCols.append(name)
            finalColsMultiIdx.append((name,'',''))
        
        # Setup empty array to hold the binned versions of each bootstrap simulation
       # bootstrapDFbinned = np.full(B, None, dtype=pd.core.frame.DataFrame)
        
        for bootstrap in range(B):
            
            
            # Get current bootstrap sample
            currentDF = bootstrapDFs[bootstrap]
            
            # get into correct format
            binadder =self.binAdder(stepVars, windDirectionSpecs, windSpeedSpecs, df=currentDF)
            binall = self.binAll(stepVars, windDirectionSpecs, windSpeedSpecs, df=binadder, filterBins=True)
            computeall = self.computeAll(stepVars, windDirectionSpecs,
                                         windSpeedSpecs, useReference, df=binall)
            
            #bootstrapDFbinned[bootstrap] = binadder
            
            binStats = computeall[finalColsMultiIdx]
            # Multi-index on the columns makes indexing annoying when all but one level is empty
            dfTemp = binStats.reset_index(drop=True).droplevel(level=[1,2], axis="columns")
            # Make sure columns are in the right order
            dfTemp = dfTemp[finalCols]
            dfTemp['repID'] = bootstrap
            
            aepTemp = np.full(shape=(8,4), fill_value=np.nan, dtype=float)
            i=0
            for method in (1,2):
                for abso in (0, 1):
                    for useRef in (0, 1):
                        aep = self.aepGain(aepMethod=method,
                                       absolute=bool(abso),
                                       useReference=bool(useRef),
                                       windDirectionSpecs=windDirectionSpecs,
                                       windSpeedSpecs=windSpeedSpecs,
                                       df=computeall)
                        
                        aepTemp[i] = np.asarray([method, abso, useRef, aep[1]])
                        i+=1
            
            if bootstrap==0:
                metricMatrix = np.asarray(dfTemp)
                aepMatrix = aepTemp.copy()
            else:
                metricMatrix = np.concatenate((metricMatrix, np.asarray(dfTemp)), axis=0)
                aepMatrix = np.concatenate((aepMatrix, np.asarray(aepTemp)), axis=0)
            
        aepSamplingDist = pd.DataFrame(data=aepMatrix, columns = ["aepMethod","absoluteAEP", "useReference","aepGain"])
        
        #for metric in ("percentPowerGain", "change")
        
        aepSummary = aepSamplingDist.groupby(by=["aepMethod","absoluteAEP", "useReference"]).agg(mean=pd.NamedAgg(column="aepGain",
                                                                      aggfunc=np.mean),
                                                     se=pd.NamedAgg(column="aepGain",
                                                                    aggfunc=np.nanstd),
                                                     median=pd.NamedAgg(column="aepGain",
                                                                        aggfunc=np.nanmedian),
                                                     upperPercentile=pd.NamedAgg(column="aepGain",
                                                                                 aggfunc=lambda x: np.nanpercentile(x,upperPercentile)),
                                                     lowerPercentile=pd.NamedAgg(column="aepGain",
                                                                                 aggfunc=lambda x: np.nanpercentile(x, lowerPercentile)),
                                                     nObvs = pd.NamedAgg(column="aepGain", 
                                                                           aggfunc='count'),
                                                     firstQuartile = pd.NamedAgg(column="aepGain",
                                                                                 aggfunc=lambda x: np.nanpercentile(x,25)),
                                                     thirdQuartile= pd.NamedAgg(column="aepGain",
                                                                                 aggfunc=lambda x: np.nanpercentile(x,75)))
        seMultdAEP = seMultiplier*aepSummary["se"]
        aepSummary["meanMinusSE"] = np.subtract(aepSummary["mean"], seMultdAEP)
        aepSummary["meanPlusSE"] = np.add(aepSummary["mean"], seMultdAEP)
        aepSummary["iqr"] = np.subtract(aepSummary['thirdQuartile'], aepSummary['firstQuartile'])
        # For convenience
        aepSummary["metric"] = 'aepGain'
        aepSummary["nReps"] = B
        
        aepSummary = aepSummary[["mean",'meanMinusSE','meanPlusSE', 
                           'median', 'lowerPercentile', 'upperPercentile',
                           'se', 'iqr','nObvs', 'metric', 'nReps']]
        
        # Save sampling distributions
        metricDF = pd.DataFrame(data=metricMatrix, columns=finalCols+['repID'])
        ppgSamplingDists = metricDF.copy().drop(columns='changeInPowerRatio', inplace=False)
        cprSamplingDists = metricDF.copy().drop(columns='percentPowerGain', inplace=False)
        
        # Compute Sample statistics for each wind condition bin
        metricDFlong = metricDF.melt(value_vars=['percentPowerGain', 'changeInPowerRatio'],
                                     value_name='value',
                                     var_name='metric',
                                     id_vars=finalCols[2:])
        
        finalCols = list(metricDFlong)[:-1]# last column is value
        dfSummary = metricDFlong.groupby(by=finalCols).agg(mean=pd.NamedAgg(column='value',
                                                                      aggfunc=np.mean),
                                                     se=pd.NamedAgg(column='value',
                                                                    aggfunc=np.nanstd),
                                                     median=pd.NamedAgg(column='value',
                                                                        aggfunc=np.nanmedian),
                                                     upperPercentile=pd.NamedAgg(column='value',
                                                                                 aggfunc=lambda x: np.nanpercentile(x,upperPercentile)),
                                                     lowerPercentile=pd.NamedAgg(column='value',
                                                                                 aggfunc=lambda x: np.nanpercentile(x, lowerPercentile)),
                                                     nObvs = pd.NamedAgg(column='value', 
                                                                           aggfunc='count'),
                                                     firstQuartile = pd.NamedAgg(column='value',
                                                                                 aggfunc=lambda x: np.nanpercentile(x,25)),
                                                     thirdQuartile= pd.NamedAgg(column='value',
                                                                                 aggfunc=lambda x: np.nanpercentile(x,75)))
        
        pctPwrGain = dfSummary.iloc[dfSummary.index.get_level_values('metric')=="percentPowerGain"]
        chngPwrRatio = dfSummary.iloc[dfSummary.index.get_level_values('metric')=="changeInPowerRatio"]
        
        for df in [pctPwrGain, chngPwrRatio]:
            seMultd = seMultiplier*df["se"]
            df["meanMinusSE"] = np.subtract(df["mean"], seMultd)
            df["meanPlusSE"] = np.add(df["mean"], seMultd)
            df["iqr"] = np.subtract(df['thirdQuartile'], df['firstQuartile'])
            # For convenience
            df["nReps"] = B
            df["metric"] = df.index.get_level_values('metric')
        
            df = df[["mean",'meanMinusSE','meanPlusSE',
                    'median', 'lowerPercentile', 'upperPercentile',
                    'se', 'iqr','nObvs', 'metric', 'nReps']]

        pctPwrGain.index=pctPwrGain.index.droplevel('metric')
        chngPwrRatio.index=chngPwrRatio.index.droplevel('metric')
        
        resultDict = {"percent power gain": pctPwrGain,
                "change in power ratio": chngPwrRatio,
                "aep gain": aepSummary,
                'ppg sampling distributions': ppgSamplingDists,
                'cpr sampling distributions':cprSamplingDists,
                'aep sampling distribution': aepSamplingDist,}
        
        if retainReps:
            resultDict['reps'] = bootstrapDFs
        
        duration = default_timer() - start
        print("Overall:", duration)
        
        if diagnose:
            dfBinned = self.binAdder(stepVars, windDirectionSpecs, windSpeedSpecs)
            
            self.bootstrapDiagnostics(bsEstimateDict=resultDict,
                                      dfBinned=dfBinned,
                                      windDirectionSpecs=windDirectionSpecs,
                                      windSpeedSpecs=windSpeedSpecs,
                                      colors=['cmr.iceburn',
                                              'cubehelix',
                                              sns.color_palette("coolwarm_r",
                                                                as_cmap=True),
                                              'cubehelix'])
            
        return resultDict
    
    def bootstrapDiagnostics(self, bsEstimateDict, dfBinned,
                             windDirectionSpecs=None, windSpeedSpecs=None,
                             colors=['turbo', 'turbo','turbo','turbo']):
        # Check for other commonalities that can be moved here
        stepVars = []
        for var in bsEstimateDict['percent power gain'].index.names:
            stepVars.append(var)     
            
        if len(stepVars)==2:
            self.__bsDiagnostics2d__(bsEstimateDict=bsEstimateDict)
        else:#(if len(stepVars)==1)
            self.__bsDiagnostics1d__(bsEstimateDict=bsEstimateDict,
                                     stepVar=stepVars, 
                                     dfBinned=dfBinned,
                                     windDirectionSpecs=windDirectionSpecs,
                                     windSpeedSpecs=windSpeedSpecs,
                                     colors=colors)
            

        return None 
    
    def __bsDiagnostics1d__(self,bsEstimateDict,
                            dfBinned,
                            stepVar,
                            windDirectionSpecs=None, windSpeedSpecs=None, 
                            colors=['turbo', 'turbo','turbo','turbo']):
        
        ppgSamplingDists = bsEstimateDict['ppg sampling distributions']
        ppgSummary = bsEstimateDict["percent power gain"]
        
        if windDirectionSpecs is None:
            windDirectionSpecs = self.defaultWindDirectionSpecs
            
        if windSpeedSpecs is None:
            windSpeedSpecs = self.defaultWindSpeedSpecs
            
        stepVar = stepVar[0]
            
        if stepVar=='directionBinLowerBound':
            width=windDirectionSpecs[2]
            edges = np.arange(*windDirectionSpecs)
            xLabel = u"Wind Direction (\N{DEGREE SIGN})"    
        else:#(if stepVar=='speed'):
            width=windSpeedSpecs[2]
            edges = np.arange(*windSpeedSpecs)
            xLabel = "Wind Speed (m/s)"
        
        # Get Data
        # This still needsto be added, the below is wrong
        
        
        # Histograms
        plt.clf()
        sns.set_theme(style="darkgrid")
        
        fig, axs = plt.subplots(nrows=1, ncols=2, sharex=True, 
                                sharey=True, figsize=(10,5), 
                                layout='constrained')
        
         
        h1 = sns.histplot(dfBinned, x=stepVar,
                          stat='density', thresh=None,
                           binwidth = width, ax=axs[1], linewidth=1)
        breakpoint()
        h0 = sns.histplot(x=ppgSamplingDists[stepVar],
                          stat='density', thresh=None,
                           binwidth=width, ax=axs[0], linewidth=1)
         

         ### Tick marks at multiples of 5 and 1
        for ax in axs:
             ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
             ax.yaxis.set_major_locator(mticker.MultipleLocator(.05))
             ax.xaxis.set_minor_locator(mticker.MultipleLocator(1)) 
             ax.yaxis.set_minor_locator(mticker.MultipleLocator(.01))
             ax.tick_params(which="major", bottom=True, length=7, 
                            color='#4C4C4C', axis='x', left=True)
             ax.tick_params(which="minor", bottom=True, length=3,
                            color='#4C4C4C', axis='x', left=True)
             ax.set_xlabel("", fontsize=0)
             ax.set_ylabel("", fontsize=0)
             ax.grid(which='minor', visible=True,linestyle='-',
                     linewidth=0.5, axis='y')
             
        axs[0].tick_params(which="minor", bottom=True, length=3,
                       color='#4C4C4C', axis='y', left=True)
        axs[0].tick_params(which="major", bottom=True, length=7, 
                       color='#4C4C4C', axis='y', left=True)
           
        ### Labels
        axs[1].set_title(f"Real Data (size={self.df.shape[0]})")
        axs[0].set_title(f"Pooled Bootstrap Samples (size={self.df.shape[0]}; nReps = {ppgSummary['nReps'].iloc[1]})")
        fig.supxlabel(xLabel, fontsize=15) #unicode formatted
        fig.suptitle("Densities ", fontsize=17)
        plt.show()
        
        
        # Sampling distribution by bin
        #sns.violinplot(data=df, x="age", y="alive", cut=0)
        
        
        return None
    
    def __bsDiagnostics2d__(self, bsEstimateDict,
                            dfBinned,
                            stepVars,
                             windDirectionSpecs, windSpeedSpecs, colors):
        
        ppgSamplingDists = bsEstimateDict['ppg sampling distributions']
        
        ppgSummary = bsEstimateDict['percent power gain']
        cprSummary = bsEstimateDict['cpr sampling distributions']
        aepSummary = bsEstimateDict['aep gain']
        
        
        
        # 2d Histogram

        directionEdges = np.arange(*windDirectionSpecs)
        speedEdges = np.arange(*windSpeedSpecs)
        
    
        
        ## Plotting   
        fig, axs = plt.subplots(nrows=1, ncols=2, 
                                sharex=True, sharey=True, 
                                figsize=(10,5), layout='constrained')
        ### Histograms
        width = np.min(np.asarray([windDirectionSpecs[2], windSpeedSpecs[2]]))
        
        h0 = sns.histplot(dfBinned,
                          x='directionBinLowerBound', y='speedBinLowerBound',
                          cbar=True, stat='density', thresh=None,
                          binwidth = width, ax=axs[1], linewidth=1,
                          cmap=sns.color_palette("rocket_r", as_cmap=True))
              
        h1 = sns.histplot(ppgSamplingDists,
                          x='directionBinLowerBound',
                          y='speedBinLowerBound', stat='density',thresh=None,
                          binwidth=width, ax=axs[0], linewidth=1,
                          cmap=sns.color_palette("rocket_r", as_cmap=True))
        
        
        
        
        
        ### Tick marks at multiples of 5 and 1
        for ax in axs:
            ax.xaxis.set_major_locator(mticker.MultipleLocator(5))
            ax.yaxis.set_major_locator(mticker.MultipleLocator(5))
            ax.xaxis.set_minor_locator(mticker.MultipleLocator(1)) 
            ax.yaxis.set_minor_locator(mticker.MultipleLocator(1))
            ax.tick_params(which="major", bottom=True, length=5)
            ax.tick_params(which="minor", bottom=True, length=3)
            ax.set_xlabel("", fontsize=0)
            ax.set_ylabel("", fontsize=0)
        
        ### Labels
        axs[1].set_title(f"Real Data (size={self.df.shape[0]})")
        axs[0].set_title(f"Pooled Bootstrap Samples (size={self.df.shape[0]}; nReps = {ppgSummary['nReps'].iloc[1]})")
        fig.supxlabel(u"Wind Direction (\N{DEGREE SIGN})", fontsize=15) #unicode formatted
        fig.supylabel("Wind Speed (m/s)",fontsize=15)
        fig.suptitle("Densities ", fontsize=17)
        plt.show()
        # Heatmaps
        
        # Not the correct way to do this but it works for now
        xlabels = []

        for num in np.arange(*windDirectionSpecs):
            if num%5==0:
                xlabels.append(str(num))
                continue
            xlabels.append(" ")
            
        ylabels = []
        for num in np.arange(*windSpeedSpecs):
            if num%5==0:
                ylabels.append(str(num))
                continue
            ylabels.append(" ")
        
        ## Getting the data
        ## 4 types of plots: Centers, variance, CI width, and CI sign )pos/neg)
        pArray = np.asarray([["Centers", "Mean","Median"],
                             ["Variance", "SE", "IQR"],
                             ["Interval Coverage", "SE Method", "Percentile Method"],
                             ["Confidence Interval Widths", "SE Method", "Percentile Method"]])
        
        idxs = [(iS,iD) for iS in range(speedEdges.size) for iD in range(directionEdges.size)]
        
        for dfSummary in [ppgSummary, cprSummary]:
        
            mCenterMean,mCenterMed,mVarSE,mVarIQR, mPosNegCI, mPosNegPerc,mIWperc,mIWci = [np.full(shape=(speedEdges.size, directionEdges.size), fill_value=np.nan, dtype=float) for i in range(8)]
            ### Just in case indices are out of order
            dfSummary.index = dfSummary.index.reorder_levels(order=['directionBinLowerBound','speedBinLowerBound'])
        
            for idx in idxs:
                try:
                    mVarSE[idx[0], idx[1]] = dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['se']
                    mVarIQR[idx[0], idx[1]] = dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['iqr']
                    mIWperc[idx[0], idx[1]] = dfSummary.loc[(directionEdges[idx[1]],
                                                               speedEdges[idx[0]])]['upperPercentile'] - dfSummary.loc[(directionEdges[idx[1]],
                                                                                                          speedEdges[idx[0]])]['lowerPercentile']
                    mIWci[idx[0], idx[1]] = dfSummary.loc[(directionEdges[idx[1]],
                                                               speedEdges[idx[0]])]['meanPlusSE'] - dfSummary.loc[(directionEdges[idx[1]],
                                                                                                          speedEdges[idx[0]])]['meanMinusSE']
                    mCenterMean[idx[0], idx[1]] = dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['mean']
                    mCenterMed[idx[0], idx[1]] = dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['median']
                    
                    
                    if dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['meanPlusSE']<0:
                        mPosNegCI[idx[0], idx[1]] = -1
                    elif dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['meanMinusSE']>0:
                        mPosNegCI[idx[0], idx[1]] = 1
                    elif dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['lowerPercentile']*dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['upperPercentile']<0:
                        mPosNegCI[idx[0], idx[1]] = 0
                        
                    if dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['upperPercentile']<0:
                        mPosNegPerc[idx[0], idx[1]] = -1
                    elif dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['lowerPercentile']>0:
                        mPosNegPerc[idx[0], idx[1]] = 1
                    elif dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['lowerPercentile']*dfSummary.loc[(directionEdges[idx[1]],speedEdges[idx[0]])]['upperPercentile']<0:
                        mPosNegPerc[idx[0], idx[1]] = 0
                    
                    
                except KeyError:
                    continue
        
            mArray = np.asarray([[mCenterMean,mCenterMed], 
                             [mVarSE,mVarIQR],
                             [mPosNegCI, mPosNegPerc],
                             [mIWperc,mIWci]])
        
            ## Plotting

            ### Set up the plotting field
            for plot in range(pArray.shape[0]):
                plt.clf()
                fig, axs = plt.subplots(nrows=1, ncols=2,
                                    sharex=True, sharey=True, 
                                    figsize=(10,5), layout='constrained')
            
                ### Set up the individual heatmaps
                for i in range(2):
                    ### Get data
                    M = mArray[plot][i]
                
                    axs[i]=sns.heatmap(M,center=0, square=False, linewidths=0, 
                                   ax=axs[i], cbar=bool(i), cbar_kws={"shrink": .8},
                                   annot=False, cmap=colors[plot], robust=True)


                    axs[i].yaxis.set_minor_locator(mticker.MultipleLocator(0.5))
                    axs[i].invert_yaxis()
                    axs[i].xaxis.set_minor_locator(mticker.MultipleLocator(0.5))
                    axs[i].xaxis.tick_bottom()

                    axs[i].tick_params(which="minor", bottom=True, length=6, color='#4C4C4C')
                    axs[i].tick_params(which="major", bottom=True, length=0, color='#4C4C4C', 
                               grid_linewidth=0)
                    axs[i].set_xticklabels(xlabels, rotation=-90)
                    axs[i].set_yticklabels(ylabels, rotation=0)
                
                    axs[i].grid(which='minor', visible=True, color='#d9d9d9',linestyle='-',
                        linewidth=1)

                    axs[i].set_title(pArray[plot][i+1], fontsize=13)                          


                axs[1].tick_params(which="minor", bottom=True, length=0, color='white')
            
                ### Labels
                fig.supxlabel(u"Wind Direction (\N{DEGREE SIGN})", fontsize=15) #unicode formatted
                fig.supylabel("Wind Speed (m/s)",fontsize=15)
                fig.suptitle(f"{pArray[plot][0]} ({dfSummary['metric'].iloc[1]}; nReps = {dfSummary['nReps'].iloc[1]})", fontsize=17)
                plt.show()
                
        return None
    
    # Seems inefficient 
    def lineplotBE(self, dfSummary=None, repsArray=None, windDirectionSpecs=None, windSpeedSpecs=None, 
             stepVar="direction", useReference=True, **BEargs):
        """
        windDirectionSpecs: list of length 3, specifications for wind direction
            bins-- [lower bound (inclusive), upper bound (exclusive), bin width]
        windSpeedSpecs: list of length 3, specifications for wind speed bins--
            [lower bound (inclusive), upper bound (exclusive), bin width]
        """
        if windDirectionSpecs is None:
            windDirectionSpecs = self.defaultWindDirectionSpecs
            
        if windSpeedSpecs is None:
            windSpeedSpecs = self.defaultWindSpeedSpecs
            
        fig, axs = plt.subplots(nrows=1, ncols=2,
                                sharex=True, sharey=True, 
                                figsize=(20,7), layout='constrained')
    
        # put other scenarios in here
        if (dfSummary is None) and (repsArray is not None):
            dfSummary=self.bootstrapEstimate(stepVars=stepVar,
                                   windDirectionSpecs=windDirectionSpecs,
                                   windSpeedSpecs=windSpeedSpecs,
                                   repsArray=repsArray,
                                   metric="percentPowerGain", 
                                   useReference=useReference,
                                   diagnose=False,
                                   retainReps = False,
                                   **BEargs)
            
        metric = dfSummary['metric'].iloc[1]
        
        X = dfSummary.index.get_level_values(f'{stepVar}BinLowerBound')
        
        yMean = dfSummary['mean']
        yUpperSE = dfSummary['meanPlusSE']
        yLowerSE = dfSummary['meanMinusSE']
        
        yMed = dfSummary['median']
        yUpperPerc = dfSummary['upperPercentile']
        yLowerPerc = dfSummary['lowerPercentile']
        
        axs[0].axhline(0, color='black', linestyle='dotted')
        axs[0].plot(X, yMean, linestyle='-', marker='.', markersize=10)
        axs[0].fill_between(x=X, y1=yUpperSE,y2=yLowerSE, alpha=0.4)
        axs[0].grid()
        axs[0].set_title("SE Method", fontsize=13)
        
        axs[1].axhline(0, color='black', linestyle='dotted')
        axs[1].plot(X, yMed, linestyle='-', marker='.',markersize=10)
        axs[1].fill_between(x=X, y1=yUpperPerc,y2=yLowerPerc, alpha=0.4)
        axs[1].grid()
        axs[1].set_title("Percentile Method", fontsize=13)
        
        if stepVar=='speed':
            xAxis = "Wind Speed (m/s)"
            title = f"Wind Directions {windDirectionSpecs[0]}" + u"\N{DEGREE SIGN}" + f" - {windDirectionSpecs[1]}" + u"\N{DEGREE SIGN}"
        else:
            xAxis = u"Wind Direction (\N{DEGREE SIGN})"
            title = f"Wind Speeds {windSpeedSpecs[0]} to {windSpeedSpecs[1]} m/s"
        fig.supxlabel(xAxis, fontsize=13) #unicode formatted
        fig.supylabel(f"{metric} bootstrap centers",fontsize=13)
        fig.suptitle(title, fontsize=17)
        plt.show()
        
        return None    