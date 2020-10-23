# load the librariesdea.path
library(yaml)
library(hash)
library(mygene)
library(EnhancedVolcano)
library(gplots)
library(RColorBrewer)
library(pheatmap)
library(DESeq2)

# ====================== load parameters in config file ======================

# passing the params from command line
args <- commandArgs(TRUE)
dea.path <- args[1]
counts.path <- args[2]
out.path <- args[3]

# load the config file
yaml.file <- yaml.load_file('configs/config_main.yaml')

# extract the information from the yaml file
controls <- yaml.file$CONTROL
treats <- yaml.file$TREAT
dea.tool <- yaml.file$DEATOOL
metafile <- yaml.file$METAFILE
splan <-read.csv(metafile, sep="\t",row.names=1, header=TRUE)

# check the number of comparisons
num.control <- length(controls)  # number of comparisons that the user wants to do
num.treat <- length(treats)  # should equals to num.control

if (num.control != num.treat) {
  message("Error: The number of Control groups don't match with the number of Treated groups!")
  message("Please check CONTROL and TREAT in config_main.yaml")
  quit(save = 'no')
}

num.comparison <- num.control

# function to plot volcano plot and heatmap
plot.volcano.heatmap <- function(name.control, name.treat) {
  message(paste("---------------","Comparing groups", name.control, "and",  name.treat, "---------------", sep=" "))
  file.dea.table <- paste(dea.path, "/dea_", name.control, "_", name.treat, ".tsv", sep = "")
  norm <- paste(dea.path, "/", name.control, '_', name.treat, '_NormCounts.tsv', sep = "")
  dea.table <- read.table(file.dea.table, header = TRUE, row.names = 1)
    
  # sort the dea table: ascending of FDR then descending of absolute valued of logFC
  if (dea.tool == 'edgeR') {
    dea.table <- dea.table[order(dea.table$FDR, -abs(dea.table$logFC), decreasing = FALSE), ]  
  } else if (dea.tool == 'DESeq2') {
    dea.table <- dea.table[order(dea.table$padj, -abs(dea.table$log2FoldChange), decreasing = FALSE), ]
  }
  gene.id.dea <- row.names(dea.table)
  gene.id.dea <- sapply(strsplit(as.character(gene.id.dea), "\\."),  "[", 1)
  gene.symbol.dea.all <- queryMany(gene.id.dea, scopes = 'ensembl.gene', fields = 'symbol')
  
  h <- hash()
  for (i in 1:nrow(gene.symbol.dea.all)) {
    query <- gene.symbol.dea.all$query[i]
    symbol <- gene.symbol.dea.all$symbol[i]
    if (has.key(query, h)) {  # if there's duplicate for the same query
      h[[query]] <- paste(hash::values(h, keys = query), symbol, sep = ', ')
    } else {
      if (is.na(symbol)) {  # if there's no hit for the query, keep the original id
        h[[query]] <- query
      } else {
        h[[query]] <- symbol
      }
    }
  }
  
  gene.dea <- gene.id.dea
  for (i in c(1:length(gene.dea))) {
    gene.dea[i] <- h[[gene.id.dea[i]]]
  }

  # volcano plot
  if (dea.tool == 'edgeR') {
  #  fig.volcano <- EnhancedVolcano(dea.table, lab = gene.dea, xlab = bquote(~Log[2]~ "fold change"), x = 'logFC', y = 'FDR', pCutoff = 10e-5, col = c("grey30", "orange2", "royalblue", "red2"),
   #                              FCcutoff = 1, xlim = c(-5, 5), ylim = c(0, 10), transcriptPointSize = 1.5, title = NULL, subtitle = NULL) 
  xlabel <- 'logFC' 
  ylabel <- 'FDR'
  } else if (dea.tool == 'DESeq2') {
    xlabel <- 'log2FoldChange'
    ylabel <- 'padj'
  }
  fig.volcano <- EnhancedVolcano(dea.table, lab = gene.dea, xlab = bquote(~Log[2]~ "fold change"), x = xlabel, y = ylabel, pCutoff = 10e-5, col = c("grey30", "orange2", "royalblue", "red2"),
                                 FCcutoff = 1, title = dea.tool, subtitle = paste(name.control, 'vs', name.treat, sep = ' '))
  pdf(file = file.path(out.path, paste('volcano_plot_', name.control, '_', name.treat, '.pdf', sep = '')), width = 9, height = 7)
  print(fig.volcano)
  dev.off()

  # heatmap
  #norm.table.control <- read.table(norm.control, header = TRUE, row.names = 1)
  #norm.table.treat <- read.table(norm.treat, header = TRUE, row.names = 1)
  
  norm.table <- read.table(norm, header = TRUE, row.names = 1)
    
  #num.control <- dim(norm.table.control)[2]
  #num.treat <- dim(norm.table.treat)[2]

  #norm.table <- cbind(norm.table.control, norm.table.treat)
  groups <- c(name.control, name.treat)
  splan.control <- splan[splan$group %in% c(name.control), ]
  #samples.control <- row.names(splan.control)
  splan.treat <- splan[splan$group %in% c(name.treat), ]
  #samples.treat <- row.names(splan.treat)
  num.control <- nrow(splan.control) 
  num.treat <- nrow(splan.treat)  

  # instead using all genes, only use the top 20 genes in dea.table
  id2 <- row.names(dea.table)
  index.deg <- which(row.names(norm.table) %in% id2[1:20])
  norm.table.deg <- norm.table[index.deg,]

  gene.id.norm.table <- rownames(norm.table.deg)
  gene.id.norm.table <- sapply(strsplit(as.character(gene.id.norm.table), "\\."),  "[", 1)
  gene.symbol.norm.table <- queryMany(gene.id.norm.table, scopes = 'ensembl.gene', fields = 'symbol')$symbol

  # if can't find a symbol for the id, then keep the id as it is
  gene.norm.table <- gene.symbol.norm.table
  for (i in c(1:length(gene.norm.table))) {
    if (is.na(gene.norm.table[i])) {
      gene.norm.table[i] <- gene.id.norm.table[i]
    }
  }

  palette <- c("#000000ac", "#9d9d9dff")
  palette.group <- c(rep(palette[1], num.control), rep(palette[2], num.treat)) # number of cotr/treat samples -> need metadata

  ## draw heatmap

  pdf(file = file.path(out.path, paste('heatmapTop_', name.control, '_', name.treat, '.pdf', sep = '')), width = 15, height = 15, title = 'Heatmap using the top features')
  heatmap.2(as.matrix(norm.table.deg), col=brewer.pal(11,"RdBu"),scale="row", trace="none", ColSideColors = palette.group, margins = c(20,18), labRow = gene.norm.table, cexRow = 1.9, cexCol = 1.9)
  legend("topright", title = 'Group', legend=groups, text.font = 15,
         col = palette, fill = palette, cex=1.8)

  dev.off()
}

