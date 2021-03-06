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

from time import time

def _run_simulation(cell, variable_dt=False, atol=0.001):
    '''
    Running the actual simulation in NEURON, simulations in NEURON
    are now interruptable.
    '''
    neuron.h.dt = cell.timeres_NEURON
    
    cvode = neuron.h.CVode()
    
    #don't know if this is the way to do, but needed for variable dt method
    if variable_dt:
        cvode.active(1)
        cvode.atol(atol)
    else:
        cvode.active(0)
    
    #initialize state
    neuron.h.finitialize(cell.v_init)
    
    #initialize current- and record
    if cvode.active():
        cvode.re_init()
    else:
        neuron.h.fcurrent()
    neuron.h.frecord_init()
    
    ##Starting simulation at tstart
    neuron.h.t = cell.tstartms
    
    cell._loadspikes()
    
    #print sim.time and realtime factor at intervals
    counter = 0.
    t0 = time()
    ti = neuron.h.t
    if cell.tstopms > 10000:
        interval = 1 / cell.timeres_NEURON * 1000
    else:
        interval = 1 / cell.timeres_NEURON * 100
    
    while neuron.h.t < cell.tstopms:
        neuron.h.fadvance()
        counter += 1.
        if np.mod(counter, interval) == 0:
            rtfactor = (neuron.h.t - ti) * 1E-3 / (time() - t0)
            if cell.verbose:
                print('t = {:.0f}, realtime factor: {:.3f}'.format(neuron.h.t,
                                                                    rtfactor))
            t0 = time()
            ti = neuron.h.t

