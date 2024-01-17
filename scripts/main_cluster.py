# The main script to manage the subworkflows of RASflow_EDC

import yaml
import os
import time
import sys
import subprocess
import check_config as ch
import edc_workflows as ew
import sched
from datetime import datetime

      
# Parameters to control the workflow
with open('config_ongoing_run.yaml') as yamlfile:
    config = yaml.load(yamlfile,Loader=yaml.BaseLoader)
# check the configuration file
config_error = ch.check_configuration('config_ongoing_run.yaml')
if config_error : sys.exit()
    
project = config["PROJECT"]
metadata = config["METAFILE"]
resultpath = config["RESULTPATH"]
reference = config["REFERENCE"]

## write the running time in a log file
start_time = time.localtime()
time_string = time.strftime("%Y%m%dT%H%M", start_time) # convert to '20200612T1705' format
log_path = resultpath+"/"+project+"/logs/"
os.makedirs(log_path, exist_ok=True)
file_main_time = open(log_path+time_string+"_running_time.txt", "a+")
file_main_time.write("Project name: " + project + "\nStart time: " + time.ctime() + "\n")


## cluster specific part
account = os.getcwd().split('projects')[1].split('/')[1]
with open('configs/cluster_config.yaml') as yamlfile:
    cluster = yaml.load(yamlfile,Loader=yaml.BaseLoader)
server_command = cluster["server_command"]
server_name = cluster["name"]

## main Snakemake command - using cluster profile 
snakemake_cmd = "snakemake --profile=configs/ "

# Monitore disk usage (every minute)   
try: writting_dir = resultpath.split('projects')[1].split('/')[1]
except: writting_dir = os.getcwd().split('projects')[1].split('/')[1]
freedisk = open(log_path+time_string+"_free_disk.txt", "a+")
total, extra = ew.get_quotas(writting_dir, server_command) 
freedisk.write("# quota:"+str(total)+"T limit:"+ str(extra)+ "T\ntime\tfree_disk\n")
rt = ew.RepeatedTimer(60, ew.get_free_disk, total, writting_dir, server_command, freedisk)

# Save run ID
print("-------------------------\n| RUN ID : "+time_string+ " |\n-------------------------")

# Download singularity image if necessary 
singularity_image =  sys.argv[1]
print("Singularity image source: ", singularity_image)
if not os.path.exists("rasflow_edc.simg"): 
    print("Download Singularity image\n")
    output = subprocess.check_output("wget --no-verbose "+singularity_image, stderr=subprocess.STDOUT, shell=True)
    print(output.decode("utf-8"))
    
# save the configuration (after getting sing image)
ew.saveconf(metadata, log_path, time_string, "RNA")
          
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
    ew.save_fastq_size(metadata, config["READSPATH"])
    
else:
    print("The workflow will stop after FASTQ quality control.")
    
print("-------------------------\nWorkflow running....")

if qc=='yes':
    start = "Starting FASTQ Quality Control..."
    step = "quality_control"
    step_lit = "quality control"
    end = "FASTQ quality control is done!"
    end2 = "Please check the report and decide whether trimming is needed or not.\n \
To run the rest of the analysis, please remember to turn off the QC in the configuration file."
    ew.execute_step(start, snakemake_cmd, step, step_lit, file_main_time, rt, freedisk, log_path, time_string, server_name, end, end2)
    
else:
    if trim=='yes':
        start = "Starting Trimming..."
        step = "trim"
        step_lit = "trimming"
        end = "Trimming is done!"
        end2 = ""
        ew.execute_step(start, snakemake_cmd, step, step_lit, file_main_time, rt, freedisk, log_path, time_string, server_name, end, end2)

    if mapping =='yes' and reference == "transcriptome":
        start = "Starting mapping using transcriptome as reference..."
        step = "quantify_trans"
        step_lit = "transcripts quantification"
        end = "Transcripts quantification is done!"
        end2 = ""
        ew.execute_step(start, snakemake_cmd, step, step_lit, file_main_time, rt, freedisk, log_path, time_string, server_name, end, end2)

    if mapping =='yes' and reference == "genome":
        start = "Starting mapping using genome as reference..."
        step = "align_count_genome"
        step_lit = "mapping"
        end = "Mapping is done!"
        end2 = ""
        ew.execute_step(start, snakemake_cmd, step, step_lit, file_main_time, rt, freedisk, log_path, time_string, server_name, end, end2)
        
    if dea=='yes' and reference == "transcriptome":
        start = "Starting differential expression analysis..."
        step = "dea_trans"
        step_lit = "DEA"
        end = "DEA is done!"
        end2 = ""
        ew.execute_step(start, snakemake_cmd, step, step_lit, file_main_time, rt, freedisk, log_path, time_string, server_name, end, end2)
    
    if dea=='yes' and reference == "genome":
        start = "Starting differential expression analysis..."
        step = "dea_genome"
        step_lit = "DEA"
        end = "DEA is done!"
        end2 = ""
        ew.execute_step(start, snakemake_cmd, step, step_lit, file_main_time, rt, freedisk, log_path, time_string, server_name, end, end2)
        
print("RASflow is done!")
exit_code = 0
ew.exit_all(exit_code, '', file_main_time, rt, freedisk, log_path, time_string, server_name)
