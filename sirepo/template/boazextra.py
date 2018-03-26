# -*- coding: utf-8 -*-
#############################################################################
# extra utility functions for Boaz
#############################################################################

import numpy as np

def interp(x,y,W,xmin,ymin,xstep,ystep,nx,ny):
    #interpolate the function in the array W.
    #x and y are the coordinates to evaluate it.
    #W is a 2-D array.  We need the minimum x and y, xmin and ymin,
    #and also the spacing xstep and ystep to find the correct values in W.
    #With nx and ny, we can quickly check if the requested value is out
    #of bounds, in which case we find the closest boundary value.
    
    xmax = xmin + (nx - 1)*xstep
    ymax = ymin + (ny - 1)*ystep

    #if target point is outside of range put it on boundary
    if(x<xmin):
        x=xmin
    if(y<ymin):
        y=ymin
    if(x>=xmax):
        x = xmax - xstep   
    if(y>=ymax):
        y = ymax - ystep    

    #now find surrounding integers for (x,y)    
    
    [djx,jx0]=np.modf((x-xmin)/xstep)
    [djy,jy0]=np.modf((y-ymin)/ystep)
    jx0=int(jx0)
    jy0=int(jy0)

    #now get values

    W00 = W[jx0,jy0]
    W01 = W[jx0,jy0+1]
    W10 = W[jx0+1,jy0]
    #W11 = W[jx0+1,jy0+1]

    return W00 +  djx*(W01-W00) + djy*(W10-W00) #+ djx*djy*W11