def _run_simulation_with_electrode(cell, electrode=None,
                                   variable_dt=False, atol=0.001,
                                   to_memory=True, to_file=False,
                                   file_name=None, dotprodcoeffs=None):
    '''
    Running the actual simulation in NEURON.
    electrode argument used to determine coefficient
    matrix, and calculate the LFP on every time step.
    '''
    try:
        import h5py
    except:
        print('h5py not found, LFP to file not possible')
        to_file = False
        file_name = None

    # Use electrode object(s) to calculate coefficient matrices for LFP
    # calculations. If electrode is a list, then
    if cell.verbose:
        print('precalculating geometry - LFP mapping')
        
    #put electrodecoeff in a list, if it isn't already
    if dotprodcoeffs is not None:
        if type(dotprodcoeffs) != list:
            dotprodcoeffs = [dotprodcoeffs]
        electrodes = []
    else:
        #create empty list if no dotprodcoeffs are supplied
        dotprodcoeffs = []
    
    #just for safekeeping
    lendotrodcoeffs0 = len(dotprodcoeffs)
    
    #access electrode object and append dotprodcoeffs
    if electrode is not None:
        #put electrode argument in list if needed
        if type(electrode) == list:
            electrodes = electrode
        else:
            electrodes = [electrode]
        
        #calculate list of dotprodcoeffs, will try temp store of imem, tvec, LFP
        cellTvec = cell.tvec
        try:
            cellImem = cell.imem.copy()
        except:
            pass
        
        cell.imem = np.eye(cell.totnsegs)
        cell.tvec = np.arange(cell.totnsegs) * cell.timeres_python
        electrodeLFP = []   #list of electrode.LFP objects if they exist
        restoreLFP = False
        restoreCellLFP = False
        for el in electrodes:
            if hasattr(el, 'LFP'):
                LFPcopy = el.LFP
                del el.LFP
                restoreLFP = True
            if hasattr(el, 'CellLFP'):
                CellLFP = el.CellLFP
                restoreCellLFP = True
            el.calc_lfp(cell=cell)
            dotprodcoeffs.append(el.LFP.copy())
            if restoreLFP:
                del el.LFP
                el.LFP = LFPcopy
            else:
                del el.LFP
            if restoreCellLFP:
                el.CellLFP = CellLFP
            else:
                if hasattr(el, 'CellLFP'):
                    del el.CellLFP
            
        #putting back variables
        cell.tvec = cellTvec        
        try:
            cell.imem = cellImem
        except:
            del cell.imem
    elif electrode is None:
        electrodes = None
   

    # Initialize NEURON simulations of cell object    
    neuron.h.dt = cell.timeres_NEURON
    
    #integrator
    cvode = neuron.h.CVode()
    
    #don't know if this is the way to do, but needed for variable dt method
    if cell.timeres_NEURON <= 1E-8:
        cvode.active(1)
        cvode.atol(atol)
    else:
        cvode.active(0)
    
    #initialize state
    neuron.h.finitialize(cell.v_init)
    
    #initialize current- and record
    if cvode.active():
        cvode.re_init()
    else:
        neuron.h.fcurrent()
    neuron.h.frecord_init()
    
    #Starting simulation at tstartms
    neuron.h.t = cell.tstartms
    
    #load spike times from NetCon
    cell._loadspikes()
    
    #print sim.time at intervals
    counter = 0.
    tstep = 0
    t0 = time()
    ti = neuron.h.t
    if cell.tstopms > 10000:
        interval = 1 / cell.timeres_NEURON * 1000
    else:
        interval = 1 / cell.timeres_NEURON * 100
    
    #temp vector to store membrane currents at each timestep
    imem = np.empty(cell.totnsegs)
    #LFPs for each electrode will be put here during simulation
    if to_memory:
        electrodesLFP = []
        for coeffs in dotprodcoeffs:
            electrodesLFP.append(np.empty((coeffs.shape[0],
                                int(cell.tstopms / cell.timeres_NEURON) + 1)))
    #LFPs for each electrode will be put here during simulations
    if to_file:
        #ensure right ending:
        if file_name.split('.')[-1] != 'h5':
            file_name += '.h5'
        el_LFP_file = h5py.File(file_name, 'w')
        i = 0
        for coeffs in dotprodcoeffs:
            el_LFP_file['electrode{:03d}'.format(i)] = np.empty((coeffs.shape[0],
                                    int(cell.tstopms / cell.timeres_NEURON + 1)))
            i += 1
    
    #multiply segment areas with specific membrane currents later,
    #mum2 conversion factor:
    area = cell.area * 1E-2
    #run fadvance until time limit, and calculate LFPs for each timestep
    while neuron.h.t < cell.tstopms:
        if neuron.h.t >= 0:
            i = 0
            for sec in cell.allseclist:
                for seg in sec:
                    imem[i] = seg.i_membrane
                    i += 1
            #pA/mum2 -> nA conversion
            imem *= area
            
            if to_memory:
                for j, coeffs in enumerate(dotprodcoeffs):
                    electrodesLFP[j][:, tstep] = np.dot(coeffs, imem)
                    
            if to_file:
                for j, coeffs in enumerate(dotprodcoeffs):
                    el_LFP_file['electrode{:03d}'.format(j)
                                ][:, tstep] = np.dot(coeffs, imem)
            
            tstep += 1
        neuron.h.fadvance()
        counter += 1.
        if divmod(counter, interval)[1] == 0:
            rtfactor = (neuron.h.t - ti) * 1E-3 / (time() - t0)
            if cell.verbose:
                print('t = {:.0f}, realtime factor: {:.3f}'.format(neuron.h.t,
                                                                   rtfactor))
            t0 = time()
            ti = neuron.h.t
    
    try:
        #calculate LFP after final fadvance()
        i = 0
        for sec in cell.allseclist:
            for seg in sec:
                imem[i] = seg.i_membrane
                i += 1
        #pA/mum2 -> nA conversion
        imem *= area
            
        if to_memory:
            for j, coeffs in enumerate(dotprodcoeffs):
                electrodesLFP[j][:, tstep] = np.dot(coeffs, imem)
        if to_file:
            for j, coeffs in enumerate(dotprodcoeffs):
                el_LFP_file['electrode{:03d}'.format(j)
                            ][:, tstep] = np.dot(coeffs, imem)

    except:
        pass
    
    # Final step, put LFPs in the electrode object, superimpose if necessary
    # If electrode.perCellLFP, store individual LFPs
    if to_memory:
        #the first few belong to input dotprodcoeffs
        cell.dotprodresults = electrodesLFP[:lendotrodcoeffs0]
        #the remaining belong to input electrode arguments
        if electrodes is not None:
            for j, LFP in enumerate(electrodesLFP):
                if not j < lendotrodcoeffs0:
                    if hasattr(electrodes[j-lendotrodcoeffs0], 'LFP'):
                        electrodes[j-lendotrodcoeffs0].LFP += LFP
                    else:
                        electrodes[j-lendotrodcoeffs0].LFP = LFP
                    #will save each cell contribution separately
                    if electrodes[j-lendotrodcoeffs0].perCellLFP:
                        if not hasattr(electrodes[j], 'CellLFP'):
                            electrodes[j-lendotrodcoeffs0].CellLFP = []
                        electrodes[j-lendotrodcoeffs0].CellLFP.append(LFP)
                    electrodes[j-lendotrodcoeffs0].electrodecoeff = dotprodcoeffs[j]

    if to_file:
        el_LFP_file.close()


