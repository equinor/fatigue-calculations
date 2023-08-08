import numpy as np
import matplotlib.pyplot as plt
import qats
import sys

'''
Implementation of SN curves using qats package
'''

class SN_Curve_qats:  
    
    def __init__(self, name):
        self.free = dict(
            reference = "DNVGL-RP-C203 - Edition April 2016, Table 2-4 S-N curves in seawater for free corrosion",
            B1 = dict(m=3.0, loga=12.436, k=0.00),
            B2 = dict(m=3.0, loga=12.262, k=0.00),
            C  = dict(m=3.0, loga=12.115, k=0.15),
            C1 = dict(m=3.0, loga=11.972, k=0.15),
            C2 = dict(m=3.0, loga=11.824, k=0.15),
            D  = dict(m=3.0, loga=11.687, k=0.20),
            E  = dict(m=3.0, loga=11.533, k=0.20),
            F  = dict(m=3.0, loga=11.378, k=0.25),
            F1 = dict(m=3.0, loga=11.222, k=0.25),
            F3 = dict(m=3.0, loga=11.068, k=0.25),
            G  = dict(m=3.0, loga=10.921, k=0.25),
            W1 = dict(m=3.0, loga=10.784, k=0.25),
            W2 = dict(m=3.0, loga=10.630, k=0.25),
            W3 = dict(m=3.0, loga=10.493, k=0.25),
        )
        self.cath = dict(
            reference = "DNVGL-RP-C203 - Edition April 2016, Table 2-2 S-N curves in seawater with cathodic protection",
            B1 = dict(m1=4.0, loga1=14.917, m2=5, Nd=1e6, loga2=17.146, fl=106.97, k=0.00),
            B2 = dict(m1=4.0, loga1=14.685, m2=5, Nd=1e6, loga2=16.856, fl= 93.59, k=0.00),
            C  = dict(m1=3.0, loga1=12.192, m2=5, Nd=1e6, loga2=16.320, fl= 73.10, k=0.05),
            C1 = dict(m1=3.0, loga1=12.049, m2=5, Nd=1e6, loga2=16.081, fl= 65.50, k=0.10),
            C2 = dict(m1=3.0, loga1=11.901, m2=5, Nd=1e6, loga2=15.835, fl= 58.48, k=0.15),
            D  = dict(m1=3.0, loga1=11.764, m2=5, Nd=1e6, loga2=15.606, fl= 52.63, k=0.20),
            E  = dict(m1=3.0, loga1=11.610, m2=5, Nd=1e6, loga2=15.350, fl= 46.78, k=0.20),
            F  = dict(m1=3.0, loga1=11.455, m2=5, Nd=1e6, loga2=15.091, fl= 41.52, k=0.25),
            F1 = dict(m1=3.0, loga1=11.299, m2=5, Nd=1e6, loga2=14.832, fl= 36.84, k=0.25),
            F3 = dict(m1=3.0, loga1=11.146, m2=5, Nd=1e6, loga2=14.576, fl= 32.75, k=0.25),
            G  = dict(m1=3.0, loga1=10.998, m2=5, Nd=1e6, loga2=14.330, fl= 29.24, k=0.25),
            W1 = dict(m1=3.0, loga1=10.861, m2=5, Nd=1e6, loga2=14.101, fl= 26.32, k=0.25),
            W2 = dict(m1=3.0, loga1=10.707, m2=5, Nd=1e6, loga2=13.845, fl= 23.39, k=0.25),
            W3 = dict(m1=3.0, loga1=10.570, m2=5, Nd=1e6, loga2=13.617, fl= 21.05, k=0.25),
        )
        self.air = dict(
            reference = "DNVGL-RP-C203 Ed.: Apr 2016, Tab. 2-1 S-N curves in air",
            B1 = dict(m1=4.0, loga1=15.117, m2=5, Nd=1e7, loga2=17.146, fl=106.97, k=0.00),
            B2 = dict(m1=4.0, loga1=14.885, m2=5, Nd=1e7, loga2=16.856, fl= 93.59, k=0.00),
            C  = dict(m1=3.0, loga1=12.592, m2=5, Nd=1e7, loga2=16.320, fl= 73.10, k=0.05),
            C1 = dict(m1=3.0, loga1=12.449, m2=5, Nd=1e7, loga2=16.081, fl= 65.50, k=0.10),
            C2 = dict(m1=3.0, loga1=12.301, m2=5, Nd=1e7, loga2=15.835, fl= 58.48, k=0.15),
            D  = dict(m1=3.0, loga1=12.164, m2=5, Nd=1e7, loga2=15.606, fl= 52.63, k=0.20),
            E  = dict(m1=3.0, loga1=12.010, m2=5, Nd=1e7, loga2=15.350, fl= 46.78, k=0.20),
            F  = dict(m1=3.0, loga1=11.855, m2=5, Nd=1e7, loga2=15.091, fl= 41.52, k=0.25),
            F1 = dict(m1=3.0, loga1=11.699, m2=5, Nd=1e7, loga2=14.832, fl= 36.84, k=0.25),
            F3 = dict(m1=3.0, loga1=11.546, m2=5, Nd=1e7, loga2=14.576, fl= 32.75, k=0.25),
            G  = dict(m1=3.0, loga1=11.398, m2=5, Nd=1e7, loga2=14.330, fl= 29.24, k=0.25),
            W1 = dict(m1=3.0, loga1=11.261, m2=5, Nd=1e7, loga2=14.101, fl= 26.32, k=0.25),
            W2 = dict(m1=3.0, loga1=11.107, m2=5, Nd=1e7, loga2=13.845, fl= 23.39, k=0.25),
            W3 = dict(m1=3.0, loga1=10.970, m2=5, Nd=1e7, loga2=13.617, fl= 21.05, k=0.25),
            Dg = dict(m1=3.5, loga1=13.540, m2=5, Nd=1e7, loga2=16.343, fl= 00.10, k=0.15), # Table F-9 S-N curves for improved details by grinding or hammer peening in air environment
        )
        
        classes = {'air': self.air, 'cath': self.cath, 'free': self.free}
        
        assert '-' in name, "Check init naming"
        curve_class, curve_type = [s.lower() for s in name.split('-')]
        
        try:
            self.input = classes[curve_type]
        except KeyError as err:
            print(f'Caught a key error: {err}, not in classes {classes.keys()}. Please check implementation of SN curve to see which types are supported. Exiting.')
            sys.exit()
        
        self.input = {key.lower(): val for key, val in self.input.items()} # make everything lower case to avoid key errors based on any manual input 
        
        try:   
            self.data = self.input[curve_class]
        except KeyError as err:
            print(f'Caught a key error: {err}. Checking for double lettered input')
            if curve_class not in self.air.keys(): # handle cases where eg. "Dg-Air" is passed to constructor
                if len(curve_class) > 1.0:
                    curve_class = curve_class[0]
                    try:
                        self.data = self.input[curve_class]
                        print(f'Interpreted {err} as {curve_class}. Continuing.')
                    except KeyError as err:
                        print(f'Caught a key error: {err}. Please check the keyword you are creating the curve with. Exiting.')
                        sys.exit()
                
        self.input = {k.lower(): v for k, v in self.input.items()} # make all keys lower case
        self.curve_type = curve_type
        self.title = self.input['reference'] + f', {curve_class}'
        self.t_ref = 25.0 # millimeters - reference thickness equal 25 mm for welded connections other than simple tubular joints. For simple tubular joints the reference thickness is 16 mm when using the T-curve. The reference thickness is equal 25 mm when other S-N curves are used for fatigue analysis of tubular joints. For bolts tref = 25 mm
        self.k = self.data['k'] # stored here since the some SN curves dont store any -> thickness exponent on fatigue strength
        
        if curve_type == 'free':
            self.SN = qats.fatigue.sn.SNCurve(name=f'{curve_class}-{curve_type}',
                                          m1 = self.data["m"], # only parameter needed for free 
                                          loga1 = self.data["loga"]
                                          )
        else: 
            self.SN = qats.fatigue.sn.SNCurve(name=f'{curve_class}-{curve_type}',
                                          m1 = self.data["m1"], # slope for N <= Nd cycles
                                          m2 = self.data["m2"], # slope for N > Nd cycles
                                          loga1 = self.data["loga1"], # crossing point for one linear curve
                                          nswitch = self.data["Nd"])
        
    def miner_sum(self, stress_ranges):
        """Calculate and return the Palmgren-Miner summation of the given stress ranges 

        Args:
            stress_ranges (np.array): 2D array containing col0 = stress ranges, col1 = counts per stress range

        Returns:
            float: The miner sum as a fraction of failure capacity (if >= 1, material fails)
        """
        return qats.fatigue.sn.minersum(stress_ranges[:,0], stress_ranges[:,1], self.SN) #takes ranges, counts, curve as input
        
    def plot_characteristics(self, info_on_plot = True):
        """Plots how the SN_curve looks as a function of stress and cycles

        Args:
            info_on_plot (bool, optional): switch to show textual highlights on the plot or not. Defaults to True.
        """
        
        S_upper = 3
        S_lower = 1
        S = np.logspace(S_lower, S_upper)
        N = self.SN.n(S)
        
        if self.curve_type in ['air', 'cath']:
            '''
            Uses the bilinear endurance curve to plot its characteristics / SN-plot for quick inspection 
            '''
            
            plt.loglog(N, S, label = self.SN.name)
            plt.title(f'DNVGL RP-C203 SN curve in air, {self.SN.name}')
            plt.xlabel("Number of cycles")
            plt.ylabel("Stress range (MPa)")
            
            plt.ylim([10**S_lower, 10**S_upper])
            plt.xlim([1e4, 1e8])
            plt.grid(which='both')

            fatigue_limit = self.SN.sswitch
            loga2 = self.SN.loga2
            
            if info_on_plot:
                plt.text(0.95, 0.95, f"Fatigue limit: {self.SN.fatigue_strength(1e7):.1f} MPa at {1e7:.1e} cycles", horizontalalignment='right', verticalalignment='center', transform=plt.gca().transAxes, backgroundcolor='#e28743')
                plt.text(0.95, 0.87, f"Intercept of second linear curve log a2: {loga2:.3f}", horizontalalignment='right', verticalalignment='center', transform=plt.gca().transAxes, backgroundcolor='#e28743')
            else:
                print(f"Fatigue limit: {fatigue_limit:.1f} MPa at {self.SN.nswitch:.1e} cycles")
                print(f"Intercept of second linear curve log a2: {loga2:.2f}")  
                
        else:
            plt.loglog(N, S, "k", lw=.5)
            plt.text(2e6, self.SN.fatigue_strength(2e6), "{0:2s}".format(self.title), fontsize=5.5, ha='center', va='center', bbox={'fc':'w', 'ec':(0, 0, 0, 0), 'pad':0})
            plt.grid(which='both')
            plt.title("S-N curve in seawater for free corrosion")
            plt.xlabel("Number of cycles")
            plt.ylabel("Stress range (MPa)")
            plt.ylim([10**S_lower, 10**S_upper])
            plt.xlim([1e4, 1e8])
            
            
