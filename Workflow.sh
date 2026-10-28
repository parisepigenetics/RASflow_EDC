#!/bin/bash

################################ Slurm options #################################

### Job name
#SBATCH --job-name=RASflow

### Output
#SBATCH --output=RASflow-%j.out  # both STDOUT and STDERR
##SBATCH -o slurm.%N.%j.out  # STDOUT file with the Node name and the Job ID
##SBATCH -e slurm.%N.%j.err  # STDERR file with the Node name and the Job ID

### Limit run time "days-hours:minutes:seconds"
#SBATCH --time=24:00:00

### Requirements
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem-per-cpu=1GB

### Email
##SBATCH --mail-user=email@address
##SBATCH --mail-type=ALL

################################################################################

echo '########################################'
echo 'Date:' $(date --iso-8601=seconds)
echo 'User:' $USER
echo 'Host:' $HOSTNAME
echo 'Job Name:' $SLURM_JOB_NAME
echo 'Job Id:' $SLURM_JOB_ID
echo 'Directory:' $(pwd)
echo '########################################'
echo 'RASflow_EDC version: v2.1'
echo '-------------------------'
echo 'Main module versions:'


start0=`date +%s`


# include parse_yaml function
. scripts/parse_yaml.sh
# read yaml file
eval $(parse_yaml configs/cluster_config.yaml "config_")

# make config.yaml for snakemake to work on the cluster without DRMAA
cat configs/.config_template.yaml > configs/config.yaml
echo "  - partition=$config_partition" >> configs/config.yaml

# modules loading
module purge
module load $config_modules # access yaml content
echo "Loaded modules : $config_modules"
python --version
echo 'snakemake' && snakemake --version

echo '-------------------------'
echo 'PATH:'
echo $PATH
echo '########################################'

# remove display to make qualimap run:
unset DISPLAY

# define singularity image source
#singularity_image="https://zenodo.org/record/7303435/files/rasflow_edc.simg"
image_version="v2.1"
echo "rasflow_edc_$image_version.sif"

# Check md5sum and download if not OK, or not present
if [ -f "rasflow_edc_$image_version.sif" ]; then
    echo "rasflow_edc_$image_version.sif exists. Checking md5sum..."
    
    if md5sum -c configs/.md5sum.txt ; then
        echo "md5sum check succeeded."
    else
        echo "Old or corrupted singularity image. Download $image_version from $singularity_image ..."
        wget --no-verbose -O rasflow_edc_$image_version.sif $singularity_image
        if md5sum -c configs/.md5sum.txt; then 
            echo "Image downloaded, md5sum check succeeded."
        else # if it doesn't work, then quit. 
            echo "Error checking the singularity image after the download."
            exit 1
        fi
    fi
else 
    echo "rasflow_edc.sif does not exist. Download $image_version from $singularity_image ..."
    wget --no-verbose -O rasflow_edc_$image_version.sif $singularity_image
    if md5sum -c configs/.md5sum.txt; then 
            echo "Image downloaded, md5sum check succeeded."
    else # if it doesn't work, then quit. 
        echo "Error checking the singularity image after the download."
        exit 1
    fi        
fi
echo "Singularity image $image_version ready!"

# make a sim link to keep rasflow_edc.sif in the rules
rm -f rasflow_edc.sif
ln -s rasflow_edc_$image_version.sif rasflow_edc.sif


# check if the workflow is already running, if not copy the configuration file and start the workflow
CONFIG_FILE="config_ongoing_run.yaml"
if test -f "$CONFIG_FILE"; then
    echo "Another run is on going, please wait for its end before restarting RASflow_EDC. "
else 
    cp configs/config_main.yaml $CONFIG_FILE && chmod 444 $CONFIG_FILE
    # run the workflow
    python scripts/main_cluster.py $singularity_image
    # remove configuration file copy
    chmod 777 $CONFIG_FILE && rm $CONFIG_FILE
    
    echo '########################################'
    echo 'Job finished' $(date --iso-8601=seconds)
    end=`date +%s`
    runtime=$((end-start0))
    minute=60
    echo "---- Total runtime $runtime s ; $((runtime/minute)) min ----"

    # move logs
    mkdir -p logs
    mv "RASflow-$SLURM_JOB_ID.out" logs
fi
