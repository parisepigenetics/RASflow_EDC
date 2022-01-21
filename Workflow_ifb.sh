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
echo 'RASflow_IFB version: v0.6.2'
echo '-------------------------'
echo 'Main module versions:'


start0=`date +%s`

# modules loading
module purge
module load conda snakemake/6.5.0 slurm-drmaa
conda --version
python --version
echo 'snakemake' && snakemake --version

echo '-------------------------'
echo 'PATH:'
echo $PATH
echo '########################################'

# remove display to make qualimap run:
unset DISPLAY

# copy configuration file
cp configs/config_main.yaml config_ongoing_run.yaml && chmod -w config_ongoing_run.yaml

# What you actually want to launch
python main_cluster.py ifb


echo '########################################'
echo 'Job finished' $(date --iso-8601=seconds)
end=`date +%s`
runtime=$((end-start0))
minute=60
echo "---- Total runtime $runtime s ; $((runtime/minute)) min ----"

# remove configuration file copy
chmod +w config_ongoing_run.yaml && rm config_ongoing_run.yaml

# move logs
cp "RASflow-$SLURM_JOB_ID.out" logs
mkdir -p slurm_output
mv *.out slurm_output
