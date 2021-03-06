#!/usr/bin/env python
'''Copyright (C) 2012 Computational Neuroscience Group, NMBU.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.'''

import numpy as np
import neuron

class PointProcess:
    '''
    Superclass on top of Synapse, StimIntElectrode, 
    just to import and set some shared variables.
    
    Arguments:
    ::
        
        cell    : LFPy.Cell object
        idx     : index of segment
        color   : color in plot (optional) 
        marker  : marker in plot (optional) 
        record_current : Must be set True for recording of pointprocess currents
        kwargs  : pointprocess specific variables passed on to cell/neuron
    '''
    def __init__(self, cell, idx, color='k', marker='o', 
                 record_current=False, **kwargs):
        '''
        cell is an LFPy.Cell object, idx index of segment. This class
        sets some variables and extracts Cartesian coordinates of a segment
        '''
        self.idx = idx
        self.color = color
        self.marker = marker
        self.record_current = record_current
        self.kwargs = kwargs
        self.update_pos(cell)

    def update_pos(self, cell):
        '''
        Extract coordinates of point-process 
        '''
        self.x = cell.xmid[self.idx]
        self.y = cell.ymid[self.idx]
        self.z = cell.zmid[self.idx]
        
class Synapse(PointProcess):
    '''
    The synapse class, pointprocesses that spawn membrane currents.
    See http://www.neuron.yale.edu/neuron/static/docs/help/neuron/neuron/mech.html#pointprocesses
    for details, or corresponding mod-files.
    
    This class is meant to be used with synaptic mechanisms, giving rise to
    currents that will be part of the membrane currents. 
    
    Usage:
    ::
        
        #!/usr/bin/env python

        import LFPy
        import pylab as pl
        
        pl.interactive(1)
        
        cellParameters = {
            'morphology' :  'morphologies/L5_Mainen96_LFPy.hoc',
            'tstopms' :     50, 
        }
        cell = LFPy.Cell(**cellParameters)

        synapseParameters = {
            'idx' : cell.get_closest_idx(x=0, y=0, z=800),
            'e' : 0,                                # reversal potential
            'syntype' : 'ExpSyn',                   # synapse type
            'tau' : 2,                              # syn. time constant
            'weight' : 0.01,                        # syn. weight
            'record_current' : True                 # syn. current record
        }
        synapse = LFPy.Synapse(cell, **synapseParameters)
        synapse.set_spike_times(pl.array([10, 15, 20, 25]))
        cell.simulate(rec_isyn=True)
        
        pl.subplot(211)
        pl.plot(cell.tvec, synapse.i)
        pl.title('Synapse current (nA)')
        pl.subplot(212)
        pl.plot(cell.tvec, cell.somav)
        pl.title('Somatic potential (mV)')
        
    '''
    def __init__(self, cell, idx, syntype, color='r', marker='o',
                 record_current=False, **kwargs):
        '''
        Initialization of class Synapse
        '''
        PointProcess.__init__(self, cell, idx, color, marker, record_current, 
                              **kwargs)
            
        self.syntype = syntype
        self.cell = cell
        self.hocidx = int(cell.set_synapse(idx, syntype,
                                           record_current, **kwargs))
        cell.synapses.append(self)
        cell.synidx.append(idx)

    def set_spike_times(self, sptimes=np.zeros(0)):
        '''Set the spike times explicitly using numpy arrays'''
        self.sptimes = sptimes
        self.cell.sptimeslist.append(sptimes)
    
    def set_spike_times_w_netstim(self, noise=1., start=0., number=1E3,
                                  interval=10., seed=1234.):
        '''
        Generate a train of pre-synaptic stimulus times by setting up the
        neuron NetStim object associated with this synapse
        
        kwargs:
        ::

            noise : float in [0, 1]
                Fractional randomness, from deterministic to intervals that drawn
                from negexp distribution (Poisson spiketimes).
            start : float
                ms, (most likely) start time of first spike
            number : int
                (average) number of spikes
            interval : float
                ms, (mean) time between spikes
            seed : float
                random seed value
        '''
        self.cell.netstimlist[-1].noise = noise
        self.cell.netstimlist[-1].start = start
        self.cell.netstimlist[-1].number = number
        self.cell.netstimlist[-1].interval = interval        
        self.cell.netstimlist[-1].seed(seed)

    def collect_current(self, cell):
        '''Collect synapse current'''
        try:
            self.i = np.array(cell.synireclist.o(self.hocidx))
        except:
            raise Exception('cell.synireclist deleted from consequtive runs')
    
    def collect_potential(self, cell):
        '''Collect membrane potential of segment with synapse'''
        try:
            self.v = np.array(cell.synvreclist.o(self.hocidx))
        except:
            raise Exception('cell.synvreclist deleted from consequtive runs')
        
