
import numpy as np
import matplotlib.pyplot as plt 
import fatpack 

def plot_inspection_of_single_stress_timeseries(y, N, S, cycles, reversals_ix, curve):
    
    '''
    y is the actual stress time series
    N is the rainflow bins calculated previously 
    '''

    n_rainflow_bins = N.shape[0]
    fig = plt.figure()

    # Plotting signal with reversals for demonstrating the reversal findings
    ax_signal = plt.subplot2grid((3, 2), (0, 0))
    ax_signal.plot(y)
    ax_signal.plot(reversals_ix, y[reversals_ix], 'ro', fillstyle='none', label='reversal')
    ax_signal.legend()
    ax_signal.set(title="Timeseries with found reversals", ylabel="Stress [Mpa]", xlabel="Timestep no.")

    # Plotting the cumulative distribution of the cycle count
    ax_cumdist = plt.subplot2grid((3, 2), (1, 0)) 
    Ncum = N.sum() - np.cumsum(N)  # Sum of all bins keeping track of how many cycles we have left in the distribution - naturally low for a single timeseries of 10 min since we are no way near the lifetime of cycles 
    ax_cumdist.semilogx(Ncum, S)
    ax_cumdist.set(title=f"Cumulative distribution for rainflow stress_ranges in {n_rainflow_bins} bins", xlabel="Count, N", ylabel="Range, S")

    # Plotting the rainflow matrix of the total cycle count
    ax_rfcmat = plt.subplot2grid((3, 2), (0, 1), rowspan=2, aspect='equal')
    bins = np.linspace(cycles.min(), cycles.max(), n_rainflow_bins)
    rfcmat = fatpack.find_rainflow_matrix(cycles, bins, bins)
    X, Y = np.meshgrid(bins, bins, indexing='ij')
    C = ax_rfcmat.pcolormesh(X, Y, rfcmat, cmap='magma')
    fig.colorbar(C)
    ax_rfcmat.set(title="Rainflow matrix", xlabel="Cycle start point", ylabel="Cycle end point")

    ax = plt.subplot2grid((3, 2), (2, 0))
    N_SN = np.logspace(6, 9)
    S_SN = curve.SN.get_stress(N_SN)

    ax.loglog(N_SN, S_SN)
    ax.set(ylim=(10., 1000.), title = f"{curve.title}", xlabel="N / Endurance [cycles]", ylabel = "dsigma / Stress Range [Mpa]")
    ax.grid()
    ax.grid(which='both')
    fig.tight_layout()