#!/bin/bash

################################ Slurm options #################################

### Job name
#SBATCH --job-name=STARindex

### Limit run time "days-hours:minutes:seconds"
#SBATCH --time=24:00:00

### Requirements
#SBATCH --partition=fast
#SBATCH --nodes=20
#SBATCH --ntasks-per-node=1
#SBATCH --mem-per-cpu=40GB

### Email
##SBATCH --mail-user=email@address
##SBATCH --mail-type=ALL

### Output
#SBATCH --output=STARindex-%j.out

################################################################################

echo '########################################'
echo 'Date:' $(date --iso-8601=seconds)
echo 'User:' $USER
echo 'Host:' $HOSTNAME
echo 'Job Name:' $SLURM_JOB_NAME
echo 'Job Id:' $SLURM_JOB_ID
echo 'Directory:' $(pwd)
echo '########################################'

start0=`date +%s`

# modules loading
module load star/2.7.5a

# index hg38 with star
STAR  --runThreadN 20 --runMode genomeGenerate --genomeDir $2 --genomeFastaFiles $1


echo '########################################'
echo 'Job finished' $(date --iso-8601=seconds)
end=`date +%s`
runtime=$((end-start0))
minute=60
echo "---- Total runtime $runtime s ; $((runtime/minute)) min ----"
