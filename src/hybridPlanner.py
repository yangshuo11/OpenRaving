from PDDLPatcher import *
import sys, subprocess, time, os
import planning_primitives
from settings import *
import getopt

def execCmd(cmd,  successStr,  dumpFile, pollTime = 12):
    ''' A generic utility for executing a command. 
    Dumpfile stores stdout and stderr'''

    print "Executing %s...   " %(cmd), 
    sys.stdout.flush()
    ## Using subprocess.call so that all the messages from the planner
    ## can be captured and parsed for the string "Solution found!"
    dumpF = open(dumpFile,  "w")
    p = subprocess.Popen([cmd], shell = True, stdout=dumpF, stderr=dumpF)
    startTime = time.time()
    
    while p.poll == None:
        time.sleep(pollTime)
        if time.time() - startTime >10:
            ans = raw_input("Still running. Continue (c), Restart (r), Quit(q)? ")
            startTime = time.time()
            if ans.strip() == "q":
                os.kill(p.pid+1,  9)
                sys.exit(-1)
            elif ans.strip() == "c":
                continue
            elif ans.strip() == "r":
                os.kill(p.pid+1,  9)
                return execCmd(cmd, successStr, dumpFile)
            else:
                print "Unrecognized response. Continuing." 
 
        
    dumpF.close()
    time.sleep(5)
#    pdb.set_trace()
    dumpF = open(dumpFile, "r")
    msg = dumpF.read()

    if successStr in msg:
        print "Success!"
        print
        return 0
    else:
        print "Failure... check %s for messages"%dumpFile
        print
        return -1








    
def iterativePlanIndependent():
    while True:
        iteration += 1
        ffCmdLine = ff + " -o " + pddlDomainFile +" -f " + pddlProblemFile
        ffOutputFile = pddlProblemFile+ ".out"
    
        execCmd(ffCmdLine, "found legal plan",  ffOutputFile)
        
        ffOutStr = OutputParser(ffOutputFile).getFFPlan()
        print "Computed plan: \n" + ffOutStr
    
        errFileName = raw_input("Enter error file name: ")
        if errFileName == "-1":
            sys.exit(0)
        if errFileName == "-2":
            pdb.set_trace()
    
        execErrF = tryOpen(path+errFileName, "r")
        errorStr = execErrF.read()
    
        errorLines = errorStr.lower().split("\n")
    
        failedActionNumber = int(errorLines[0].strip("linenumber: "))
        propList = filter( lambda x: len(x)>0, errorLines[1:])
    
        ## If action i failed, need state just after action i-1
        ## kth element of state list from ffoutputfile is 
        ## the state before application of action k.
        myPatcher.patchWithFFOutput(ffOutputFile, failedActionNumber)
        myPatcher.patchWithProps(propList)
        print "State to re-pan from:"
        myPatcher.printInitState()
    
        pddlProblemFile = initialProblemFile.replace(".pddl", \
                                                         repr(iteration)+".pddl")
        myPatcher.writeCurrentInitState(pddlProblemFile)
        

def iterativePlanAuto(pddlDomainFile, pddlProblemFile, viewer):
    iteration = 0
    ex = planning_primitives.initOpenRave(viewer)
    while True:
        iteration += 1
        ffCmdLine = ff + " -o " + pddlDomainFile +" -f " + pddlProblemFile
        ffOutputFile = pddlProblemFile+ ".out"
    
        if execCmd(ffCmdLine, "found legal plan",  ffOutputFile) < 0:
                sys.exit(-1)
        
        ffOutStr = OutputParser(ffOutputFile).getFFPlan()
        print "Computed plan: \n" + ffOutStr
        planFile = pddlProblemFile+".plan"
        tryIO(planFile, "write", ffOutStr)
        time.sleep(2)
        
        try:
            planning_primitives.test(planFile, ex)
            print "Success. Quitting."
            sys.exit(0)
        except planning_primitives.ExecutingException, e:
            errorStr = e.pddl_error_info
    
        if errorStr == "":
            print "Failure: Error in simulation. Try increasing number of samples."
            sys.exit(-1)

        print "Got facts:"
        print errorStr
        if viewer:
            raw_input("Press return to continue")
        else:
            time.sleep(5)
    
        errorLines = errorStr.lower().split("\n")
    
        failedActionNumber = int(errorLines[0].strip("linenumber: "))
        propList = filter( lambda x: len(x)>0, errorLines[1:])
    
        ## If action i failed, need state just after action i-1
        ## kth element of state list from ffoutputfile is 
        ## the state before application of action k.
        myPatcher.patchWithFFOutput(ffOutputFile, failedActionNumber)
        myPatcher.patchWithProps(propList)
        print "State to re-plan from:"
        myPatcher.printInitState()
    
        pddlProblemFile = initialProblemFile.replace(".pddl", \
                                                         repr(iteration)+".pddl")
        myPatcher.writeCurrentInitState(pddlProblemFile)

def main(argv):
    iteration = 0
    pddlProblemFile = initialProblemFile

    try:
        opts, args = getopt.getopt(argv[1:],"v")
    except getopt.GetoptError:
        print 'Use -v for viewer'
        sys.exit(2)

    viewer = False
    for opt,arg in opts:
        if opt == "-v":
            print "Setting viewer mode to True"
            viewer = True

            
    iterativePlanAuto(pddlDomainFile, initialProblemFile, viewer)


if __name__ == "__main__":
    myPatcher = PDDLPatcher(initialProblemFile)
    #myPatcher.printInitState()
    main(sys.argv)