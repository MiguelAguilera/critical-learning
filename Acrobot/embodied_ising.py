import numpy as np
from itertools import combinations
import matplotlib.pyplot as plt
from acrobot import AcrobotEnv


class ising:
	#Initialize the network
	def __init__(self, netsize,Nsensors=1,Nmotors=1):	#Create ising model
	
		self.size=netsize
		self.Ssize=Nsensors			#Number of sensors
		self.Msize=Nmotors			#Number of sensors
		
		self.h=np.zeros(netsize)
		self.J=np.zeros((netsize,netsize))
		self.max_weights=2
		self.randomize_state()
		
		self.env = AcrobotEnv()
		mass=1.75
		self.set_mass(mass)
		self.observation = self.env.reset()
		self.randomize_position()
		
		self.Beta=1.0
		self.defaultT=max(100,netsize*20)
		self.maxspeed=self.env.MAX_VEL_1
		self.minspeed=-self.env.MAX_VEL_1
		self.maxspeed2=self.env.MAX_VEL_2
		self.minspeed2=-self.env.MAX_VEL_2
		self.maxacc=5
		self.minacc=-5
		self.maxheight=2
		self.minheight=-2
		self.Ssize1=int(np.floor(self.Ssize/2))
			
		self.Update(0)
		
		
	def get_state(self,mode='all'):
		if mode=='all':
			return self.s
		elif mode=='motors':
			return self.s[-self.Msize:]
		elif mode=='sensors':
			return self.s[0:self.Ssize]
		elif mode=='hidden':
			return self.s[self.Ssize:-self.Msize]
		elif mode=='non-sensors':
			return self.s[self.Ssize:]
			
	def get_state_index(self,mode='all'):
		return bool2int(0.5*(self.get_state(mode)+1))
			
	def set_mass(self,mass=1):
		self.env.LINK_MASS_1=mass
		self.env.LINK_MASS_2=mass
	#Randomize the state of the network
	def randomize_state(self):
		self.s = np.random.randint(0,2,self.size)*2-1

	def randomize_position(self):
		self.observation = self.env.reset()
		self.theta1_dot=0
		
	#Set random bias to sets of units of the system
	def random_fields(self,max_weights=None):
		if max_weights is None:
			max_weights=self.max_weights
		self.h[self.Ssize:]=max_weights*(np.random.rand(self.size-self.Ssize)*2-1)		
		
	#Set random connections to sets of units of the system
	def random_wiring(self,max_weights=None):	#Set random values for h and J
		if max_weights is None:
			max_weights=self.max_weights
		for i in range(self.size):
			for j in np.arange(i+1,self.size):
				if i<j and (i>=self.Ssize or j>=self.Ssize):
					self.J[i,j]=(np.random.rand(1)*2-1)*self.max_weights
		
	def Move(self):
		action=int(np.digitize(np.sum(self.s[-self.Msize:])/self.Msize,[-1/3,1/3,1.1]))
		observation, reward, done, info = self.env.step(action)
		theta1_dot_p=self.theta1_dot
		self.theta1_dot=self.env.state[2]
		self.theta1_dot2=self.theta1_dot-theta1_dot_p
		
	def SensorIndex(self,x,xmax):
		return int(np.floor((x+xmax)/(2*xmax)*2**self.Ssize1))
		
	def UpdateSensors(self):
		self.acc=self.theta1_dot2
		s = self.env.state
		self.theta=s[0]
		
		self.ypos0=-np.cos(s[0])
		self.xpos0=np.sin(s[0])
		
		self.ypos=-np.cos(s[0]) - np.cos(s[1] + s[0])
		self.xpos=np.sin(s[0]) + np.sin(s[1] + s[0])
		
		self.speed=self.env.state[2]
		
		self.posx_ind=self.SensorIndex(self.xpos,self.maxheight)
		self.posy_ind=self.SensorIndex(self.ypos,self.maxheight)
		
		
		self.s[self.Ssize1:self.Ssize]= 2*bitfield(self.posx_ind,self.Ssize-self.Ssize1)-1
		self.s[0:self.Ssize1]=2*bitfield(self.posy_ind,self.Ssize1)-1
		
	#Execute step of the Glauber algorithm to update the state of one unit
	def GlauberStep(self,i=None):			#Execute step of Glauber algorithm
		if i is None:
			i = np.random.randint(self.size)
		eDiff = 2*self.s[i]*(self.h[i] + np.dot(self.J[i,:]+self.J[:,i],self.s))
		if self.Beta*eDiff < np.log(1.0/np.random.rand(1)-1):    # Glauber
			self.s[i] = -self.s[i]
			
	#Compute energy difference between two states with a flip of spin i	
	def deltaE(self,i):		
		return 2*(self.s[i]*self.h[i] + np.sum(self.s[i]*(self.J[i,:]*self.s)+self.s[i]*(self.J[:,i]*self.s)))
		
		
	#Update states of the agent from its sensors		
	def Update(self,i=None):	
		if i is None:
			i = np.random.randint(self.size)
		if i==0:
			self.Move()
			self.UpdateSensors()
		elif i>=self.Ssize:
			self.GlauberStep(i)
	
	def SequentialUpdate(self):
		for i in np.random.permutation(self.size):
			self.Update(i)



	#Dynamical Critical Learning Algorithm for poising units in a critical state
	def HomeostaticGradient(self,T=None):
		if T==None:
			T=self.defaultT
		
		self.m=np.zeros(self.size)
		self.c=np.zeros((self.size,self.size))
		self.C=np.zeros((self.size,self.size))
		
		# Main simulation loop:
		self.y=np.zeros(T)
		samples=[]
		for t in range(T):
			
			self.SequentialUpdate()
			self.y[t]=self.ypos
			self.m+=self.s
			for i in range(self.size):
				self.c[i,i+1:]+=self.s[i]*self.s[i+1:]
		self.m/=T
		self.c/=T
		for i in range(self.size):
			self.C[i,i+1:]=self.c[i,i+1:]-self.m[i]*self.m[i+1:]		
		
		
		c1=np.zeros((self.size,self.size))
		for i in range(self.Ssize,self.size):
			inds=np.array([],int)
			c=np.array([])
			for j in range(self.size):
				if not i==j:
					inds=np.append(inds,[j])
				if i<j:
					c=np.append(c,[self.c[i,j]])
				elif i>j:
					c=np.append(c,[self.c[j,i]])
			order=np.argsort(c)[::-1]
			c1[i,inds[order]]=self.Cint[i,:]
		self.c1=np.triu(c1+c1.T,1)
		self.c1[self.Ssize:,self.Ssize:]*=0.5

		dh = self.m1-self.m
		dJ = self.c1-self.c
		
		dh[0:self.Ssize]=0
		dJ[0:self.Ssize,0:self.Ssize]=0
		dJ[-self.Msize:,-self.Msize:]=0
		dJ[0:self.Ssize,-self.Msize:]=0
		return dh,dJ
		
		
	def CriticalLearning(self,Iterations,T=None,mode='homeostatic'):	
		u=0.01
		count=0
		if mode=='static':
			dh,dJ=self.CriticalGradient(T)
		if mode=='dynamic':
			dh,dJ=self.DynamicalCriticalGradient(T)
		if mode=='homeostatic':
			dh,dJ=self.HomeostaticGradient(T)
		fit=max(np.max(np.abs(self.c1-self.c)),np.max(np.abs(self.m1-self.m)))
		print(count,fit,self.env.LINK_MASS_1,np.max(np.abs(self.J)),np.mean(np.abs(self.J[0:self.Ssize,self.Ssize:])),np.mean(self.y),np.max(self.y))
		self.l2=0.004
		for i in range(Iterations):
			count+=1
			self.h+=u*dh - self.l2*self.h
			self.J+=u*dJ - self.l2*self.J
			
			Vmax=self.max_weights
			for i in range(self.size):
				if np.abs(self.h[i])>Vmax:
					self.h[i]=Vmax*np.sign(self.h[i])
				for j in np.arange(i+1,self.size):
					if np.abs(self.J[i,j])>Vmax:
						self.J[i,j]=Vmax*np.sign(self.J[i,j])
						
			if mode=='static':
				dh,dJ=self.CriticalGradient(T)
			if mode=='dynamic':
				dh,dJ=self.DynamicalCriticalGradient(T)
			if mode=='homeostatic':
				dh,dJ=self.HomeostaticGradient(T)
			fit=np.max(np.abs(self.c1[self.Ssize:,self.Ssize:]-self.c[self.Ssize:,self.Ssize:]))
		
			
			if count%1==0:
				print(self.size,count,fit,self.env.LINK_MASS_1,np.max(np.abs(self.J)),np.mean(self.y),np.max(self.y))
			

#Transform bool array into positive integer
def bool2int(x):				
	y = 0
	for i,j in enumerate(np.array(x)[::-1]):
		y += j*2**i
	return int(y)

#Transform positive integer into bit array
def bitfield(n,size):
	x = [int(x) for x in bin(int(n))[2:]]
	x = [0]*(size-len(x)) + x
	return np.array(x)