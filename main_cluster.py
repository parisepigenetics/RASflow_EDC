# The main script to manage the subworkflows of RASflow_EDC

import yaml
import os
import time
import sys
import subprocess
import scripts.check_config as ch
import scripts.edc_workflows as ew
import sched
from datetime import datetime
import hashlib

      
# Parameters to control the workflow
with open('config_ongoing_run.yaml') as yamlfile:
    config = yaml.load(yamlfile,Loader=yaml.BaseLoader)
# check the configuration file
config_error = ch.check_configuration('config_ongoing_run.yaml')
if config_error : sys.exit()
    
project = config["PROJECT"]
metadata = config["METAFILE"]
resultpath = config["RESULTPATH"]
njobs = config["NJOBS"]
reference = config["REFERENCE"]

## write the running time in a log file
start_time = time.localtime()
time_string = time.strftime("%Y%m%dT%H%M", start_time) # convert to '20200612T1705' format
LogPath = resultpath+"/"+project+"/logs/"
os.makedirs(LogPath, exist_ok=True)
file_main_time = open(LogPath+time_string+"_running_time.txt", "a+")
file_main_time.write("\nProject name: " + project + "\n")
file_main_time.write("Start time: " + time.ctime() + "\n")


## differences between clusters
server = sys.argv[1]
if server == "ifb" :
    account = os.getcwd().split('projects')[1].split('/')[1]
    option = "-A "+account+"\""   # + -x cpu-node-25 # to remove slow nodes
    server_name = "IFB"
    server_command = "-p"  # group management is different between ifb and ipop-up
if server == "ipop-up":
    option = "-p ipop-up\" --conda-frontend conda"    # no mamba (default with recent Snakemake versions) on ipop-up server -> use conda    
    server_name = "iPOP-UP"
    server_command = "-g"  # group management is different between ifb and ipop-up
    
# Snakemake command with all options
#snakemake_cmd = "snakemake -k --cluster-config cluster.yaml --drmaa  \
#    \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus} "+option+\
#    " --use-conda --conda-prefix .snakemake/conda/ --cores 300 --jobs="+njobs+" --latency-wait 40 "

snakemake_cmd = "snakemake -k --cluster-config cluster.yaml --drmaa  \
    \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus} "+option+\
    " --use-singularity --cores 300 --jobs="+njobs+" --latency-wait 40 "


# Monitore disk usage    
try: writting_dir = resultpath.split('projects')[1].split('/')[1]
except: writting_dir = os.getcwd().split('projects')[1].split('/')[1]
freedisk = open(LogPath+time_string+"_free_disk.txt", "a+")
quotas = str(subprocess.check_output(["bash scripts/getquota2.sh "+writting_dir +" "+server_command], shell=True)).strip().split() \
    # format: quotas = ["b'2T", '3T', "1.645T\\n'"]
unit = quotas[0][-1]
if unit == 'T': 
    total = float(quotas[0].split('T')[0].split("b'")[1])
    extra = float(quotas[1].split('T')[0])    
if unit == 'G': 
    total = float(quotas[0].split('G')[0].split("b'")[1])/1024
    unit_extra = quotas[1][-1]
    if unit_extra == 'T' : # in case total in G and extra in T 
        extra = float(quotas[1].split('T')[0])
    if unit_extra == 'G' : 
        extra = float(quotas[1].split('G')[0])/1024
        
freedisk.write("# quota:"+str(total)+"T limit:"+ str(extra)+ "T\ntime\tfree_disk\n")
rt = ew.RepeatedTimer(60, ew.get_free_disk, total, writting_dir, server_command, freedisk)

# save the configuration
subprocess.call("(echo && echo \"==========================================\" && echo && echo \"SAMPLE PLAN\") \
    | cat config_ongoing_run.yaml - "+metadata+" >" + LogPath+time_string+"_configuration.txt", shell=True)
subprocess.call("(echo && echo \"==========================================\" && echo && echo \"CONDA ENV\" && echo) \
    | cat - workflow/env.yaml >>" + LogPath+time_string+"_configuration.txt", shell=True)
subprocess.call("(echo && echo \"==========================================\" && echo && echo \"CLUSTER\" && echo) \
    | cat - cluster.yaml >>" + LogPath+time_string+"_configuration.txt", shell=True)
subprocess.call("(echo && echo \"==========================================\" && echo && echo \"VERSION\" && echo) \
    >>" + LogPath+time_string+"_configuration.txt", shell=True)
subprocess.call("(git log | head -3) >>" + LogPath+time_string+"_configuration.txt", shell=True)


# Start the workflow

print("-------------------------\n| RUN ID : "+time_string+ " |\n-------------------------")
print("Starting RASflow on project: " + project)
print("Free disk is measured for the cluster project (folder): "+writting_dir+"\n-------------------------\nWorkflow summary")

## Do you download data from SRA? 
qc = config["QC"]
sra = config["SRA"]
if sra == 'yes' : 
    print("The FASTQ files will be downloaded from SRA. A quality control will follow.")
    qc = 'yes'  # force quality control after dowloading external data. 

## Do you need to do FASTQ quality control?
print("Is FASTQ quality control required? ", qc)