def _collect_geometry_neuron(cell):
    '''Loop over allseclist to determine area, diam, xyz-start- and
    endpoints, embed geometry to cell object'''
    
    
    areavec = np.zeros(cell.totnsegs)
    diamvec = np.zeros(cell.totnsegs)
    lengthvec = np.zeros(cell.totnsegs)
    
    xstartvec = np.zeros(cell.totnsegs)
    xendvec = np.zeros(cell.totnsegs)
    ystartvec = np.zeros(cell.totnsegs)
    yendvec = np.zeros(cell.totnsegs)
    zstartvec = np.zeros(cell.totnsegs)
    zendvec = np.zeros(cell.totnsegs)
    
    counter = 0
    
    #loop over all segments
    for sec in cell.allseclist:
        n3d = int(neuron.h.n3d())
        nseg = sec.nseg
        gsen2 = 1./2/nseg
        if n3d > 0:
            #create interpolation objects for the xyz pt3d info:
            L = np.zeros(n3d)
            x = np.zeros(n3d)
            y = np.zeros(n3d)
            z = np.zeros(n3d)
            for i in range(n3d):
                L[i] = neuron.h.arc3d(i)
                x[i] = neuron.h.x3d(i)
                y[i] = neuron.h.y3d(i)
                z[i] = neuron.h.z3d(i)
            
            #normalize as seg.x [0, 1]
            L /= sec.L
                        
            #temporary store position of segment midpoints
            segx = np.zeros(nseg)
            for i, seg in enumerate(sec):
                segx[i] = seg.x
            
            #can't be >0 which may happen due to NEURON->Python float transfer:
            segx0 = (segx - gsen2).round(decimals=6)
            segx1 = (segx + gsen2).round(decimals=6)
            
            #fill vectors with interpolated coordinates of start and end points
            xstartvec[counter:counter+nseg] = np.interp(segx0, L, x)
            xendvec[counter:counter+nseg] = np.interp(segx1, L, x)
            
            ystartvec[counter:counter+nseg] = np.interp(segx0, L, y)
            yendvec[counter:counter+nseg] = np.interp(segx1, L, y)
            
            zstartvec[counter:counter+nseg] = np.interp(segx0, L, z)
            zendvec[counter:counter+nseg] = np.interp(segx1, L, z)
                        
            #fill in values area, diam, length
            for i, seg in enumerate(sec):
                areavec[counter] = neuron.h.area(seg.x)
                diamvec[counter] = seg.diam
                lengthvec[counter] = sec.L/nseg

                counter += 1
    
    #set cell attributes
    cell.xstart = xstartvec
    cell.ystart = ystartvec
    cell.zstart = zstartvec
    
    cell.xend = xendvec
    cell.yend = yendvec
    cell.zend = zendvec
    
    cell.area = areavec
    cell.diam = diamvec
    cell.length = lengthvec

