#
# trailerlib module
#

import scipy
import kdtree
import numpy as np
import matplotlib as plt
import NearestNeighbors
import math

# Parameters for the truck and trailer
# Units in radians and meters
WB = 3.7            # wheel base of the system
LT = 8.0            # length between trailer pivot and fifth wheel
W = 2.6             # system width
LF = 4.5            # length between fifth wheel and front of truck
LB = 1.0            # length between fifth wheel and back of truck
LTF = 1.0           # length between fifth wheel and front of trailer
LTB = 9.0           # length between fifth wheel and back of trailer
MAX_STEER = 0.6     # maximum steering angle for truck
TR = 0.5            # tire radius
TW = 1.0            # tire width


# Parameters for collision checking
# Units in radians and meters
WBUBBLE_DIST = 3.5  # distance between fifth wheel and bubble center
WBUBBLE_R = 10.0    # bubble radius
B = 4.45            # distance between fifth wheel and back of truck
C = 11.54           # distance between fifth wheel and front of truck
I = 8.55            # system width
VRX = [C, C, -B, -B, C]
VRY = [(-I/2.0), (I/2.0), (I/2.0), (-I/2.0), (-I/2.0)]


# uses circle or bubble to check for collision
def check_collision(x, y, yaw, kdtree, ox, oy, wbd, wbr, vrx, vry):
    for (ix, iy, iyaw) in zip(x, y, yaw):
        cx = ix + wbd*math.cos(iyaw)
        cy = iy + wbd*math.sin(iyaw)

        # collision check for whole bubble
        # this is dependent on some function called inrange.jl which is one of the source files
        # in NearestNeighbors.jl
        ids = inrange(kdtree, [cx, cy], wbr, True)
        if len(ids) == 0:
            continue

        if not rect_check(ix, iy, iyaw, ox[ids], oy[ids], vrx, vry):    # need to check if syntax is correct
            return False    # this means there is a collision

    return True     # this means no collision


# uses rectangle to check for collisions
def rect_check(ix, iy, iyaw, ox, oy, vrx, vry):
    c = math.cos(-iyaw)
    s = math.sin(-iyaw)

    for (iox, ioy) in zip(ox, oy):
        tx = iox - ix
        ty = ioy - iy
        lx = (c*tx - s*ty)
        ly = (s*tx + c*ty)

        sumangle = 0.0
        for i in range(1, len(vrx)-1):
            x1 = vrx[i] - lx
            y1 = vry[i] - ly
            x2 = vrx[i+1] - lx
            y2 = vry[i+1] - ly
            d1 = math.hypot(x1, y1)
            d2 = math.hypot(x2, y2)
            theta1 = math.atan2(y1, x1)
            tty = (-math.sin(theta1)*x2 + math.cos(theta1)*y2)
            tmp = ((x1 * y1) + (y1 * y2)) / (d1 * d2)

            if tmp >= 1.0:
                tmp = 1.0
            elif tmp <= 0.0:
                tmp = 0.0

            if tty >= 0.0:
                sumangle += math.acos(tmp)
            else:
                sumangle -= math.acos(tmp)

        if sumangle >= math.pi:
            return False    # this means there is a collision


    return True     # this means no collision


# this calculates the trailer yaw from the x, y, yaw lists
def calc_trailer_yaw_from_xyyaw(x, y, yaw, init_tyaw, steps):
    tyaw = np.zeros(len(x))
    tyaw[1] = init_tyaw

    for i in range(2, len(x)):
        tyaw[i] += (tyaw[i - 1] + steps[i - 1]) / (LT * math.sin(yaw[i - 1] - tyaw[i - 1]))

    return tyaw


# this calculates the motion model for the trailer and the equations comes from the link
# http://planning.cs.uiuc.edu/node661.html#77556
def trailer_motion_model(x, y, yaw0, yaw1, D, d, L, delta):
    x += D * math.cos(yaw0)
    y += D * math.sin(yaw0)
    yaw0 += D / (L * math.tan(delta))
    yaw1 += D / (d * math.sin(yaw0 - yaw1))

    return x, y, yaw0, yaw1


