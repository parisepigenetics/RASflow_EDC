wget http://refgenomes.databio.org/v2/asset/hg38_chr22/hisat2_index/archive?tag=default
--2020-11-10 14:03:29--  http://refgenomes.databio.org/v2/asset/hg38_chr22/hisat2_index/archive?tag=default
Resolving refgenomes.databio.org (refgenomes.databio.org)... 18.210.227.79
Connecting to refgenomes.databio.org (refgenomes.databio.org)|18.210.227.79|:80... connected.
HTTP request sent, awaiting response... 307 Temporary Redirect
Location: http://awspds.refgenie.databio.org/hg38_chr22/hisat2_index__default.tgz [following]
--2020-11-10 14:03:29--  http://awspds.refgenie.databio.org/hg38_chr22/hisat2_index__default.tgz
Resolving awspds.refgenie.databio.org (awspds.refgenie.databio.org)... 52.216.113.243
Connecting to awspds.refgenie.databio.org (awspds.refgenie.databio.org)|52.216.113.243|:80... connected.
HTTP request sent, awaiting response... 200 OK
Length: 61159365 (58M) [application/x-tar]
Saving to: ‘archive?tag=default’

archive?tag=default       100%[===================================>]  58,33M  1,96MB/s    in 29s     

2020-11-10 14:03:58 (2,04 MB/s) - ‘archive?tag=default’ saved [61159365/61159365]

(base) mag@BI-platform:~/Documents/Plateforme_BI/GitHub/RASflow_IFB/TestDataset$ ll
total 59736
drwxr-xr-x 2 mag mag     4096 Nov 10 14:03  ./
drwxr-xr-x 4 mag mag     4096 Nov 10 14:02  ../
-rw-r--r-- 1 mag mag 61159365 Jul 11 21:48 'archive?tag=default'
(base) mag@BI-platform:~/Documents/Plateforme_BI/GitHub/RASflow_IFB/TestDataset$ mv 'archive?tag=default' hisat2_index.tgz
(base) mag@BI-platform:~/Documents/Plateforme_BI/GitHub/RASflow_IFB/TestDataset$ tar -zxvf hisat2_index.tgz 
(base) mag@BI-platform:~/Documents/Plateforme_BI/GitHub/RASflow_IFB/TestDataset/hisat2_index$ tar -d hisat2_index.tgz
hisat2_index/
hisat2_index/hg38_chr22.2.ht2
hisat2_index/hg38_chr22.3.ht2
hisat2_index/hg38_chr22.1.ht2
hisat2_index/hg38_chr22.6.ht2
hisat2_index/hg38_chr22.8.ht2
hisat2_index/hg38_chr22.7.ht2
hisat2_index/hg38_chr22.4.ht2
hisat2_index/hg38_chr22.5.ht2
(base) mag@BI-platform:~/Documents/Plateforme_BI/GitHub/RASflow_IFB/TestDataset$ ll hisat2_index/
total 135988
drwxr-xr-x 3 mag mag     4096 Nov 10 14:06 ./
drwxr-xr-x 4 mag mag     4096 Nov 10 14:02 ../
-rw-r--r-- 1 mag mag 18433223 Jul 11 20:00 hg38_chr22.1.ht2
-rw-r--r-- 1 mag mag 10673168 Jul 11 20:00 hg38_chr22.2.ht2
-rw-r--r-- 1 mag mag      818 Jul 11 20:00 hg38_chr22.3.ht2
-rw-r--r-- 1 mag mag 10673160 Jul 11 20:00 hg38_chr22.4.ht2
-rw-r--r-- 1 mag mag 18962269 Jul 11 20:00 hg38_chr22.5.ht2
-rw-r--r-- 1 mag mag 10860276 Jul 11 20:00 hg38_chr22.6.ht2
-rw-r--r-- 1 mag mag       12 Jul 11 20:00 hg38_chr22.7.ht2
-rw-r--r-- 1 mag mag        8 Jul 11 20:00 hg38_chr22.8.ht2