class StimIntElectrode(PointProcess):
    '''
    Class for NEURON point processes, ie VClamp, SEClamp and ICLamp,
    SinIClamp, ChirpIClamp with arguments.
    Electrode currents go here.
    Membrane currents will no longer sum to zero if these mechanisms are used.
    
    Refer to NEURON documentation @ neuron.yale.edu for kwargs
            
    Usage example:
    ::
        
        #/usr/bin/python
        
        import LFPy
        import pylab as pl

        pl.interactive(1)
        
        #define a list of different electrode implementations from NEURON
        pointprocesses = [
            {
                'idx' : 0,
                'record_current' : True,
                'pptype' : 'IClamp',
                'amp' : 1,
                'dur' : 20,
                'delay' : 10,
            },
            {
                'idx' : 0,
                'record_current' : True,
                'pptype' : 'VClamp',
                'amp[0]' : -65,
                'dur[0]' : 10,
                'amp[1]' : 0,
                'dur[1]' : 20,
                'amp[2]' : -65,
                'dur[2]' : 10,
            },
            {
                'idx' : 0,
                'record_current' : True,
                'pptype' : 'SEClamp',
                'dur1' : 10,
                'amp1' : -65,
                'dur2' : 20,
                'amp2' : 0,
                'dur3' : 10,
                'amp3' : -65,
            },
        ]
        
        #create a cell instance for each electrode
        for pointprocess in pointprocesses:
            cell = LFPy.Cell(morphology='morphologies/L5_Mainen96_LFPy.hoc')
            stimulus = LFPy.StimIntElectrode(cell, **pointprocess)
            cell.simulate(rec_istim=True)
            
            pl.subplot(211)
            pl.plot(cell.tvec, stimulus.i, label=pointprocess['pptype'])
            pl.legend(loc='best')
            pl.title('Stimulus currents (nA)')
            
            pl.subplot(212)
            pl.plot(cell.tvec, cell.somav, label=pointprocess['pptype'])
            pl.legend(loc='best')
            pl.title('Somatic potential (mV)')
    '''    
    def __init__(self, cell, idx, pptype='SEClamp',
                 color='p', marker='*', record_current=False, **kwargs):
        '''
        Will insert pptype on
        cell-instance, pass the corresponding kwargs onto
        cell.set_point_process.
        '''
        PointProcess.__init__(self, cell, idx, color, marker, record_current)
        self.pptype = pptype
        self.hocidx = int(cell.set_point_process(idx, pptype,
                                                 record_current, **kwargs))
        cell.pointprocesses.append(self)
        cell.pointprocess_idx.append(idx)

    def collect_current(self, cell):
        '''
        Fetch electrode current from recorder list
        '''
        self.i = np.array(cell.stimireclist.o(self.hocidx))
    
    def collect_potential(self, cell):
        '''
        Collect membrane potential of segment with PointProcess
        '''
        self.v = np.array(cell.synvreclist.o(self.hocidx))


