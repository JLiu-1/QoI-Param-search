import os 
from dlib import find_min_global
import sys
import argparse

parser = argparse.ArgumentParser()


parser.add_argument('--input','-i',type=str)
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
inputName = args.input 
numDims = args.dim 
dimSeq = " ".join(args.dims)
dataEB = args.data_eb  
QoIEB = args.qoi_eb 
maxIter = args.max_iter 
scaling_factor = args.scale
ub = min(args.upper_bound,dataEB) 
lb = args.lower_bound

ut = args.upper_tol_rate
lt = args.lower_tol_rate

iteration = 0
time_cost = 0
pid=os.getpid()

block_qoi = False
with open(args.config) as f:
    lines = f.read().splitlines()
    for line in lines:
        if "qoiRegionMode" in line and eval(line.split("=")[-1]) == 1:
            block_qoi = True
            break

target = QoIEB # target qoi error bound
best_eb = -1
best_cr = 0
best_log = ""
def loss_function(rel_error_bound):
    global iteration, time_cost, target,best_eb,best_cr,best_log,iteration,scaling_factor,ub
    command = "%s -z -f -a -%d %s -i %s -o %s.hpez.out -M REL %.8E;%s -f -%d %s -i %s -o %s.hpez.out -c %s;rm -f %s*" % \
    (args.cmp_command, numDims, dimSeq, inputName, pid, rel_error_bound, args.val_command, numDims, dimSeq, inputName, pid, args.config, pid)
    time = 0
    #print(command)
   
    with os.popen(command) as f:
        log=f.read()
        for line in log.splitlines():
            #print(line)
            if (not block_qoi) and "relative qoi error" in line:
                rel_qoi_error = eval(line.split("=")[-1])
            elif block_qoi and "L^infinity error of average" in line:
                rel_qoi_error = eval(line.split("=")[-1])
            if line[0] == "Q" and "QoI validation time" in line:
                time += eval(line.split("=")[-1].split("s")[0])
            if line[0] == "c" and "compression time" in line:
                time += eval(line.split("=")[-1].split("s")[0])
            if block_qoi and "RegionalQoI validation time" in line:
                time += eval(line.split("=")[-1].split("s")[0])
            if "compression ratio" in line:
                cr = eval(line.split("=")[-1])
    iteration += 1
    print("Round %d, error bound = %.8E, CR = %.4f, QoI relative error = %.4E, time cost = %.4f" % (iteration, rel_error_bound, cr, rel_qoi_error,time))
    time_cost +=time
    #print(rel_qoi_error,target)
    if rel_qoi_error <= ut*target:
        if cr > best_cr:
            best_cr = cr 
            best_eb = rel_error_bound
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



