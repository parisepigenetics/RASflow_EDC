# load the libraries
library(DESeq2)
library(RColorBrewer)
library(yaml)
library(pheatmap)
library(Glimma)
library(limma)
library(ggplot2)
library(tximport)

# passing the params from command line
args <- commandArgs(TRUE)
counts.path <- args[1]
output.path <- args[2]


# extract the information from the yaml file
yaml.file <- yaml.load_file('config_ongoing_run.yaml')
metafile <- yaml.file$METAFILE

## adding the experimental plan
splan <-read.csv(metafile, sep="\t",row.names=1, header=TRUE)

# load count files
countload <-function(input.path, samples){
    message(paste("loading gene counts from", input.path, "...", sep=" "))
    files <- file.path(input.path, samples, "quant.sf")
    names(files) <- samples
    txi <- tximport(files, type = "salmon", txOut = TRUE, countsFromAbundance = "no")
    message("Done")
    txi
}


txi <- countload(paste(counts.path, sep = ""),rownames(splan))

txi.counts <- txi$counts
message("size of the table")
message("number of transcripts")
message(dim(txi.counts)[1])
message("number of samples")
message(dim(txi.counts)[2])
message("number of counts per sample")
print(colSums(txi.counts))

## Building DESeqDataSet
dds <- DESeqDataSetFromTximport(txi, DataFrame(condition=splan$group),~condition)

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
rownames(sampleDistMatrix) <- paste(rownames(colData(rld)), colData(rld)[, c("condition")],sep=":")
colnames(sampleDistMatrix) <- rownames(colData(rld))
colors <- colorRampPalette(rev(brewer.pal(9,"Blues")))(255)
title <- "Sample distances for transcripts"
filename <- 'Heatmap_samples.pdf'
 
pheatmap(sampleDistMatrix, clustering_distance_cols = sampleDists, clustering_distance_rows = sampleDists, color = colors, main=title, filename=paste(output.path,"/",filename, sep = ""))



## Export the plots

title <- 'PCA using transcripts counts'
filename <- 'PCA.pdf'
    

pdf(file = file.path(paste(output.path,"/",filename, sep = "")), width = 15, height = 15, title = 'Exploratory analysis')
  par(mfrow = c(2,1))
  # run PCA
  pca = DESeq2::plotPCA(rld, intgroup=c("condition"), returnData=TRUE, ntop=1000)
  ggplot(data=pca, aes_string(x="PC1", y="PC2", color="group")) + geom_point(size=3) + 
    labs(title=title, x =paste0("PC1: ",round(attr(pca, 'percentVar')[1] * 100),"% variance"), y = paste0("PC2: ",round(attr(pca, 'percentVar')[2] * 100),"% variance")) +
    coord_fixed()

  boxplot(log2(1+txi.counts),las=2, ylab="raw counts (log2)", col="gray70", pch=16, main = "Raw counts per sample")
  dev.off()

## Glimma interactive MDS
html <- 'MDSPlot'
glMDSPlot(dds, groups=dds$samples$group,path=output.path, folder="Glimma",html=html, launch=FALSE)
