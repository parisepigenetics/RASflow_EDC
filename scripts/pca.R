# load the libraries
library(DESeq2)
library(RColorBrewer)
library(yaml)
library(pheatmap)
library(Glimma)
library(limma)
library(ggplot2)

# passing the params from command line
args <- commandArgs(TRUE)
counts.path <- args[1]
suffix <- args[2]
output.path <- args[3]


# extract the information from the yaml file
yaml.file <- yaml.load_file('config_ongoing_run.yaml')
metafile <- yaml.file$METAFILE

## adding the experimental plan
splan <-read.csv(metafile, sep="\t",row.names=1, header=TRUE)

# load count files
countload <-function(input_path, samples){
    message(paste("loading gene counts from", input_path, "...", sep=" "))
    exprs.in <-lapply(samples, function(x) { paste(input_path,'/',x,suffix,sep="")})                                 
    counts.exprs <-lapply(exprs.in, read.csv, sep="\t", header=FALSE,row.names=1, check.names=FALSE)
    counts.exprs <-data.frame(lapply(counts.exprs, "[", 1))
    counts.exprs[] <- lapply(counts.exprs, as.integer)
    colnames(counts.exprs) <-samples
    message("Done")
    counts.exprs
}

d <- countload(paste(counts.path, sep = ""),rownames(splan))

message("size of the table")
message("number of genes")
message(dim(d)[1])
message("number of samples")
message(dim(d)[2])
message("number of counts per sample")
print(colSums(d))

## Building DESeqDataSet
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
rownames(sampleDistMatrix) <- paste(rownames(colData(rld)), colData(rld)[, c("condition")],sep=":")
colnames(sampleDistMatrix) <- rownames(colData(rld))
colors <- colorRampPalette(rev(brewer.pal(9,"Blues")))(255)
if (suffix == "_countGenes.tsv") {
    title <- "Sample distances for genes"
    filename <- 'Heatmap_samples.pdf'
} 
if (suffix == "_countTE.tsv") {
    title <- "Sample distances for repeats"
    filename <- 'Heatmap_samples_TE.pdf'
} 
pheatmap(sampleDistMatrix, clustering_distance_cols = sampleDists, clustering_distance_rows = sampleDists, color = colors, main=title, filename=paste(output.path,"/",filename, sep = ""))



## Export the plots

if (suffix == "_countGenes.tsv") {
    title <- 'PCA using gene counts'
    filename <- 'PCA.pdf'
    
} 
if (suffix == "_countTE.tsv") {
    title <- 'PCA using repeat counts'
    filename <- 'PCA_TE.pdf'
} 

pdf(file = file.path(paste(output.path,"/",filename, sep = "")), width = 15, height = 15, title = 'Exploratory analysis')
  par(mfrow = c(2,1))
  # run PCA
  #DESeq2::plotPCA(rld, intgroup =c("condition"), ntop=1000)
  pca = DESeq2::plotPCA(rld, intgroup=c("condition"), returnData=TRUE, ntop=1000)
  ggplot(data=pca, aes_string(x="PC1", y="PC2", color="group")) + geom_point(size=3) + 
    labs(title=title, x =paste0("PC1: ",round(attr(pca, 'percentVar')[1] * 100),"% variance"), y = paste0("PC2: ",round(attr(pca, 'percentVar')[2] * 100),"% variance")) +
    coord_fixed()

  boxplot(log2(1+d),las=2, ylab="raw counts (log2)", col="gray70", pch=16, main = "Raw counts per sample")
  dev.off()

## Glimma interactive MDS
html <- 'MDSPlot'
glMDSPlot(dds, groups=dds$samples$group,path=output.path, folder="Glimma",html=html, launch=FALSE)