# this checks for trailer collision using KDTree.jl function which is one of the source files
# in NearestNeighbors.jl
def check_trailer_collision(ox, oy, x, y, yaw0, yaw1, kdtree):
    if kdtree == None:
        kdtree = KDTree([np.conj(ox), np.conj(oy)])     #not sure if this is set up properly for kdtree, also see julia code for transpose syntax '

    vrxt = np.array([LTF, LTF, -LTB, -LTB, LTF])
    vryt = np.array([(-W/2.0), (W/2.0), (W/2.0), (-W/2.0), (-W/2.0)])


    # these are bubble parameters
    DT = (LTF + LTB) / 2.0 - LTB    # need to review order of operations
    DTR = (LTF + LTB) / 2.0 + 0.3   # need to review order of operations


    # check for trailer collision
    if not check_collision(x, y, yaw1, kdtree, ox, oy, DT, DTR, vrxt, vryt):    # need to verify if syntax is correct
        return False    # there is collision


    vrxf = np.array([LF, LF, -LB, LF])
    vryf = np.array([(-W/2.0), (W/2.0), (W/2.0), (-W/2.0), (-W/2.0)])


    # these are bubble parameters
    DF = (LF + LB) / 2.0 - LB       # need to review order of operations
    DFR = (LF + LB) / 2.0 + 0.3     # need to review order of operations


    # check for front trailer collision
    # but i think this is checking for truck collision
    if not check_collision(x, y, yaw0, kdtree, ox, oy, DF, DFR, vrxf, vryf):    # need to verify if syntax is correct
        return False    # there is collision

    return True     # there is no collision


