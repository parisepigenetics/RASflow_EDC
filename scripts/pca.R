# load the libraries
library(DESeq2)
#if (!require("RColorBrewer")) install.packages("RColorBrewer")
library(RColorBrewer)
library(yaml)
#if (!require("pheatmap")) {install.packages("pheatmap")}
library(pheatmap)

# passing the params from command line
args <- commandArgs(TRUE)
counts.path <- args[1]

# extract the information from the yaml file
yaml.file <- yaml.load_file('configs/config_main.yaml')
metafile <- yaml.file$METAFILE


# load count files
countload <-function(input_path){
    message(paste("loading gene counts from", input_path, "...", sep=" "))
    exprs.in <-list.files(path=input_path,pattern="count.tsv",full.names=TRUE,recursive=TRUE)
    counts.exprs <-lapply(exprs.in, read.csv, sep="\t", header=FALSE,row.names=1, check.names=FALSE)
    counts.exprs <-data.frame(lapply(counts.exprs, "[", 1))
    colnames(counts.exprs) <-basename(exprs.in)
    message("Done")
    counts.exprs
}

d <- countload(counts.path)

## rename columns
if (lengths(strsplit(as.character(colnames(d)), "\\_"))[1] == 2) {
    colnames(d) <- sapply(strsplit(as.character(colnames(d)), "\\_"),  "[", 1)
}

message("size of the table")
message("number of genes")
message(dim(d)[1])
message("number of samples")
message(dim(d)[2])
message("number of counts per sample")
print(colSums(d))


## adding the experimental plan
splan <-read.csv(metafile, sep="\t",row.names=1, header=TRUE)
dds <-DESeqDataSetFromMatrix(countData=d,DataFrame(condition=splan$group),~condition)

## Estimate size factors
dds <-estimateSizeFactors(dds)

## Remove lines with only zeros
dds <- dds[rowSums(counts(dds))>0, ]
## Run the rlog normalization
rld <-rlog(dds, blind=TRUE)

## heatmaps
## Obtain the sample euclidean distances
sampleDists <- dist(t(assay(rld)))
sampleDistMatrix <- as.matrix(sampleDists)
## Add names based on intgroup
rownames(sampleDistMatrix) <- apply(as.data.frame(colData(rld)[, c("condition")]), 1,
    paste, collapse = ' : ')
colnames(sampleDistMatrix) <- NULL
colors <- colorRampPalette(rev(brewer.pal(9,"Blues")))(255)
pheatmap(sampleDistMatrix, clustering_distance_rows = sampleDists, clustering_distance_cols = sampleDists, color = colors, main="sample distance", filename=paste(counts.path,"/","heatmap.pdf", sep = ""))

## Export the plots

pdf(file = file.path(paste(counts.path,"/",'PCA.pdf', sep = "")), width = 15, height = 15, title = 'Exploratory analysis')
  par(mfrow = c(2,1))
  boxplot(log2(1+d),las=2, ylab="raw counts (log2)", col="gray70", pch=16, main = "Raw counts per sample")
  # run PCA
  DESeq2::plotPCA(rld, intgroup =c("condition"), ntop=1000)
  dev.off()


