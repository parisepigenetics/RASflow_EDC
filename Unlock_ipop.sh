#!/bin/bash

################################ Slurm options #################################

### Job name
#SBATCH --job-name=Unlock

### Limit run time "days-hours:minutes:seconds"
#SBATCH --time=24:00:00

### Requirements
#SBATCH --partition=ipop-up
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
##SBATCH --mem-per-cpu=8GB

### Email
##SBATCH --mail-user=email@address
##SBATCH --mail-type=ALL

### Output
#SBATCH --output=Unlock-%j.out

################################################################################

echo '########################################'
echo 'Date:' $(date --iso-8601=seconds)
echo 'User:' $USER
echo 'Host:' $HOSTNAME
echo 'Job Name:' $SLURM_JOB_NAME
echo 'Job Id:' $SLURM_JOB_ID
echo 'Directory:' $(pwd)
echo '########################################'

# modules loading
module load snakemake/5.19.2

# unlock 
snakemake --unlock --drmaa -s workflow/quality_control.rules

mkdir -p slurm_output
mv Unlock-* slurm_output

echo "Working directory unlocked"