# this creates the arrays that hold the values for plotting
# not sure if the structures for the arrays are correct
# need to double-check the order of operations for some of the calcs
# also, julia uses .+= for element-wise additions, but python does not
# need the . right?
def plot_trailer(x, y, yaw, yaw1, steer):
    truckcolor = "-k"   # need to verify if syntax is correct

    LENGTH = LB + LF        # this is full length of truck
    LENGTHt = LTB + LTF     # this is full length of trailer

    truckOutLine = np.array([-LB, (LENGTH-LB), (LENGTH-LB), -LB, -LB], [(W/2), (W/2), (-W/2), (-W/2), (W/2)])   # syntax correct for 2x5?
    trailerOutLine = np.array([-LTB, (LENGTHt-LTB), (LENGTHt-LTB), -LTB, -LTB], [(W/2), (W/2), (-W/2), (W/2)])  # syntax correct for 2x5?

    rr_wheel = np.array([TR, -TR, -TR, TR, TR], [((-W/12.0)+TW), ((-W/12.0)+TW), ((W/12.0)+TW), ((W/12.0)+TW), ((-W/12.0)+TW)])     # check order of operations
    rl_wheel = np.array([TR, -TR, -TR, TR, TR], [((-W/12.0)-TW), ((-W/12.0)-TW), ((W/12.0)-TW), ((W/12.0)-TW), ((-W/12.0)-TW)])     # check order of operations

    fr_wheel = np.array([TR, -TR, -TR, TR, TR], [((-W/12.0)+TW), ((-W/12.0)+TW), ((W/12.0)+TW), ((W/12.0)+TW), ((-W/12.0)+TW)])     # check order of operations
    fl_wheel = np.array([TR, -TR, -TR, TR, TR], [((-W/12.0)-TW), ((-W/12.0)-TW), ((W/12.0)-TW), ((W/12.0)-TW), ((-W/12.0)-TW)])     # check order of operations

    tr_wheel = np.array([TR, -TR, -TR, TR, TR], [((-W/12.0)+TW), ((-W/12.0)+TW), ((W/12.0)+TW), ((W/12.0)+TW), ((-W/12.0)+TW)])     # check order of operations
    tl_wheel = np.array([TR, -TR, -TR, TR, TR], [((-W/12.0)-TW), ((-W/12.0)-TW), ((W/12.0)-TW), ((W/12.0)-TW), ((-W/12.0)-TW)])     # check order of operations

    Rot1 = np.array([math.cos(yaw), math.sin(yaw)], [-math.sin(yaw), math.cos(yaw)])            # syntax correct for 2x2?
    Rot2 = np.array([math.cos(steer), math.sin(steer)], [-math.sin(steer), math.cos(steer)])    # syntax correct for 2x2?
    Rot3 = np.array([math.cos(yaw1), math.sin(yaw1)], [-math.sin(yaw1), math.cos(yaw1)])        # syntax correct for 2x2?

    fr_wheel = np.conj(np.conj(fr_wheel)*Rot2)      # check syntax of this
    fl_wheel = np.conj(np.conj(fl_wheel)*Rot2)      # check syntax of this

    fr_wheel[1, :] += WB                            # check syntax of this
    fl_wheel[1, :] += WB                            # check syntax of this

    fr_wheel = np.conj(np.conj(fr_wheel)*Rot1)      # check syntax of this
    fl_wheel = np.conj(np.conj(fl_wheel)*Rot1)      # check syntax of this

    tr_wheel[1, :] -= LT                            # check syntax of this
    tl_wheel[1, :] -= LT                            # check syntax of this

    tr_wheel = np.conj(np.conj(tr_wheel)*Rot3)      # check syntax of this
    tl_wheel = np.conj(np.conj(tl_wheel)*Rot3)      # check syntax of this

    truckOutLine = np.conj(np.conj(truckOutLine)*Rot1)          # check syntax of this
    trailerOutLine = np.conj(np.conj(trailerOutLine)*Rot1)      # check syntax of this

    rr_wheel = np.conj(np.conj(rr_wheel)*Rot1)      # check syntax of this
    rl_wheel = np.conj(np.conj(rl_wheel)*Rot1)      # check syntax of this

    truckOutLine[1, :] += x
    truckOutLine[2, :] += y

    trailerOutLine[1, :] += x
    trailerOutLine[2, :] += y

    fr_wheel[1, :] += x
    fr_wheel[2, :] += y

    rr_wheel[1, :] += x
    rr_wheel[2, :] += y

    fl_wheel[1, :] += x
    fl_wheel[2, :] += y

    rl_wheel[1, :] += x
    rl_wheel[2, :] += y

    tr_wheel[1, :] += x
    tr_wheel[2, :] += y

    tl_wheel[1, :] += x
    tl_wheel[2, :] += y


    # not sure why python complaining about plot not being in __init__.py
    plt.plot([truckOutLine[1, :], truckOutLine[2, :], truckcolor])
    plt.plot([trailerOutLine[1, :], trailerOutLine[2, :], truckcolor])

    plt.plot([fr_wheel[1, :], fr_wheel[2, :], truckcolor])
    plt.plot([rr_wheel[1, :], rr_wheel[2, :], truckcolor])

    plt.plot([fl_wheel[1, :], fl_wheel[2, :], truckcolor])
    plt.plot([rl_wheel[1, :], rl_wheel[2, :], truckcolor])

    plt.plot([tr_wheel[1, :], tr_wheel[2, :], truckcolor])
    plt.plot([tl_wheel[1, :], tl_wheel[2, :], truckcolor])

    plt.plot([x, y, "*"])


def main():
    x = 0.0
    y = 0.0
    yaw0 = math.radians(10.0)
    yaw1 = math.radians(-10.0)

    plot_trailer(x, y, yaw0, yaw1, 0.0)

    DF = (LF + LB) / 2.0 - LB       # check operation of order
    DFR = (LF + LB) / 2.0 + 0.3     # check operation of order

    DT = (LTF + LTB) / 2.0 - LTB    # check operation of order
    DTR = (LTF + LTB) / 2.0 + 0.3   # check operation of order

    axis("equal")

    show()

    if length(PROGRAM_FILE) != 0 && occursin(PROGRAM_FILE, @ __FILE__):     # check syntax of this
        @time main()