if __name__ == '__main__':
    
    
    # The code below is for testing against reported values
    curve = SN_Curve_qats('d-cath')
    D = 8.456
    t = 72. / 1000
    DFF = 3.0
    SCF = 1.14
    grit = 1.00
    t_eff = 61.
    alpha = max(1.0, (t_eff / curve.t_ref)**curve.k)
    in_out = 'i'
    
    # All vals below are in 1e6
    if in_out == 'o':
        A = np.pi * ((D/2)**2 - ((D - 2*t)/2)**2) # [m**2] Area in the plane of the current circular, holed geometry 
        I = np.pi / 64.0 * (D**4 - (D - 2*t)**4) # [m**4]
        Z = I / (D / 2)
    else:
        out_D = D + 2 * t
        A = np.pi * (((out_D)/2)**2 - ((out_D - 2*t)/2)**2)
        I = np.pi / 64.0 * (out_D**4 - (D)**4)
        Z = I / (D / 2)

    M = 124.5 # MPa    
    N = 10e6 # cycles
    
    S = M / Z
    Shs = S * SCF * grit
    
    util = curve.miner_sum(np.array([[Shs * alpha, N]])) * DFF
    
    print(f'M {M:.2f}, S {S:.2f}, Shs {Shs:.2f}, alpha = {alpha:.3f}, util {util * 100:.1f}')
    