class PointProcessPlayInSoma(object):
    '''
    Sets an interpolated voltage trace as a boundary condition for the
    soma compartment. Could for instance be used to play back an action
    potential waveform as in Pettersen & Einevoll (2008) Biophys J 94.
    '''
    def __init__(self, soma_trace):
        '''
        Class for playing back somatic trace at specific time points
        into soma as boundary condition for the membrane voltage
        
        Parameters:
        ::
            
            soma_trace : file, contains time (column 1) and voltage (column 2)
                values, as floats in units of ms and mV respectively, separated
                by space.
        
        Example:
        ::
            
            from pylab import * # populate namespace with math and plot functions
            import LFPy
            import neuron
            
            # create cell
            cell = LFPy.Cell(morphology='morphologies/example_morphology.hoc')
            
            # create 'action potential trace' as gaussian pulse, save to file
            t = arange(0, 10., cell.timeres_python)
            sigma = 0.5
            v = exp(-(t-5.)**2 / (2*sigma**2))*100.
            savetxt('vtrace.txt', zip(t, v))
            
            # set voltage trace as boundary condition in soma
            stim = LFPy.pointprocess.PointProcessPlayInSoma('vtrace.txt')
            stim.set_play_in_soma(cell, t_on = array([10., 50.]))
            
            # simulate, record transmembrane currents
            cell.simulate(rec_imem=True, rec_vmem=True)
            
            subplot(311)
            plot(cell.tvec, cell.somav)
            subplot(312)
            imshow(cell.imem, interpolation='nearest')
            axis('tight')
            colorbar(orientation='horizontal')
            subplot(313)
            imshow(cell.vmem, interpolation='nearest')
            axis('tight')
            colorbar(orientation='horizontal')
            show()            
        '''
        self.soma_trace = soma_trace
    
    def set_play_in_soma(self, cell, t_on=np.array([0])):
        '''
        Set mechanisms for playing soma trace at time(s) t_on,
        where t_on is a np.array
        '''
        if type(t_on) != np.ndarray:
            t_on = np.array(t_on)
        
        f = file(self.soma_trace)
        x = []
        for line in f.readlines():
            x.append(list(map(float, line.split())))
        x = np.array(x)
        X = x.T
        f.close()
        
        #time and values for trace, shifting
        tTrace = X[0, ]
        tTrace -= tTrace[0]
        
        trace = X[1, ]
        trace -= trace[0]
        trace += cell.e_pas
        
        #creating trace
        somaTvec0 = tTrace
        somaTvec0 += t_on[0]
        somaTvec = somaTvec0
        somaTrace = trace
        
        for i in range(1, t_on.size):
            somaTvec = np.concatenate((somaTvec, somaTvec0 + t_on[i]))
            somaTrace = np.concatenate((somaTrace, trace))
                
        somaTvecVec = np.interp(np.arange(somaTvec[0], somaTvec[-1], 
                                cell.timeres_NEURON),
                                somaTvec, somaTvec)
        somaTraceVec = np.interp(np.arange(somaTvec[0], somaTvec[-1],
                                cell.timeres_NEURON),
                                somaTvec, somaTrace)
        
        for sec in neuron.h.soma:
            #ensure that soma is perfect capacitor
            sec.cm = 1E9
        
        #call function that insert trace on soma
        self._play_in_soma(somaTvecVec, somaTraceVec)
            
    def _play_in_soma(self, somaTvecVec, somaTraceVec):
        '''
        Replacement of LFPy.hoc "proc play_in_soma()",
        seems necessary that this function lives in hoc
        '''
        neuron.h('objref soma_tvec, soma_trace')
        
        neuron.h('soma_tvec = new Vector()')
        neuron.h('soma_trace = new Vector()')
        
        neuron.h.soma_tvec.from_python(somaTvecVec)
        neuron.h.soma_trace.from_python(somaTraceVec)
        
        neuron.h('soma_trace.play(&soma.v(0.5), soma_tvec)')
