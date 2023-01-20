import numpy as np
import matplotlib.pyplot as plt
import fatpack
import qats

'''
Implementation of SN curves using various python packages 

TODO these classes should be created as first a parent class with all information, and then fatpack and qats should inherit from it
During implementation and prototyping / testing, this was not prioritized 
'''

class SN_Curve_fatpack:
    """
    Return a DNVGL C203 endurance curve - the implementation of an SN curve in the way fatpack interacts with it
    Found at https://github.com/Gunnstein/fatpack/blob/master/examples/Defining%20DNVGL%20RP-C203%20endurance%20curves%20with%20fatpack.ipynb
    Adjusted to only contain in air
    Added a plotting function
    """    
    
    def __init__(self, name):
        self.input = dict(
                    reference = "DNVGL-RP-C203 Ed.: Apr 2016, Tab. 2-1 S-N curves in air",
                    B1= dict(m1=4.0, loga1=15.117, m2=5, Nd=1e7, loga2=17.146, fl=106.97, k = 0.00),
                    B2= dict(m1=4.0, loga1=14.885, m2=5, Nd=1e7, loga2=16.856, fl= 93.59, k = 0.00),
                    C = dict(m1=3.0, loga1=12.592, m2=5, Nd=1e7, loga2=16.320, fl= 73.10, k = 0.05),
                    C1= dict(m1=3.0, loga1=12.449, m2=5, Nd=1e7, loga2=16.081, fl= 65.50, k = 0.10),
                    C2= dict(m1=3.0, loga1=12.301, m2=5, Nd=1e7, loga2=15.835, fl= 58.48, k = 0.15),
                    D = dict(m1=3.0, loga1=12.164, m2=5, Nd=1e7, loga2=15.606, fl= 52.63, k = 0.20),
                    E = dict(m1=3.0, loga1=12.010, m2=5, Nd=1e7, loga2=15.350, fl= 46.78, k = 0.20),
                    F = dict(m1=3.0, loga1=11.855, m2=5, Nd=1e7, loga2=15.091, fl= 41.52, k = 0.25),
                    F1= dict(m1=3.0, loga1=11.699, m2=5, Nd=1e7, loga2=14.832, fl= 36.84, k = 0.25),
                    F3= dict(m1=3.0, loga1=11.546, m2=5, Nd=1e7, loga2=14.576, fl= 32.75, k = 0.25),
                    G = dict(m1=3.0, loga1=11.398, m2=5, Nd=1e7, loga2=14.330, fl= 29.24, k = 0.25),
                    W1= dict(m1=3.0, loga1=11.261, m2=5, Nd=1e7, loga2=14.101, fl= 26.32, k = 0.25),
                    W2= dict(m1=3.0, loga1=11.107, m2=5, Nd=1e7, loga2=13.845, fl= 23.39, k = 0.25),
                    W3= dict(m1=3.0, loga1=10.970, m2=5, Nd=1e7, loga2=13.617, fl= 21.05, k = 0.25),
                    )
        
        self.name = name + '_fatpack'
        self.title = self.input['reference'] + f', {name}'
        self.data = self.input[name]
        self.t_ref = 25.0 # millimeters - reference thickness equal 25 mm for welded connections other than simple tubular joints. For simple tubular joints the reference thickness is 16 mm when using the T-curve. The reference thickness is equal 25 mm when other S-N curves are used for fatigue analysis of tubular joints. For bolts tref = 25 mm
        self.k = self.data['k'] # stored here since the fatpack SN curve dont store any 
        self.SN = self.in_air()
            
    def miner_sum(self, stress_ranges):
        """Calculate and return the Palmgren-Miner summation of the given stress ranges 

        Args:
            stress_ranges (np.array): 2D array containing col0 = stress ranges, col1 = counts per stress range

        Returns:
            float: The miner sum as a fraction of failure capacity
        """
        return self.SN.find_miner_sum(stress_ranges)
        
    def in_air(self):
        """
        Returns a DNVGL endurance curve (SN curve)
        
        This method returns an endurance curve in air according to 
        table 2-1 in DNVGL RP-C203.
        
        Arguments
        ---------
        name : str
            Name of the endurance curve.
            
        Returns
        -------
        fatpack.BiLinearEnduranceCurve
            Endurance curve corresponding to `name` in DNVGL RP-C203
            
        Example
        -------
        >>>curve = DNVGL_EnduranceCurve.in_air("D")
        >>>N = curve.get_endurance(90.0)
        
        """
        Sc = 1.0 # Set to one in order to get the DNV standard directly out from fatpack, which is based on Eurocode 3        
        curve = fatpack.BiLinearEnduranceCurve(Sc)
        curve.Nc = 10 ** self.data["loga1"] # intercept of N-axis, found as "log a_bar" in DNV standard. This is needed for adjust compared to default Nc value since we are transforming from Eurocode with S_c = 1.0 
        curve.Nd = self.data["Nd"] # fatigue limit at 10**7 cycles
        curve.m1 = self.data["m1"] # slope for N <= 10**7 cycles
        curve.m2 = self.data["m2"] # slope for N > 10**7 cycles
        curve.reference = self.input["reference"]
        return curve
    
    def plot_characteristics(self, info_on_plot = True):
        '''
        Uses the bilinear endurance curve to plot its characteristics / SN-plot for quick inspection 
        '''
        N = np.logspace(4, 8, 1000)
        S = self.SN.get_stress(N)
        plt.figure(dpi=96)
        plt.loglog(N, S)
        plt.title(f'DNVGL RP-C203 SN curve in air, {self.name}')
        plt.xlabel("Number of cycles")
        plt.ylabel("Stress range (MPa)")
        plt.xlim([10**5, 10**8])
        plt.ylim([10**1.2, 10**2.4])
        plt.grid(which='both')

        fatigue_limit = self.SN.get_stress(10**7)
        loga2 = np.log10(self.SN.get_endurance(1))
        
        if info_on_plot:
            plt.text(0.95, 0.95, f"Fatigue limit: {fatigue_limit:.1f} MPa at 1e7 cycles", horizontalalignment='right', verticalalignment='center', transform=plt.gca().transAxes, backgroundcolor='#e28743')
            plt.text(0.95, 0.87, f"Intercept of second linear curve log a2: {loga2:.2f}", horizontalalignment='right', verticalalignment='center', transform=plt.gca().transAxes, backgroundcolor='#e28743')
        else:
            # Not mandatory - TODO can be removed
            print(f"Fatigue limit: {fatigue_limit:.1f} MPa at 1e7 cycles")
            print(f"Intercept of second linear curve log a2: {loga2:.2f}")  
              