# function to load count tables 
countload <-function(input_path, samples){
    message(paste("loading gene counts from", input_path, "...", sep=" "))
    exprs.in <-list.files(path=input_path,pattern="count.tsv",full.names=TRUE,recursive=TRUE)
    exprs.in <- exprs.in[grep(paste(samples, collapse="|"),exprs.in)]
    counts.exprs <-lapply(exprs.in, read.csv, sep="\t", header=FALSE,row.names=1, check.names=FALSE)
    counts.exprs <-data.frame(lapply(counts.exprs, "[", 1))
    colnames(counts.exprs) <-basename(exprs.in)
    message("Done")
    counts.exprs
}

# function to plot PCA and sample distances
plot.pca <- function(name.control, name.treat) {
  splan.2G <- splan[splan$group %in% c(name.control, name.treat), ]
  samples <- row.names(splan.2G)
  d <- countload(counts.path,samples)
  message("size of the table")
  message("number of genes")
  message(dim(d)[1])
  message("number of samples")
  message(dim(d)[2])
  message("number of counts per sample")
  print(colSums(d))
  ## transform with DESeq
  dds <-DESeqDataSetFromMatrix(countData=d,DataFrame(condition=splan.2G$group),~condition)
  ## Estimate size factors
  dds <-estimateSizeFactors(dds)
  ## Remove lines with only zero
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
  pheatmap(sampleDistMatrix, clustering_distance_rows = sampleDists, clustering_distance_cols = sampleDists, color = colors, main="sample distance", filename=file.path(out.path, paste('SampleDistances_', name.control, '_', name.treat, '.pdf', sep = '')))

  ## PCA
  pdf(file = file.path(out.path, paste('PCA_', name.control, '_', name.treat, '.pdf', sep = '')), width = 15, height = 15, title = 'PCA')
    par(mfrow = c(2,1))
    # run PCA
    fig.pca <- DESeq2::plotPCA(rld, intgroup =c("condition"), ntop=1000)
    print(fig.pca)
    dev.off()
}

# the main function
for (ith.comparison in c(1:num.comparison)) {
  name.control <- controls[ith.comparison]
  name.treat <- treats[ith.comparison]
  plot.volcano.heatmap(name.control, name.treat)
  plot.pca(name.control, name.treat)
}
