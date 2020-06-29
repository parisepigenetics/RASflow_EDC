#!/bin/bash

################################ Slurm options #################################

### Job name
##SBATCH --job-name=QC

### Output
##SBATCH --output=/shared/projects/YourProjectName/RASflow_IFB/slurm_output/QC-%j.out

### Limit run time "days-hours:minutes:seconds"
#SBATCH --time=24:00:00

### Requirements
#SBATCH --partition=fast
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
echo 'RASflow_IFB version: v0.2'
echo '-------------------------'
echo 'Main module versions:'


start0=`date +%s`

# modules loading
module load snakemake python conda slurm-drmaa
python --version
echo 'snakemake' && snakemake --version
conda --version
echo '-------------------------'
# remove display to make qualimap run:
unset DISPLAY

# What you actually want to launch
python /shared/projects/YourProjectName/RASflow_IFB/main_cluster.py


echo '########################################'
echo 'Job finished' $(date --iso-8601=seconds)
end=`date +%s`
runtime=$((end-start0))
minute=60
echo "---- Total runtime $runtime s ; $((runtime/minute)) min ----"
