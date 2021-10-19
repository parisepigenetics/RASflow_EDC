# The main script to manage the subworkflows of RASflow

import yaml
import os
import time
import sys
import subprocess
import scripts.reporting as reporting
import sched
from datetime import datetime
from threading import Timer
import hashlib

class RepeatedTimer(object):   ## to monitore disk usage
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


with open('configs/config_main.yaml') as yamlfile:
    config = yaml.load(yamlfile,Loader=yaml.BaseLoader)

# Parameters to control the workflow
project = config["PROJECT"]
metadata = config["METAFILE"]
resultpath = config["RESULTPATH"]
njobs = config["NJOBS"]

# differences between clusters
server = sys.argv[1]
if server == "rpbs":
    option = " -p epigenetique" ## blank before the option!!
    MainPath = "/scratch/epigenetique/workflows/RASflow_RPBS/"
    server_name = "RPBS"
if server == "ifb" :
    option = " -x cpu-node-53"  ## to remove slow nodes, blank before the option!!
    MainPath = ""
    server_name = "IFB"
    try: writting_dir = resultpath.split('projects')[1].split('/')[1]
    except: writting_dir = os.getcwd().split('projects')[1].split('/')[1]
if server == "ipop-up":
    option = " -p ipop-up"
    MainPath = ""   
    server_name = "iPOP-UP"
    try: writting_dir = resultpath.split('projects')[1].split('/')[1]
    except: writting_dir = os.getcwd().split('projects')[1].split('/')[1]
    
# Start the workflow
print("Starting RASflow on project: " + project)

## Do you need to do FASTQ quality control?
qc = config["QC"]
print("Is FASTQ quality control required?\n", qc)

if qc!='yes':
    ## Do you need to do trimming?
    trim = config["TRIMMED"]
    print("Is trimming required?\n", trim)

    ## Do you need to do mapping?
    mapping = config["MAPPING"]
    print("Are mapping and counting required?\n", mapping)
    
    if mapping == 'yes': 
        ## Which mapping reference do you want to use? Genome or transcriptome?
        reference = config["REFERENCE"]
        print("Which mapping reference will be used?\n", reference)

        ## Do you want to analyse the repeats? 
        repeats = config["REPEATS"]
        print("Do you want to analyse the repeats?\n", repeats)         

    ## Do you want to do Differential Expression Analysis (DEA)?
    dea = config["DEA"]
    print("Is DEA required?\n", dea)
    
    # save the size of the biggest fastq in a txt file using md5 sum to have corresponding samples.
    os.system("cat "+metadata+" |  awk '{{print $1}}' > "+metadata+".samples.txt")
    with open(metadata+".samples.txt",'rb') as file_to_check:
        data = file_to_check.read()             # read contents of the file
    md5_samples = hashlib.md5(data).hexdigest()      # md5 on file content
    path_file = metadata+"_"+md5_samples+".max_size"
    if not os.path.isfile(path_file):  ## if already there, not touched. So the run can be restarted later without the FASTQ. 
        print("writting "+path_file)
        os.system("ls -l "+config["READSPATH"]+" | grep -f "+metadata+".samples.txt | awk '{{print $5}}' | sort -nr | head -n1 > "+path_file)


else:
    print("The workflow will stop after FASTQ quality control.")

## write the running time in a log file
start_time = time.localtime()
time_string = time.strftime("%Y%m%dT%H%M", start_time) # convert to '20200612T1705' format

LogPath = resultpath+"/"+project+"/logs/"
os.makedirs(LogPath, exist_ok=True)
file_main_time = open(LogPath+time_string+"_running_time.txt", "a+")
file_main_time.write("\nProject name: " + project + "\n")
file_main_time.write("Start time: " + time.ctime() + "\n")

## follow memory usage IFB only for now
def get_free_disk():
    quotas = str(subprocess.check_output(["bash scripts/getquota2.sh "+writting_dir], shell=True)).strip().split()
    used = quotas[2].split('G')[0]
    remaining=int(float(extra)*1024 - float(used))    
    time_now= time.localtime()
    time_now = time.strftime("%Y%m%dT%H%M", time_now)
    freedisk.write(time_now+'\t'+str(remaining)+'\n')
     #print('running get_free_disk', time_now)

if server == "ifb":
    print("Free disk is measured for the project "+writting_dir)
    freedisk = open(LogPath+time_string+"_free_disk.txt", "a+")
    quotas = str(subprocess.check_output(["bash scripts/getquota2.sh "+writting_dir], shell=True)).strip().split()
    tot = quotas[0].split('T')[0]
    extra = quotas[1].split('T')[0]
    freedisk.write("# quota:"+tot+" limit:"+ extra+ "\ntime\tfree_disk\n")
    rt = RepeatedTimer(60, get_free_disk)
            
# save the configuration
os.system("(echo && echo \"==========================================\" && echo && echo \"SAMPLE PLAN\") | cat configs/config_main.yaml - "+metadata+" >" + LogPath+time_string+"_configuration.txt")
os.system("(echo && echo \"==========================================\" && echo && echo \"CONDA ENV\" && echo) | cat - workflow/env.yaml >>" + LogPath+time_string+"_configuration.txt")
os.system("(echo && echo \"==========================================\" && echo && echo \"CLUSTER\" && echo) | cat - cluster.yaml >>" + LogPath+time_string+"_configuration.txt")



