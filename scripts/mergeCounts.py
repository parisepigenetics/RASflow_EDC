import pandas as pd
import sys
import os

counter = sys.argv[1]
output = sys.argv[2]
parts = sys.argv[3:]


df = pd.DataFrame()

if parts != []:
    for table in parts: 
        print(table)
        if df.empty: 
            df = pd.read_table(table, names=['feature','counts'])
        else : 
            df2 = pd.read_table(table, names=['feature','counts'])
            df = pd.merge(df,df2,on='feature', how="outer")
                                
    df['row_sum'] = df.sum(axis=1)
    df_export = df[["feature","row_sum"]]
    df_export.to_csv(output, sep = "\t", header = False, index =False)