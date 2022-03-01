import yaml
from os import path
import pandas as pd


def check_configuration(yaml_file): 

    with open(yaml_file) as yamlfile:
        config = yaml.load(yamlfile,Loader=yaml.BaseLoader)

    error = False
    if len(config["PROJECT"]) < 3 : 
        print("Error in the configuration file 'config_main.yaml'.\nKey PROJECT: Give a name with more than 2 letters to your project.")
        error = True

    for key in ["QC","TRIMMED","MAPPING","REPEATS","DEA"] : 
        if config[key] not in ['yes', 'no', True, False] : 
            print("Error in the configuration file 'config_main.yaml'.\nKey "+key+": Put 'yes' or 'no'.")
            error = True
        
    if config["REFERENCE"] not in ["genome", "transcriptome"] : 
        print("Error in the configuration file 'config_main.yaml'.\nKey REFERENCE: Put 'genome' or 'transcriptome'.")
        error = True
        if config["REFERENCE"] == "transcriptome": 
            print("Transcriptome mapping not yet implemented.")
            error = True
            
    if not path.exists(config["METAFILE"]):
        print("Error in the configuration file 'config_main.yaml'.\nKey METAFILE: The file "+config["METAFILE"]+" doesn't exist.")
        error = True
    else : 
        metadata = pd.read_table(config["METAFILE"], header = 0)
        if list(metadata.columns) != ['sample', 'group', 'subject'] : 
            print("Error: The file "+config["METAFILE"]+" is not formated as expected.\nPlease see the example TestDataset/configs/metadata.tsv.\nThe header should be 'sample\tgroup\tsubject' and the columns have to be tab-separated.")
            error = True
        if metadata.isnull().values.any():
            print("Error: The file "+config["METAFILE"]+" is not formated as expected.\nPlease see the example TestDataset/configs/metadata.tsv.\nThe columns have to be tab-separated.")
            error = True

            
    if (config["MAPPING"] == 'yes' or config["MAPPING"] == True):  # check reference files
        if config["ALIGNER"] == "HISAT2":
            if len(config["INDEXBASE"].split('/')) > 1: 
                print("Error: The index base is not a path but the prefix of the index files for HISAT2, ie 'genome' if the index files are named 'genome.1.ht2', 'genome.2.ht2', ...")
                error = True
            if not path.exists(config["INDEXPATH"]+'/'+config["INDEXBASE"]+".1.ht2"):
                print("Error: Index files "+config["INDEXPATH"]+'/'+config["INDEXBASE"]+".xx.ht2 not found. Please check your configuration file (keys INDEXPATH and INDEXBASE).") 
                error = True
        else : 
            if not path.exists(config["INDEXPATH"]): 
                print("Error: STAR index folder "+config["INDEXPATH"]+" not found. Please check your configuration file (key INDEXPATH).")               
                error = True
        if not path.exists(config["ANNOTATION"]):
            print("Error: Annotation file "+config["ANNOTATION"]+" not found. Please check your configuration file (key ANNOTATION).")
            error = True
            
    return error
