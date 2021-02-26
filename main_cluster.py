# The main script to manage the subworkflows of RASflow

import yaml
import os
import time
import sys
import subprocess
import scripts.reporting as reporting

server = sys.argv[1]
if server == "rpbs":
    option = " -p epigenetique"
    MainPath = "/scratch/epigenetique/workflows/RASflow_RPBS/"
elif server == "ifb" :
    option = ""
    MainPath = ""

with open('configs/config_main.yaml') as yamlfile:
    config = yaml.load(yamlfile,Loader=yaml.BaseLoader)

# Parameters to control the workflow
project = config["PROJECT"]

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
    print("Is mapping required?\n", mapping)

    ## Which mapping reference do you want to use? Genome or transcriptome?
    reference = config["REFERENCE"]
    print("Which mapping reference will be used?\n", reference)

    ## Do you want to do Differential Expression Analysis (DEA)?
    dea = config["DEA"]
    print("Is DEA required?\n", dea)

else:
    print("The workflow will stop after FASTQ quality control.")

## write the running time in a log file
start_time = time.localtime()
time_string = time.strftime("%Y%m%dT%H%M", start_time) # convert to '20200612T1705' format

resultpath = config["RESULTPATH"]
LogPath = resultpath+"/"+project+"/logs/"
os.makedirs(LogPath, exist_ok=True)
file_main_time = open(LogPath+time_string+"_running_time.txt", "a+")
file_main_time.write("\nProject name: " + project + "\n")
file_main_time.write("Start time: " + time.ctime() + "\n")

# save the configuration
metadata = config["METAFILE"]
os.system("(echo && echo \"==========================================\" && echo && echo \"SAMPLE PLAN\") | cat configs/config_main.yaml - "+metadata+" >" + LogPath+time_string+"_configuration.txt")

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
        os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus} "+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs=30 --latency-wait 40 -s "+MainPath+"workflow/quality_control.rules 2> " + LogPath+time_string+"_quality_control.txt")
        end_time = time.time()
        file_main_time.write("Time of running QC: " + spend_time(start_time, end_time) + "\n")
        print("FASTQ quality control is done! ("+spend_time(start_time, end_time)+")\n Please check the report and decide whether trimming is needed or not.\n To run the rest of the analysis, please remember to turn off the QC in the configuration file.")

else:
    if trim=='yes':
        print("Starting Trimming...")
        start_time = time.time()
        os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus} "+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs=30 -s "+MainPath+"workflow/trim.rules 2> " + LogPath+time_string+"_trim.txt")
        end_time = time.time()
        file_main_time.write("Time of running trimming: " + spend_time(start_time, end_time) + "\n")
        print("Trimming is done! ("+spend_time(start_time, end_time)+")")
    else:
        print("Trimming is not required.")


    if mapping =='yes' and reference == "transcriptome":
        print("Starting mapping using ", reference, " as reference...")
        start_time = time.time()
        os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus} "+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs=30 -s "+MainPath+"workflow/quantify_trans.rules 2> " + LogPath+time_string+"_quantify_trans.txt")
        end_time = time.time()
        file_main_time.write("Time of running transcripts quantification: " + spend_time(start_time, end_time) + "\n")
        print("Mapping is done! ("+spend_time(start_time, end_time)+")")

    if mapping =='yes' and reference == "genome":
        print("Starting mapping using ", reference, " as reference...")
        start_time = time.time()
        os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus} "+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs=30 -s "+MainPath+"workflow/align_count_genome.rules 2> " + LogPath+time_string+"_align_count_genome.txt")
        end_time = time.time()
        file_main_time.write("Time of running genome alignment and counting: " + spend_time(start_time, end_time) + "\n")
        print("Mapping is done! ("+spend_time(start_time, end_time)+")")

    if dea=='yes':
        print("Starting differential expression analysis...")
        if reference == "transcriptome":
            start_time = time.time()
            os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus} "+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs=30 -s "+MainPath+"workflow/dea_trans.rules 2> " + LogPath+time_string+"_dea_trans.txt")
            end_time = time.time()
            file_main_time.write("Time of running DEA transcriptome based: " + spend_time(start_time, end_time) + "\n")
        elif reference == "genome":
            start_time = time.time()
            os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem} -J {cluster.name} -c {cluster.cpus} "+option+"\" --use-conda --conda-prefix "+MainPath+".snakemake/conda/ --jobs=30 -s "+MainPath+"workflow/dea_genome.rules 2> " + LogPath+time_string+"_dea_genome.txt")
            end_time = time.time()
            file_main_time.write("Time of running DEA genome based: " + spend_time(start_time, end_time) + "\n")
        print("DEA is done! ("+spend_time(start_time, end_time)+")")
        reporting.main(time_string)

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

