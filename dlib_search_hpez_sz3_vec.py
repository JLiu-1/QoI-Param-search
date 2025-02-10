import os 
from dlib import find_min_global
import sys
import argparse

parser = argparse.ArgumentParser()


parser.add_argument('--inputs','-i',type=str,nargs="+")
#parser.add_argument('--output','-o',type=str)
parser.add_argument('--dim','-d',type=int,default=3, help='Number of dims')
parser.add_argument('--dims','-m',type=str,nargs="+",help='Dim order is the same as compression command')
parser.add_argument('--cmp_command','-a',type=str, help='Compression sub-command')
parser.add_argument('--val_command','-v',type=str, help='QoI-val command')
parser.add_argument('--config','-c',type=str,default=None, help='QoI config file')
parser.add_argument('--data_eb',"-e",type=float,default=1.0,help='VR-REL data eb',)
parser.add_argument('--qoi_eb',"-t",type=float,default=1e-3,help='VR-REL QoI eb',)
parser.add_argument('--max_iter',"-x",type=int,default=100)
parser.add_argument('--upper_tol_rate',"-ut",type=float,default=1.0, help='Tune upper tol rate')
parser.add_argument('--lower_tol_rate',"-lt",type=float,default=0.95, help='Tune lower tol rate')
parser.add_argument('--upper_bound',"-ub",type=float,default=1.0, help='Tune upper bound (in VR-REL data eb)')
parser.add_argument('--lower_bound',"-lb",type=float,default=0.0, help='Tune lower bound (in VR-REL data eb)')
parser.add_argument('--scale',"-s",type=float,default=1e12, help='Loss scaling factor')

args = parser.parse_args()
inputNames = args.inputs 
numDims = args.dim 
dimSeq = " ".join(args.dims)
dataEB = args.data_eb  
QoIEB = args.qoi_eb 
maxIter = args.max_iter 
ub = min(args.upper_bound,dataEB) 
lb = args.lower_bound

ut = args.upper_tol_rate
lt = args.lower_tol_rate
scaling_factor = args.scale
iteration = 0
time_cost = 0
pid=os.getpid()

target = QoIEB # target qoi error bound
best_eb = -1
best_cr = 0
best_log = ""
def loss_function(eb):
    global iteration, time_cost, target,best_eb,best_cr,best_log,iteration,scaling_factor,ub
    command = "%s -z -f -a -%d %s -i %s -o %s.hpez.out1 -M REL %.8E;%s -z -f -a -%d %s -i %s -o %s.hpez.out2 -M REL %.8E;%s -z -f -a -%d %s -i %s -o %s.hpez.out3 -M REL %.4E;%s -f -%d %s -i %s -o %s.hpez.out1 %s.hpez.out2 %s.hpez.out3 -c %s;rm -f %s*" % \
    (args.cmp_command, numDims, dimSeq, inputNames[0], pid, eb,args.cmp_command, numDims, dimSeq, inputNames[1], pid, eb,args.cmp_command, numDims, dimSeq, inputNames[2], pid, eb, args.val_command, numDims, dimSeq, " ".join(inputNames), pid, pid, pid, args.config, pid)
    time = 0
    #print(command)
    br = 0 
    with os.popen(command) as f:
        log=f.read()
        for line in log.splitlines():
            #print(line)
            if "relative qoi error" in line:
                rel_qoi_error = eval(line.split("=")[-1])
            if line[0] == "Q" and "QoI validation time" in line:
                time += eval(line.split("=")[-1].split("s")[0])
            if line[0] == "c" and "compression time" in line:
                time += eval(line.split("=")[-1].split("s")[0])
            if "compression ratio" in line:
                br += 32.0/eval(line.split("=")[-1])
    br /= 6.0
    cr = 32.0/br
    iteration += 1
    print("Round %d, error bound = %.8E, CR = %.4f, QoI relative error = %.8E, time cost = %.4f" % (iteration, eb, cr, rel_qoi_error,time))
    time_cost +=time
    #print(rel_qoi_error,target)
    if rel_qoi_error <= ut*target:
        if cr > best_cr:
            best_cr = cr 
            best_eb = eb
            best_log = log

        if rel_qoi_error >= lt*target or rel_error_bound >= ub*0.99:
            print("Best compression log:")
            print(best_log)
            print("Terminated after %d rounds. Best error bound = %.8E, best CR = %.4f, total time cost = %.4f" % (iteration, best_eb, best_cr,time_cost))
            sys.exit()
            return 0
    return scaling_factor*(rel_qoi_error-target)**2

_ = loss_function(ub)

best_eb,_ = find_min_global(loss_function,[lb],[ub],maxIter-1)#second: eb low bound, third: eb high bound
print("Best compression log:")
print(best_log)
print("Terminated after %d rounds. Best error bound = %.8E, best CR = %.4f, total time cost = %.4f" % (iteration, best_eb, best_cr,time_cost))