class SN_Curve_qats:  
    
    def __init__(self, name):
        self.input = dict(
                    reference = "DNVGL-RP-C203 Ed.: Apr 2016, Tab. 2-1 S-N curves in air",
                    B1= dict(m1=4.0, loga1=15.117, m2=5, Nd=1e7, loga2=17.146, fl=106.97, k = 0.00),
                    B2= dict(m1=4.0, loga1=14.885, m2=5, Nd=1e7, loga2=16.856, fl= 93.59, k = 0.00),
                    C = dict(m1=3.0, loga1=12.592, m2=5, Nd=1e7, loga2=16.320, fl= 73.10, k = 0.05),
                    C1= dict(m1=3.0, loga1=12.449, m2=5, Nd=1e7, loga2=16.081, fl= 65.50, k = 0.10),
                    C2= dict(m1=3.0, loga1=12.301, m2=5, Nd=1e7, loga2=15.835, fl= 58.48, k = 0.15),
                    D = dict(m1=3.0, loga1=12.164, m2=5, Nd=1e7, loga2=15.606, fl= 52.63, k = 0.20),
                    E = dict(m1=3.0, loga1=12.010, m2=5, Nd=1e7, loga2=15.350, fl= 46.78, k = 0.20),
                    F = dict(m1=3.0, loga1=11.855, m2=5, Nd=1e7, loga2=15.091, fl= 41.52, k = 0.25),
                    F1= dict(m1=3.0, loga1=11.699, m2=5, Nd=1e7, loga2=14.832, fl= 36.84, k = 0.25),
                    F3= dict(m1=3.0, loga1=11.546, m2=5, Nd=1e7, loga2=14.576, fl= 32.75, k = 0.25),
                    G = dict(m1=3.0, loga1=11.398, m2=5, Nd=1e7, loga2=14.330, fl= 29.24, k = 0.25),
                    W1= dict(m1=3.0, loga1=11.261, m2=5, Nd=1e7, loga2=14.101, fl= 26.32, k = 0.25),
                    W2= dict(m1=3.0, loga1=11.107, m2=5, Nd=1e7, loga2=13.845, fl= 23.39, k = 0.25),
                    W3= dict(m1=3.0, loga1=10.970, m2=5, Nd=1e7, loga2=13.617, fl= 21.05, k = 0.25),
                    )
        
        self.name = name + '_qats'
        self.title = self.input['reference'] + f', {name}'
        self.data = self.input[name]
        self.t_ref = 25.0 # millimeters - reference thickness equal 25 mm for welded connections other than simple tubular joints. For simple tubular joints the reference thickness is 16 mm when using the T-curve. The reference thickness is equal 25 mm when other S-N curves are used for fatigue analysis of tubular joints. For bolts tref = 25 mm
        self.k = self.data['k'] # stored here since the some SN curves dont store any 
        self.SN = qats.fatigue.sn.SNCurve(name='qats SN curve, "D in air"', m1 = self.data["m1"], m2 = self.data["m2"], loga1 = self.data["loga1"], nswitch = self.data["Nd"])
        
    def miner_sum(self, stress_ranges):
        """Calculate and return the Palmgren-Miner summation of the given stress ranges 

        Args:
            stress_ranges (np.array): 2D array containing col0 = stress ranges, col1 = counts per stress range

        Returns:
            float: The miner sum as a fraction of failure capacity
        """
        return qats.fatigue.sn.minersum(stress_ranges[:,0], stress_ranges[:,1], self.SN) #takes ranges, counts, curve as input
        
    def plot_characteristics(self, info_on_plot = True):
        '''
        Uses the bilinear endurance curve to plot its characteristics / SN-plot for quick inspection 
        '''
        S = np.logspace(1.2, 2.4)
        N = self.SN.n(S)
        plt.figure(dpi=96)
        plt.loglog(N, S)
        plt.title(f'DNVGL RP-C203 SN curve in air, {self.name}')
        plt.xlabel("Number of cycles")
        plt.ylabel("Stress range (MPa)")
        plt.xlim([10**5, 10**8])
        plt.ylim([10**1.2, 10**2.4])
        plt.grid(which='both')

        fatigue_limit = self.SN.sswitch
        loga2 = self.SN.loga2
        
        if info_on_plot:
            plt.text(0.95, 0.95, f"Fatigue limit: {fatigue_limit:.1f} MPa at 1e7 cycles", horizontalalignment='right', verticalalignment='center', transform=plt.gca().transAxes, backgroundcolor='#e28743')
            plt.text(0.95, 0.87, f"Intercept of second linear curve log a2: {loga2:.3f}", horizontalalignment='right', verticalalignment='center', transform=plt.gca().transAxes, backgroundcolor='#e28743')
        else:
            # Not mandatory - TODO can be removed
            print(f"Fatigue limit: {fatigue_limit:.1f} MPa at 1e7 cycles")
            print(f"Intercept of second linear curve log a2: {loga2:.2f}")  