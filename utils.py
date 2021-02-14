from time import time

# Object which is true once after <interval> seconds
# For Python2, use the __nonzero__ method
class Every:
    def __init__(self, interval):
        self.interval = interval
        self.lasttime = time()

    def __bool__(self):
        current = time()
        if current-self.lasttime>=self.interval:
            self.lasttime = current
            return True
        return False

#https://github.com/void4/gammacorrection

def gamma(a):
	return tuple(p**2.2 for p in a)

def degamma(a):
	return tuple(int(p**(1/2.2)) for p in a)

def mix(a,b,p=0.5):
	return tuple(int(a[i]*p+b[i]*(1-p)) for i in range(len(a)))

GREEN = (0,255,0)
RED = (255,0,0)

def gradient(p):
    """p between 0-1"""
    return degamma(mix(gamma(RED), gamma(GREEN), p))

def tohex(tup):
    return "#" + "".join(hex(t)[2:].rjust(2, '0') for t in tup)
