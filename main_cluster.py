# The main script to manage the subworkflows of RASflow

import yaml
import os
import time

with open('configs/config_main.yaml') as yamlfile:
    config = yaml.load(yamlfile,Loader=yaml.BaseLoader)

# Parameters to control the workflow
project = config["PROJECT"]

## Do you need to do quality control?
qc = config["QC"]
print("Is quality control required?\n", qc)

## Do you need to do trimming?
trim = config["TRIMMED"]
print("Is trimming required?\n", trim)

## Which mapping reference do you want to use? Genome or transcriptome?
reference = config["REFERENCE"]
print("Which mapping reference will be used?\n", reference)

## Do you want to do Differential Expression Analysis (DEA)?
dea = config["DEA"]
print("Is DEA required?\n", dea)

## Do you want to visualize the results of DEA?
visualize = config["VISUALIZE"]
print("Is visualization required?\n", visualize)

# Start the workflow
print("Start RASflow on project: " + project)

## write the running time in a log file
start_time = time.localtime()
time_string = time.strftime("%Y%m%d_%H%M", start_time) # convert to '20200612_1705' format
file_main_time = open("logs/running_time_"+time_string+".txt", "a+")
file_main_time.write("\nProject name: " + project + "\n")
file_main_time.write("Start time: " + time.ctime() + "\n")

def spend_time(start_time, end_time):
    seconds = end_time - start_time
    hours = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    
    return "%d:%02d:%02d" % (hours, minutes, seconds)

WorkingDir = os.getcwd()


if qc=='yes':
    # Double check that the user really wants to do QC instead of forgetting to change the param after doing QC
        print("Start Quality Control!")
        start_time = time.time()
        os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem}\" --use-conda --jobs=30 -s workflow/quality_control.rules 2> logs/quality_control_"+time_string+".txt")
        end_time = time.time()
        file_main_time.write("Time of running QC: " + spend_time(start_time, end_time) + "\n")
        print("Quality control is done!\n Please check the report and decide whether trimming is needed\n Please remember to turn off the QC in the config file!")
        os._exit(0)
else:
    if trim=='yes':
        print("Start Trimming!")
        start_time = time.time()
        os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem}\" --use-conda --jobs=30 -s workflow/trim.rules 2> logs/trim_"+time_string+".txt")
        end_time = time.time()
        file_main_time.write("Time of running trimming:" + spend_time(start_time, end_time) + "\n")
        print("Trimming is done!")
    else:
        print("Trimming is not required")

    print("Start mapping using ", reference, " as reference!")

    if reference == "transcriptome":
        start_time = time.time()
        os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem}\" --use-conda --jobs=30 -s workflow/quantify_trans.rules 2> logs/quantify_trans_"+time_string+".txt")
        end_time = time.time()
        file_main_time.write("Time of running transcripts quantification:" + spend_time(start_time, end_time) + "\n")
    elif reference == "genome":
        start_time = time.time()
        os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem}\" --use-conda --jobs=30 -s workflow/align_count_genome.rules 2> logs/align_count_genome_"+time_string+".txt")
        end_time = time.time()
        file_main_time.write("Time of running genome alignment:" + spend_time(start_time, end_time) + "\n")

    if dea=='yes':
        print("Start doing DEA!")
        if reference == "transcriptome":
            start_time = time.time()
            os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem}\" --use-conda --jobs=30 -s workflow/dea_trans.rules 2> logs/dea_trans_"+time_string+".txt")
            end_time = time.time()
            file_main_time.write("Time of running DEA transcriptome based:" + spend_time(start_time, end_time) + "\n")
        elif reference == "genome":
            start_time = time.time()
            os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem}\" --use-conda --jobs=30 -s workflow/dea_genome.rules 2> logs/dea_genome_"+time_string+".txt")
            end_time = time.time()
            file_main_time.write("Time of running DEA genome based:" + spend_time(start_time, end_time) + "\n")
        print("DEA is done!")

        if visualize=='yes':
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

            print("Start visualization of DEA results!")
            start_time = time.time()
            os.system("snakemake -k --cluster-config cluster.yml --drmaa \" --mem={cluster.mem}\" --use-conda --jobs=30 -s workflow/visualize.rules 2> logs/visualize_"+time_string+".txt")
            end_time = time.time()
            file_main_time.write("Time of running visualization:" + spend_time(start_time, end_time) + "\n")
            print("Visualization is done!")
            print("RASflow is done!")
        else:
            print("Visualization is not required and RASflow is done!")
    else:
        print("DEA is not required and RASflow is done!")

file_main_time.write("Finish time: " + time.ctime() + "\n")
file_main_time.close()
