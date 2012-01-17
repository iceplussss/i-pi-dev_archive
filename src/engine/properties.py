"""Holds the class which computes required simple properties.

Classes:
   Properties: This is the class that holds all the algorithms to calculate
      the important properties that should be output.
"""

__all__ = ['properties']

import numpy as np
import math, random
from utils.depend import *
from utils.units import Constants
from utils.mathtools import h2abc
from atoms import *
from cell import *
from ensembles import *
from forces import *

_DEFAULT_FINDIFF = 1e-5
_DEFAULT_FDERROR = 1e-9
_DEFAULT_MINFID = 1e-12
class Properties(dobject):
   """A proxy to compute and output properties of the system.

   Takes the fundamental properties calculated during the simulation, and 
   prepares them for output. It also contains simple algorithms to calculate
   other properties not calculated during the simulation itself, so that 
   these can also be output.

   Attributes:
      _DEFAULT_FINDIFF: A float giving the size of the finite difference
         parameter used in the Yamamoto kinetic energy estimator.
      fd_delta: Equivalent to _DEFAULT_FINDIFF.
      _DEFAULT_FDERROR: A float giving the size of the minimum precision 
         allowed for the finite difference calculation in the Yamamoto kinetic
         energy estimator.
      _DEFAULT_MINFID: A float giving the maximum displacement in the Yamamoto 
         kinetic energy estimator.
      dbeads: A dummy Beads object used in the Yamamoto kinetic energy
         estimator.
      dforces: A dummy Forces object used in the Yamamoto kinetic energy
         estimator.
      simul: The Simulation object containing the data to be output.
      ensemble: The Ensemble object in simul.
      beads: The Beads object in simul.
      cell: The Cell object in simul.
      forces: The Forces object in simul.
      property_dict: A dictionary containing all the properties that can be
         output.
      time: A float giving the time passed in the simulation.
      econs: A float giving the conserved quantity.
      kin: A float giving the classical kinetic energy estimator.
      pot: A float giving the potential energy estimator.
      temp: A float giving the classical kinetic temperature estimator.
      cell_params: A list giving the lengths of the cell box and the angles
         between them.
      stress: An array giving the components of the classical stress tensor
         estimator.
      press: A float giving the classical pressure estimator.
      kin_cv: A float giving the quantum centroid virial kinetic energy 
         estimator.
      kstress_cv: An array giving the components of the quantum centroid virial
         kinetic stress tensor estimator.
      stress_cv: An array giving the components of the quantum centroid virial
         stress tensor estimator.
      press_cv: A float giving the quantum centroid virial pressure estimator.
      kin_yama: A float giving the quantum displaced path estimator for the
         kinetic energy.
   """

   def __init__(self):
      """Initialises Properties."""

      self.property_dict = {}
      self.fd_delta = -_DEFAULT_FINDIFF
      
   def bind(self, simul):
      """Binds the necessary objects from the simulation to calculate the
      required properties.

      This function takes the appropriate simulation object, and creates the
      property_dict object which holds all the objects which can be output.
      It is given by: 
      {'time': time elapsed,
      'conserved': conserved quantity,
      'kinetic_md': classical kinetic energy estimator,
      'potential': potential energy estimator,
      'temperature': classical kinetic temperature estimator,
      'cell_parameters': simulation box lengths and the angles between them,
      'V': simulation box volume,
      'stress_md.xx': the xx component of the classical stress tensor estimator,
      'pressure_md': classical pressure estimator
      'kinetic_cv': quantum centroid virial kinetic energy estimator,
      'stress_cv.xx': xx component of the quantum centroid virial estimator of 
         the stress tensor,
      'pressure_cv': quantum centroid virial pressure estimator
      'kinetic_yamamoto': quantum displaced path kinetic energy estimator}.

      Args:
         simul: The Simulation object to be bound.
      """

      self.ensemble = simul.ensemble
      self.beads = simul.beads
      self.cell = simul.cell
      self.forces = simul.forces
      self.simul = simul      

      dset(self, "time", depend_value(name="time",  func=self.get_time, dependencies=[dget(self.simul,"step"), dget(self.ensemble,"dt")]))
      self.property_dict["time"] = dget(self,"time")
      
      dset(self, "econs", depend_value(name="econs", func=self.get_econs, dependencies=[dget(self.ensemble,"econs")]))
      self.property_dict["conserved"] = dget(self,"econs")
      
      dset(self, "kin", depend_value(name="kin", func=self.get_kin, dependencies=[dget(self.beads,"kin"),dget(self.cell,"kin")]))
      self.property_dict["kinetic_md"] = dget(self,"kin")
      
      dset(self, "pot", depend_value(name="pot", func=self.get_pot, dependencies=[dget(self.forces,"pot")]))      
      self.property_dict["potential"] = dget(self,"pot")

      dset(self, "temp", depend_value(name="temp", func=self.get_temp, dependencies=[dget(self.beads,"kin")]))      
      self.property_dict["temperature"] = dget(self,"temp")     
     
      self.property_dict["V"] = dget(self.cell,"V")
      dset(self, "cell_params", depend_value(name="cell_params", func=self.get_cell_params, dependencies=[dget(self.cell, "h")]))
      self.property_dict["cell_parameters"] = dget(self,"cell_params")

      dset(self, "stress", depend_value(name="stress", func=self.get_stress, dependencies=[dget(self.beads, "kstress"), dget(self.forces, "vir"), dget(self.cell, "V")]))
      self.property_dict["stress_md.xx"] = depend_value(name="scl_xx", dependencies=[dget(self, "stress")], func=(lambda : self.stress[0,0]) ) 
      
      dset(self, "press", depend_value(name="press", func=self.get_press, dependencies=[dget(self,"stress")]))
      self.property_dict["pressure_md"] = dget(self,"press")

      dset(self, "kin_cv", depend_value(name="kin_cv", func=self.get_kincv, dependencies=[dget(self.beads,"q"),dget(self.forces,"f"),dget(self.ensemble,"temp")]))
      self.property_dict["kinetic_cv"] = dget(self,"kin_cv")

      dset(self, "kstress_cv", depend_value(name="kstress_cv", func=self.get_kstresscv, dependencies=[dget(self.beads,"q"),dget(self.forces,"f"),dget(self.ensemble,"temp")]))
      dset(self, "stress_cv", depend_value(name="stress_cv", func=self.get_stresscv, dependencies=[dget(self,"kstress_cv"),dget(self.forces,"vir"), dget(self.cell, "V")]))
      self.property_dict["stress_cv.xx"] = depend_value(name="scv_xx", dependencies=[dget(self, "stress_cv")], func=(lambda : self.stress_cv[0,0]) ) 
      dset(self, "press_cv", depend_value(name="press_cv", func=self.get_presscv, dependencies=[dget(self,"stress_cv")]))
      self.property_dict["pressure_cv"] = dget(self,"press_cv")
      
      self.dbeads = simul.beads.copy()
      self.dforces = ForceBeads()
      self.dforces.bind(self.dbeads, self.simul.cell,  self.simul._forcemodel)     
      dset(self, "kin_yama", depend_value(name="kin_yama", func=self.get_kinyama, dependencies=[dget(self.beads,"q"),dget(self.ensemble,"temp")]))
      self.property_dict["kinetic_yamamoto"] = dget(self,"kin_yama")
      
   def get_kin(self):
      """Calculates the classical kinetic energy estimator."""

      return self.beads.kin/self.beads.nbeads

   def get_time(self):
      """Calculates the elapsed simulation time."""

      return (1 + self.simul.step)*self.ensemble.dt

   def __getitem__(self,key):
      """Retrieves the item given by key.

      Args:
         key: A string contained in property_dict.
      """

      return self.property_dict[key].get()

   def get_pot(self):
      """Calculates the potential energy estimator."""

      return self.forces.pot/self.beads.nbeads

   def get_temp(self):
      """Calculates the classical kinetic temperature estimator."""

      return self.beads.kin/(0.5*Constants.kb*(3*self.beads.natoms*self.beads.nbeads - (3 if self.ensemble.fixcom else 0))*self.beads.nbeads)

   def get_econs(self):
      """Calculates the conserved quantity estimator."""

      return self.ensemble.econs/self.beads.nbeads

   def get_stress(self):
      """Calculates the classical kinetic energy estimator."""

      return (self.forces.vir + self.beads.kstress)/self.cell.V

   def get_press(self):
      """Calculates the classical pressure estimator."""

      return np.trace(self.stress)/3.0

   def get_stresscv(self):
      """Calculates the quantum central virial stress tensor estimator."""

      return (self.forces.vir + self.kstress_cv)/self.cell.V                  

   def get_presscv(self):
      """Calculates the quantum central virial pressure estimator."""

      return np.trace(self.stress_cv)/3.0
   
   def get_kincv(self):        
      """Calculates the quantum central virial kinetic energy estimator."""

      kcv=0.0
      for b in range(self.beads.nbeads):
         kcv += np.dot(depstrip(self.beads.q[b]) - depstrip(self.beads.qc), depstrip(self.forces.f[b]))
      kcv *= -0.5/self.beads.nbeads
      kcv += 0.5*Constants.kb*self.ensemble.temp*(3*self.beads.natoms) 
      return kcv

   def get_kstresscv(self):        
      """Calculates the quantum central virial kinetic stress tensor 
      estimator.
      """

      kst=np.zeros((3,3),float)
      q=depstrip(self.beads.q)
      qc=depstrip(self.beads.qc)
      na3=3*self.beads.natoms;
      for b in range(self.beads.nbeads):
         for i in range(3):
            for j in range(i,3):
               kst[i,j] += np.dot(q[b,i:na3:3] - qc[i:na3:3], depstrip(self.forces.f[b])[j:na3:3])

      kst *= -1/self.beads.nbeads
      for i in range(3): kst[i,i] += Constants.kb*self.ensemble.temp*(3*self.beads.natoms) 
      return kst

   def get_kinyama(self):              
      """Calculates the quantum displaced path kinetic energy estimator."""
      
      dbeta = abs(self.fd_delta)
      
      v0 = self.pot
      while True: 
         splus = math.sqrt(1.0 + dbeta)
         sminus = math.sqrt(1.0 - dbeta)
         
         for b in range(self.beads.nbeads):
            self.dbeads[b].q = self.beads.centroid.q*(1.0 - splus) + splus*self.beads[b].q
         vplus = self.dforces.pot/self.beads.nbeads
         
         for b in range(self.beads.nbeads):
            self.dbeads[b].q = self.beads.centroid.q*(1.0 - sminus) + sminus*self.beads[b].q      
         vminus = self.dforces.pot/self.beads.nbeads

         kyama = ((1.0 + dbeta)*vplus - (1.0 - dbeta)*vminus)/(2*dbeta) - v0
         kyama += 0.5*Constants.kb*self.ensemble.temp*(3*self.beads.natoms) 
         if (self.fd_delta < 0 and abs((vplus + vminus)/(v0*2) - 1.0) > _DEFAULT_FDERROR and dbeta > _DEFAULT_MINFID):
            dbeta *= 0.5
            print "Reducing displacement in Yamamoto kinetic estimator"
            continue
         else:
            break
         
      return kyama
         
   def get_cell_params(self):
      """Returns a list of the cell box lengths and the angles between them."""

      a, b, c, alpha, beta, gamma = h2abc(self.cell.h)
      return [a, b, c, alpha, beta, gamma]