def spend_time(start_time, end_time):
    seconds = end_time - start_time
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%d:%02d:%02d" % (hours, minutes, seconds)


if qc=='yes':
        print("Starting FASTQ Quality Control...")
        start_time = time.time()
        os.system("snakemake -k --cluster-config cluster.yaml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus}"+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs="+njobs+" --latency-wait 40 -s "+MainPath+"workflow/quality_control.rules 2> " + LogPath+time_string+"_quality_control.txt")
        end_time = time.time()
        file_main_time.write("Time of running QC: " + spend_time(start_time, end_time) + "\n")
        print("FASTQ quality control is done! ("+spend_time(start_time, end_time)+")\n Please check the report and decide whether trimming is needed or not.\n To run the rest of the analysis, please remember to turn off the QC in the configuration file.")

else:
    if trim=='yes':
        print("Starting Trimming...")
        start_time = time.time()
        os.system("snakemake -k --cluster-config cluster.yaml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus}"+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs="+njobs+" --latency-wait 40 -s "+MainPath+"workflow/trim.rules 2> " + LogPath+time_string+"_trim.txt")
        end_time = time.time()
        file_main_time.write("Time of running trimming: " + spend_time(start_time, end_time) + "\n")
        print("Trimming is done! ("+spend_time(start_time, end_time)+")")
    else:
        print("Trimming is not required.")


    if mapping =='yes' and reference == "transcriptome":
        print("Starting mapping using ", reference, " as reference...")
        start_time = time.time()
        os.system("snakemake -k --resources load=100 --cluster-config cluster.yaml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus}"+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs="+njobs+" --latency-wait 40 -s "+MainPath+"workflow/quantify_trans.rules 2> " + LogPath+time_string+"_quantify_trans.txt")
        end_time = time.time()
        file_main_time.write("Time of running transcripts quantification: " + spend_time(start_time, end_time) + "\n")
        print("Mapping is done! ("+spend_time(start_time, end_time)+")")

    if mapping =='yes' and reference == "genome":
        print("Starting mapping using ", reference, " as reference...")
        start_time = time.time()
        ##### -k removed to put back before production!!!!!!!!
        #os.system("snakemake -k --resources load=100 --cluster-config cluster.yaml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus}"+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs="+njobs+" --latency-wait 40 -s "+MainPath+"workflow/align_count_genome.rules 2> " + LogPath+time_string+"_align_count_genome.txt")
        os.system("snakemake --resources load=100 --cluster-config cluster.yaml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus}"+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs="+njobs+" --latency-wait 40 -s "+MainPath+"workflow/align_count_genome.rules 2> " + LogPath+time_string+"_align_count_genome.txt")
        end_time = time.time()
        file_main_time.write("Time of running genome alignment and counting: " + spend_time(start_time, end_time) + "\n")
        print("Mapping is done! ("+spend_time(start_time, end_time)+")")

    if dea=='yes':
        print("Starting differential expression analysis...")
        if reference == "transcriptome":
            start_time = time.time()
            os.system("snakemake -k --cluster-config cluster.yaml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus}"+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs="+njobs+" --latency-wait 40 -s "+MainPath+"workflow/dea_trans.rules 2> " + LogPath+time_string+"_dea_trans.txt")
            end_time = time.time()
            file_main_time.write("Time of running DEA transcriptome based: " + spend_time(start_time, end_time) + "\n")
        elif reference == "genome":
            start_time = time.time()
            os.system("snakemake -k --cluster-config cluster.yaml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus}"+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs="+njobs+" --latency-wait 40 -s "+MainPath+"workflow/dea_genome.rules 2> " + LogPath+time_string+"_dea_genome.txt")
            end_time = time.time()
            file_main_time.write("Time of running DEA genome based: " + spend_time(start_time, end_time) + "\n")
        print("DEA is done! ("+spend_time(start_time, end_time)+")")
        reporting.main(time_string, server_name)

        # Visualization can only be done on gene-level
        if reference == "genome":
                pass
        elif reference == "transcriptome":
                gene_level = config["GENE_LEVEL"]
                if gene_level:
                    pass
                else:
                    print("Sorry! RASflow currently can only visualize on gene-level")
                    os._exit(1)

        print("RASflow is done!")

    else:
        print("DEA is not required and RASflow is done!")

file_main_time.write("Finish time: " + time.ctime() + "\n")
file_main_time.close()

if server == "ifb":
    rt.stop()
    freedisk.close()

print("########################################")
print("---- Errors ----")
returned_output = subprocess.check_output(["grep -A 5 -B 5 'error message\|error:\|Errno\|MissingInputException\|SyntaxError' " + LogPath+time_string+"*;exit 0"], shell=True)
if returned_output == b'' :
    print("There were no errors ! It's time to look at your results, enjoy!")
else :
    decode = returned_output.decode("utf-8")
    print(decode.replace(".txt",".txt\t"))
# Save logs
os.makedirs("logs", exist_ok=True)
os.system("cp "+LogPath+time_string+"* logs/")

