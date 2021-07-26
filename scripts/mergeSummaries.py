import pandas as pd
import sys
import os

parts = sys.argv[2:]
output = sys.argv[1]

df = pd.DataFrame()
for table in parts: 
    print(table)
    if df.empty: 
        df = pd.read_table(table, names=['feature','counts'], skiprows=1)  ###  get all rows except first one.
        with open(table) as f:
            firstline = f.readline().rstrip().split('\t')       
    else : 
        df2 = pd.read_table(table, names=['feature','counts'], skiprows=1)
        df = pd.merge(df,df2,on='feature', how="outer")
df['row_sum'] = df.sum(axis=1)
sample = os.path.dirname(firstline[1])+'/'+os.path.basename(firstline[1]).split('_0')[0]+'.bam'  ### change the name to bam without parts
df_export = df[["feature","row_sum"]]
df_export.to_csv(output, sep = "\t", header = [firstline[0],sample], index =False)    