if qc!='yes':
    ## Do you need to do trimming?
    trim = config["TRIMMED"]
    print("Is trimming required? ", trim)

    ## Do you need to do mapping?
    mapping = config["MAPPING"]
    print("Are mapping and counting required? ", mapping)
    
    if mapping == 'yes': 
        ## Which mapping reference do you want to use? Genome or transcriptome?
        print("Which mapping reference will be used? ", reference)

        ## Do you want to analyse the repeats? 
        repeats = config["REPEATS"]
        print("Do you want to analyse the repeats? ", repeats)         

    ## Do you want to do Differential Expression Analysis (DEA)?
    dea = config["DEA"]
    print("Is DEA required? ", dea)
    
    # save the size of the biggest fastq in a txt file using md5 sum to have corresponding samples.
    subprocess.call("cat "+metadata+" |  awk '{{print $1}}' > "+metadata+".samples.txt", shell=True)
    with open(metadata+".samples.txt",'rb') as file_to_check:
        data = file_to_check.read()             # read contents of the file
    md5_samples = hashlib.md5(data).hexdigest()      # md5 on file content
    path_file = metadata+"_"+md5_samples+".max_size"
    if not os.path.isfile(path_file):  ## if already there, not touched. So the run can be restarted later without the FASTQ. 
        print("writting "+path_file)
        subprocess.call("ls -l "+config["READSPATH"]+" | grep -f "+metadata+".samples.txt | awk '{{print $5}}' | sort -nr | head -n1 > "+path_file, shell=True)

else:
    print("The workflow will stop after FASTQ quality control.")
    
print("-------------------------\nWorkflow running....")

if qc=='yes':
        print("Starting FASTQ Quality Control...")
        start_time = time.time()
        exit_code = subprocess.call(snakemake_cmd+"-s workflow/quality_control.rules 2> " + LogPath+time_string+"_quality_control.txt", shell=True)
        if exit_code != 0 : 
            print("Error during quality control; exit code: ", exit_code)
            ew.exit_all(exit_code, "quality control", file_main_time, rt, freedisk, LogPath, time_string, server_name)
                        
        end_time = time.time()
        file_main_time.write("Time of running QC: " + ew.spend_time(start_time, end_time) + "\n")
        print("FASTQ quality control is done! ("+ew.spend_time(start_time, end_time)+")\n \
              Please check the report and decide whether trimming is needed or not.\n \
              To run the rest of the analysis, please remember to turn off the QC in the configuration file.")

else:
    if trim=='yes':
        print("Starting Trimming...")
        start_time = time.time()
        exit_code = subprocess.call(snakemake_cmd+"-s workflow/trim.rules 2> " + LogPath+time_string+"_trim.txt", shell=True)
        if exit_code != 0 : 
            print("Error during trimming; exit code: ", exit_code)
            ew.exit_all(exit_code, "trimming", file_main_time, rt, freedisk, LogPath, time_string, server_name)
        end_time = time.time()
        file_main_time.write("Time of running trimming: " + ew.spend_time(start_time, end_time) + "\n")
        print("Trimming is done! ("+ew.spend_time(start_time, end_time)+")")

    if mapping =='yes' and reference == "transcriptome":
        print("Starting mapping using ", reference, " as reference...")
        start_time = time.time()
        exit_code = subprocess.call(snakemake_cmd+"-s workflow/quantify_trans.rules 2> " + LogPath+time_string+"_quantify_trans.txt", shell=True)
        if exit_code != 0 : 
            print("Error during mapping; exit code: ", exit_code)
            ew.exit_all(exit_code, "mapping", file_main_time, rt, freedisk, LogPath, time_string, server_name)
        end_time = time.time()
        file_main_time.write("Time of running transcripts quantification: " + ew.spend_time(start_time, end_time) + "\n")
        print("Mapping is done! ("+ew.spend_time(start_time, end_time)+")")

    if mapping =='yes' and reference == "genome":
        print("Starting mapping using ", reference, " as reference...")
        start_time = time.time()
        exit_code = subprocess.call(snakemake_cmd+"-s workflow/align_count_genome.rules 2> " + LogPath+time_string+"_align_count_genome.txt", shell=True)
        if exit_code != 0 : 
            print("Error during mapping; exit code: ", exit_code)
            ew.exit_all(exit_code, "mapping", file_main_time, rt, freedisk, LogPath, time_string, server_name)
        end_time = time.time()
        file_main_time.write("Time of running genome alignment and counting: " + ew.spend_time(start_time, end_time) + "\n")
        print("Mapping is done! ("+ew.spend_time(start_time, end_time)+")")

    if dea=='yes':
        print("Starting differential expression analysis...")
        if reference == "transcriptome":
            start_time = time.time()
            exit_code = subprocess.call(snakemake_cmd+"-s workflow/dea_trans.rules 2> " + LogPath+time_string+"_dea_trans.txt", shell=True)
            if exit_code != 0 : 
                print("Error during DEA; exit code: ", exit_code)
                ew.exit_all(exit_code, "differential expression analysis", file_main_time, rt, freedisk, LogPath, time_string, server_name)
            end_time = time.time()
            file_main_time.write("Time of running DEA transcriptome based: " + ew.spend_time(start_time, end_time) + "\n")
        elif reference == "genome":
            start_time = time.time()
            exit_code = subprocess.call(snakemake_cmd+"-s workflow/dea_genome.rules 2> " + LogPath+time_string+"_dea_genome.txt", shell=True)
            if exit_code != 0 : 
                print("Error during DEA; exit code: ", exit_code)
                ew.exit_all(exit_code, "differential expression analysis", file_main_time, rt, freedisk, LogPath, time_string, server_name)
            end_time = time.time()
            file_main_time.write("Time of running DEA genome based: " + ew.spend_time(start_time, end_time) + "\n")
        print("DEA is done! ("+ew.spend_time(start_time, end_time)+")")

        print("RASflow is done!")

    else:
        print("DEA is not required and RASflow is done!")

exit_code = 0
ew.exit_all(exit_code, '', file_main_time, rt, freedisk, LogPath, time_string, server_name)
