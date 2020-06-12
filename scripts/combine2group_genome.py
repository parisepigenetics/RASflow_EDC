# combine the samples belonging to the same group together

import yaml
import pandas as pd
import numpy as np
# import ipdb

def load_globals():
    
    global samples; global groups; global config; global input_path; global output_path

    with open('configs/config_main.yaml') as yamlfile:
        config = yaml.load(yamlfile)
    
    samples = np.array(pd.read_table(config["METAFILE"], header = 0)['sample'])

    groups = np.array(pd.read_table(config["METAFILE"], header = 0)['group'])

    input_path = config["FINALOUTPUT"] + "/" + config["PROJECT"] + "/genome/countFile"
    output_path = config["FINALOUTPUT"] + "/" + config["PROJECT"] + "/genome/dea"


def main():

    load_globals()

    groups_unique = np.unique(groups)

    num_samples = len(samples)
    num_groups_unique = len(groups_unique)

    id_list = get_id_list()
  
    for name_group in groups_unique:
        combine_group(name_group, id_list)

def combine_group(name_group, id_list):
    index_group = [index for index, element in enumerate(groups) if element == name_group]  # all the index of this group
    samples_group = samples[index_group]  # the samples belonging to this group

    group_count = pd.DataFrame()
    group_count['ID'] = id_list

    for sample in samples_group:
        group_count["sample_" + str(sample)] = np.array(pd.read_table(input_path + "/" + str(sample) + "_count.tsv", header = None))[:, 1]
    
    # write to file
    group_count.to_csv(output_path + "/countGroup/" + str(name_group) + "_gene_count.tsv", sep = "\t", header = True, index = False)

def get_id_list():

    # extract the id list from the count file
    id_list = np.array(pd.read_table(input_path + '/' + str(samples[0]) + "_count.tsv", header = None))[:, 0]
    return id_list


if __name__ == "__main__":
    main()

