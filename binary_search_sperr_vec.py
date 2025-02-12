import os 
#from dlib import find_min_global
import sys
import argparse
import numpy as np
import uuid
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

#pid=os.getpid()
pid = str(uuid.uuid1())
target = QoIEB # target qoi error bound
data_ranges=[0,0,0]
for i in range(3):
    idata = np.fromfile(inputNames[i],dtype=np.float32)
    data_ranges[i] = np.max(idata)-np.min(idata)


def binary_search(target,start,end, max_iter = 100):
    iteration = 0
    time_cost = 0
    best_eb = start
    best_log = ""
    best_cr = 0

    eb = end
    command = "%s %s -c --omp 1 --ftype 32 --print_stats --dims %s --bitstream %s.sperr1 --decomp_f %s.sperr.out1 --pwe %.8E;%s %s -c --omp 1 --ftype 32 --print_stats --dims %s --bitstream %s.sperr2 --decomp_f %s.sperr.out2 --pwe %.4E;%s %s -c --omp 1 --ftype 32 --print_stats --dims %s --bitstream %s.sperr3 --decomp_f %s.sperr.out3 --pwe %.4E;%s -f -%d %s -i %s -o %s.sperr.out1 %s.sperr.out2 %s.sperr.out3 -c %s;rm -f %s*" % \
    (args.cmp_command, inputNames[0], dimSeq, pid, pid, eb*data_ranges[0],args.cmp_command, inputNames[1], dimSeq, pid, pid, eb*data_ranges[1],args.cmp_command, inputNames[2], dimSeq, pid, pid, eb*data_ranges[2], args.val_command, numDims, dimSeq, " ".join(inputNames), pid, pid, pid, args.config, pid)
    time = 0
    br = 0 
#print(command)
    with os.popen(command) as f:
        log=f.read()
        for line in log.splitlines():
        #print(line)
            if "relative qoi error" in line:
                rel_qoi_error = eval(line.split("=")[-1])
            if line[0] == "Q" and "QoI validation time" in line:
                time += eval(line.split("=")[-1].split("s")[0])
            if line[0] == "C" and "Compression time" in line:
                time += eval(line.split("=")[-1].split("s")[0])
            if "Bitrate" in line:
                br += eval(line.split(",")[0].split("=")[-1])
    br /= 3.0
    cr = 32.0/br
    iteration += 1
    print("Round %d, error bound = %.8E, CR = %.4f, QoI relative error = %.4E, time cost = %.4f" % (iteration, eb, cr, rel_qoi_error,time))
    time_cost +=time

    if rel_qoi_error <=ut*target:
        best_eb = eb 
        best_log = log 
        best_cr = cr
        return best_eb,best_cr, iteration,time_cost,best_log



    while 1:
        eb = (start+end)/2
        command = "%s %s -c --omp 1 --ftype 32 --print_stats --dims %s --bitstream %s.sperr1 --decomp_f %s.sperr.out1 --pwe %.8E;%s %s -c --omp 1 --ftype 32 --print_stats --dims %s --bitstream %s.sperr2 --decomp_f %s.sperr.out2 --pwe %.4E;%s %s -c --omp 1 --ftype 32 --print_stats --dims %s --bitstream %s.sperr3 --decomp_f %s.sperr.out3 --pwe %.4E;%s -f -%d %s -i %s -o %s.sperr.out1 %s.sperr.out2 %s.sperr.out3 -c %s;rm -f %s*" % \
        (args.cmp_command, inputNames[0], dimSeq, pid, pid, eb*data_ranges[0],args.cmp_command, inputNames[1], dimSeq, pid, pid, eb*data_ranges[1],args.cmp_command, inputNames[2], dimSeq, pid, pid, eb*data_ranges[2], args.val_command, numDims, dimSeq, " ".join(inputNames), pid, pid, pid, args.config, pid)
        time = 0
        br = 0 
    #print(command)
        with os.popen(command) as f:
            log=f.read()
            for line in log.splitlines():
            #print(line)
                if "relative qoi error" in line:
                    rel_qoi_error = eval(line.split("=")[-1])
                if line[0] == "Q" and "QoI validation time" in line:
                    time += eval(line.split("=")[-1].split("s")[0])
                if line[0] == "C" and "Compression time" in line:
                    time += eval(line.split("=")[-1].split("s")[0])
                if "Bitrate" in line:
                    br += eval(line.split(",")[0].split("=")[-1])
        br /= 3.0
        cr = 32.0/br
        iteration += 1
        print("Round %d, error bound = %.8E, CR = %.4f, QoI relative error = %.4E, time cost = %.4f" % (iteration, eb, cr, rel_qoi_error,time))
        time_cost +=time

        if rel_qoi_error <=ut*target:
            if cr > best_cr:
                best_eb = eb 
                best_log = log 
                best_cr = cr
        #print(rel_qoi_error,target)
        if (rel_qoi_error >= lt*target and rel_qoi_error <=ut*target) or iteration>=max_iter or end-start<1e-15:
            break
        if rel_qoi_error < target:
            start = eb 
        else:
            end = eb 
    return best_eb,best_cr, iteration,time_cost,best_log

best_eb,best_cr,iteration,time_cost, best_log = binary_search(target,lb,ub,maxIter)
print("Best compression log:")
print(best_log)
print("Terminated after %d rounds. Best error bound = %.8E, best CR = %.4f, total time cost = %.4f" % (iteration, best_eb, best_cr,time_cost))





