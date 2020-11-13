(base) [mhennion @ clust-slurm-client 15:00]$ hisat2_index : wget https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz
--2020-11-12 15:00:46--  https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/chr22.fa.gz
Resolving hgdownload.soe.ucsc.edu (hgdownload.soe.ucsc.edu)... 128.114.119.163
Connecting to hgdownload.soe.ucsc.edu (hgdownload.soe.ucsc.edu)|128.114.119.163|:443... connected.
HTTP request sent, awaiting response... 200 OK
Length: 12255678 (12M) [application/x-gzip]
Saving to: ‘chr22.fa.gz’
(base) [mhennion @ clust-slurm-client 15:00]$ hisat2_index : gzip -d chr22.fa.gz 

(base) [mhennion @ clust-slurm-client 17:09]$ hisat2_index : sbatch hisat_index.sh 
Submitted batch job 13631272


hisat2-build chr22.fa hisat2_hg38_chr22
