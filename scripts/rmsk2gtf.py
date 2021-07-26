import sys

rmsk_file = sys.argv[1]
te_gtf_file = sys.argv[2]

te_gtf = open(te_gtf_file,'w')

ID = rmsk_file.split('.')[-2].split('/')[-1]
dup={}
with open(rmsk_file, 'r') as rmsk:
    for line in rmsk:
        if line.startswith('#') == False:
            ss=line.split('\t')
            chrom = ss[5]
            start = int(ss[6])+1
            end = int(ss[7])
            L = int(ss[1])
            strand = ss[9]
            gene_id = ss[10]
            if gene_id in dup:
                dup[gene_id] += 1
                transcript_id = gene_id+'_dup'+str(dup[gene_id])
            else :
                dup[gene_id] = 0
                transcript_id = gene_id
            family_id = ss[12]
            class_id = ss[11]
            te_gtf.write(f"{chrom}\t{ID}_rmsk\ttranscript\t{start}\t{end}\t{L}\t{strand}\t.\tgene_id \"{gene_id}\"; transcript_id \"{transcript_id}\"; family_id \"{family_id}\"; class_id \"{class_id}\";\n")

te_gtf.close()

