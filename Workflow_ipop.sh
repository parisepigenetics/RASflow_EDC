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
#SBATCH --partition=ipop-up
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --mem-per-cpu=5GB

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
echo 'RASflow_EDC version: v0.6.3, on iPOP-UP cluster'
echo '-------------------------'
echo 'Main module versions:'


start0=`date +%s`

# modules loading
module purge
module load snakemake/5.19.2

conda --version
python --version
echo 'snakemake' && snakemake --version

echo '-------------------------'
echo 'PATH:'
echo $PATH
echo '########################################'

# remove display to make qualimap run:
unset DISPLAY

# check if the workflow is already running, if not copy the configuration file and start the workflow
CONFIG_FILE="config_ongoing_run.yaml"
if test -f "$CONFIG_FILE"; then
    echo "Another run is on going, please wait for its end before restarting RASflow_EDC. "
else 
    cp configs/config_main.yaml $CONFIG_FILE && chmod 444 $CONFIG_FILE
    # run the workflow
    python main_cluster.py ipop-up
    # remove configuration file copy
    chmod 777 $CONFIG_FILE && rm $CONFIG_FILE
    
    echo '########################################'
    echo 'Job finished' $(date --iso-8601=seconds)
    end=`date +%s`
    runtime=$((end-start0))
    minute=60
    echo "---- Total runtime $runtime s ; $((runtime/minute)) min ----"

    # move logs
    cp "RASflow-$SLURM_JOB_ID.out" logs
    mkdir -p slurm_output
    mv *.out slurm_output
    
fi
