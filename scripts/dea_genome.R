library(yaml)
library(edgeR)
library(DESeq2)
library(regionReport)
library(mygene)
library(Glimma)
library(limma)
library(hash)
library(EnhancedVolcano)
library(gplots)
library(RColorBrewer)
library(pheatmap)
library(DEFormats)

# ====================== define the function of DEA ======================

DEA <- function(control, treat) {
  message("###############################################################################################")
  message(paste("---------------","Comparing groups", control, "and",  treat, "---------------", sep=" "))  
  count.control <- read.table(paste(counts_path, control, '_counts.tsv', sep = ''), header = TRUE, row.names = 1)
  count.treat <- read.table(paste(counts_path, treat, '_counts.tsv', sep = ''), header = TRUE, row.names = 1)
  count.table <- cbind(count.control, count.treat)  # merge the control and treat tables together
  
  # number of samples in control and treat groups (should be the same if it's a pair test)
  num.sample <- ncol(count.table)
  num.sample.control <- ncol(count.control)
  num.sample.treat <- ncol(count.treat)

  # samples of two groups
  sample.control <- colnames(count.control)
  sample.treat <- colnames(count.treat)
  
  # save gene list in gene.list for extracting gene names later
  gene.list <- rownames(count.table)
  
  # get the sample id
  samples <- colnames(count.table)

  # define the group
  subject <- factor(subject.all[c(which(group.all == control), which(group.all == treat))])
  group <- factor(group.all[c(which(group.all == control), which(group.all == treat))])
  group <- relevel(group, ref = control)

  # depending  on the tool:   
 
  if (dea.tool == 'edgeR') {  # use edgeR for DEA
      
   # The design matrix
    if (pair.test) {
      design <- model.matrix(~subject+group)
    } else {
      design <- model.matrix(~group)
    }
      
    # Put the data into a DGEList object
    y <- DGEList(counts = count.table, genes = gene.list)
    
    # do DEA

    # Filtering
    if (filter.need==TRUE || filter.need=="yes") {
      countsPerMillion <- cpm(y)
      countCheck <- countsPerMillion > 1
      keep <- which(rowSums(countCheck) > 1)
      y <- y[keep, ]
    }
    
    # Normalization
    y <- calcNormFactors(y, method="TMM")
    
    normalized_counts <- cpm(y)  # counts-per-million (TMM normalized) 
      
    y$samples$subject <- subject
    y$samples$group <- group
    
    rownames(design) <- colnames(y)  
      
    # Estimating the dispersion
    
    # estimate the NB dispersion for the dataset
    dds <- estimateDisp(y, design, robust = TRUE)
    
    # Differential expression
    
    # determine differentially expressed genes
    # fit genewise glms
    fit <- glmFit(dds, design)
    
    # conduct likelihood ratio tests for treated vs control conditions and show the top genes
    res.dea <- glmLRT(fit)
    
    #Report
    report <- edgeReport(dds, res.dea ,"edgeR Report",intgroup = "group", outdir = paste(output.path,'Report/regionReport/', control, '_', treat, sep = ''))
    message(paste("---------------","Report for DEA between", control, "and",  treat, "exported ---------------", sep=" "))

    # the DEA result for all the genes

    toptag <- topTags(res.dea, n = nrow(dds$genes), p.value = 1)
    dea <- toptag$table  # just to add one more column of FDR
    dea <- dea[order(dea$FDR, -abs(dea$logFC), decreasing = FALSE), ]  # sort the table: ascending of FDR then descending of absolute valued of logFC

    # differentially expressed genes
    toptag <- topTags(res.dea, n = nrow(dds$genes), p.value = 0.05)
    deg <- toptag$table
    if (!is.null(deg)) {
      deg <- deg[order(deg$FDR, -abs(deg$logFC), decreasing = FALSE), ]  # sort the table: ascending of FDR then descending of absolute valued of logFC
    }
  
    row.name = F  
      
    dds <- as.DESeqDataSet(dds)  
    
    res.dea$table$dt <- as.numeric(res.dea$table$PValue<0.05)
    res.dea$table$DE <- ifelse(res.dea$table$dt == 0,0, sign(res.dea$table$logFC))  
      
    annotation <- data.frame(res.dea$table)  
    annotation$GeneID <- rownames(res.dea$table)
    
      
    DE <- res.dea$table$DE
      ## in case there is no DEG or only Up or Down. 
    if (nlevels(as.factor(DE)) == 3) {
       DE <- c("downregulated", "notDE", "upregulated")[as.factor(DE)]
       cols <- c("blue","red", "grey")
    }
    if (nlevels(as.factor(DE)) == 1) {
       DE <- c("notDE")[as.factor(DE)]
       cols <- c("grey")
    }
    if (nlevels(as.factor(DE)) == 2 && -1 %in% levels(as.factor(DE))) {
       DE <- c("downregulated","notDE")[as.factor(DE)]
       cols <- c("red", "grey")
    }
    if (nlevels(as.factor(DE)) == 2 && 1 %in% levels(as.factor(DE))) {
       DE <- c("notDE", "upregulated")[as.factor(DE)]
       cols <- c("blue", "grey")
    }   
      
    status <- decideTestsDGE(res.dea)
      
    LogFC <- res.dea$table$logFC  
    Pval <- -log10(res.dea$table$PValue)     
    xlab <- "LogFC"
    ylab <- "-Log10(PValue)"
    
    # for volcano plots  
    x.volc <- 'logFC'
    y.volc <- 'FDR'
      
    count.table.noNA <- normalized_counts
    transform <- TRUE

  } 
    
  else if (dea.tool == "DESeq2") {  # use DESeq2 for DEA
      
    # The design matrix
    if (pair.test) {
      design <- ~subject+group
    } else {
      design <- ~group
    }

    ## create the DESeqDataSet
    colData = data.frame(samples, subject, group)
    dds <- DESeqDataSetFromMatrix(count.table, colData = colData, design = design)

    # generate normalized counts
    dds <- estimateSizeFactors(dds)
    normalized_counts <- counts(dds, normalized=TRUE)
      
    write.table(normalized_counts, paste(output.path, 'Tables/', control, '_', treat, '_NormCounts.tsv', sep = ''), quote = FALSE, sep = "\t")

    ## Filtering
    if (filter.need==TRUE || filter.need=="yes") {
      keep <- rowSums(counts(dds)) >= 10
      dds <- dds[keep,]
    }
    
    ## perform DEA
    dds <- DESeq(dds)
      
    ## export dds as Rds:
    ## saveRDS(object = dds, file = paste(output.path, '/DEA_DESeq2/dds_', control, '_', treat, '.rds', sep = ''))      

    ## make a report
    gc()  # I added this command because I add an error "reached elapsed time limit" for some datasets
    report <- DESeq2Report(dds, "DESeq2-report", outdir = paste(output.path,'Report/regionReport/', control, '_', treat, sep = ''),intgroup = c("group"))
    message(paste("---------------","Report for DEA between ", control, "and",  treat, "exported ---------------", sep=" "))
    #message(paste("---------------","skipping Report for DEA between ", control, "and",  treat, " ---------------", sep=" "))

    ## export the results
    contrast <- c("group",treat,control)
    res.dea <- results(dds, contrast=contrast)
    res.dea <- res.dea[complete.cases(res.dea), ]  # remove any rows with NA

    dea <- as.data.frame(res.dea)
    dea <- dea[order(dea$padj, -abs(dea$log2FoldChange), decreasing = FALSE), ]  # sort the table: ascending of padj then descending of absolute valued of logFC
    
    deg <- dea[dea$padj < 0.05, ]
    if (nrow(deg) > 1) {
      deg <- deg[order(deg$padj, -abs(deg$log2FoldChange), decreasing = FALSE), ]  # sort the table: ascending of padj then descending of absolute valued of logFC
    }
    
    row.name = T
      
    annotation <- data.frame(res.dea)  
    annotation$GeneID <- rownames(res.dea)
    
    status <- as.numeric(res.dea$padj<0.05)
      
    DE <- ifelse(status == 0,0, sign(res.dea$log2FoldChange))  
    if (nlevels(as.factor(DE)) == 3) {
       DE <- c("downregulated", "notDE", "upregulated")[as.factor(DE)]
       cols <- c("blue","red", "grey")
    }
    if (nlevels(as.factor(DE)) == 1) {
       DE <- c("notDE")[as.factor(DE)]
       cols <- c("grey")
    }
    if (nlevels(as.factor(DE)) == 2 && -1 %in% levels(as.factor(DE))) {
       DE <- c("downregulated","notDE")[as.factor(DE)]
       cols <- c("red", "grey")
    }
    if (nlevels(as.factor(DE)) == 2 && 1 %in% levels(as.factor(DE))) {
       DE <- c("notDE", "upregulated")[as.factor(DE)]
       cols <- c("blue", "grey")
    }  
      
    LogFC <- res.dea$log2FoldChange
    Pval <- -log10(res.dea$padj)
    xlab <- "Log2FC"
    ylab <- "-Log10(padj)"
    
    # for volcano plots  
    x.volc <- 'log2FoldChange'
    y.volc <- 'padj'
      
    # for MD plots  
    count.table.noNA <- normalized_counts[rownames(res.dea),]     
    transform <-FALSE
      
  }            
      
## common part: 
    
    # save the normalized count table  
    write.table(normalized_counts, paste(output.path, 'Tables/', control, '_', treat, '_NormCounts.tsv', sep = ''), quote = FALSE, sep = "\t")   
    
    # save the DEA result and DEGs to files
    write.table(dea, paste(output.path, 'Tables/dea_', control, '_', treat, '.tsv', sep = ''), row.names = row.name, quote = FALSE, sep = '\t')
    write.table(deg, paste(output.path, 'Tables/deg_', control, '_', treat, '.tsv', sep = ''), row.names = row.name, quote = FALSE, sep = '\t') 
    message(paste("---------------","Tables for DEA between", control, "and",  treat, "exported ---------------", sep=" "))
      
    ## Export Glimma interactive plots
      
    # MDS plots
    html <- paste('MDSPlot_', control, '_', treat, sep = '')
    glMDSPlot(dds, groups=group,path=paste(output.path, "Report/", sep=""), folder="Glimma",html=html, launch=FALSE)
     
    # MD and volcano plots
    # get Symbols 
    
    annotation$GeneID <- sapply(strsplit(as.character(annotation$GeneID), "\\."),  "[", 1)
    gene.id.dea <- annotation$GeneID
    gene.symbol.dea.all <- queryMany(gene.id.dea, scopes = 'ensembl.gene', fields = 'symbol')
    h <- hash()
    for (i in 1:nrow(gene.symbol.dea.all)) {
      query <- gene.symbol.dea.all$query[i]
      symbol <- gene.symbol.dea.all$symbol[i]
      if (has.key(query, h)) {  # if there's duplicate for the same query
        h[[query]] <- paste(hash::values(h, keys = query), symbol, sep = ', ')
      }
      else {
        if (is.na(symbol)) {  # if there's no hit for the query, keep the original id
          h[[query]] <- query
        } 
        else {
          h[[query]] <- symbol
        }
      }
    }
    gene.dea <- gene.id.dea
    for (i in c(1:length(gene.dea))) {
       gene.dea[i] <- h[[gene.id.dea[i]]]
    }
    annotation$GeneID <- gene.dea
    anno <- as.data.frame(cbind(annotation$GeneID, DE))      
    
    html <- paste('MDPlot_', control, '_', treat, sep = '')  
    glMDPlot(res.dea, status=status, counts=count.table.noNA, transform=transform, groups=group, samples=samples,anno=annotation, path=paste(output.path, "Report/", sep=""), folder="Glimma",html=html, launch=FALSE) 
    
    sample.cols <- c("darkgreen", "purple")[group]
    
      
    html <- paste('Volcano_', control, '_', treat, sep = '')
    message()
    glXYPlot(x=LogFC, y=Pval, xlab=xlab, ylab=ylab,anno=annotation,path=paste(output.path, "Report/", sep=""), folder="Glimma",html=html,status=anno$DE, cols=cols, side.main="GeneID",counts=count.table.noNA, groups=group, sample.cols=sample.cols, launch=FALSE)
    message(paste("---------------","Glimma interactive plots for DEA between", control, "and",  treat, "exported ---------------", sep=" "))

    # add PDFs of important figures
    # volcano
    fig.volcano <- EnhancedVolcano(dea, lab = gene.dea, xlab = bquote(~Log[2]~ "fold change"), x = x.volc, y = y.volc, pCutoff = 10e-5, col = c("grey30", "orange2", "royalblue", "red2"),
                                 FCcutoff = 1, title = dea.tool, subtitle = paste(control, 'vs', treat, sep = ' '))
    pdf(file = file.path(output.path, paste('Report/plots/volcano_plot_', control, '_', treat, '.pdf', sep = '')), width = 9, height = 7)
    print(fig.volcano)
    dev.off()  
    message(paste("---------------","Volcano plot for DEA between", control, "and",  treat, "exported ---------------", sep=" "))
    
    # draw heatmap of the Top20 regulated genes
    groups <- c(control, treat)  
    splan.control <- meta.data[meta.data$group %in% c(control), ]
    splan.treat <- meta.data[meta.data$group %in% c(treat), ]
    num.control <- nrow(splan.control) 
    num.treat <- nrow(splan.treat)  

    # instead using all genes, only use the top 20 genes in dea.table
    id2 <- row.names(dea)
    index.deg <- which(row.names(normalized_counts) %in% id2[1:20])
    norm.table.deg <- normalized_counts[index.deg,]

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

    pdf(file = file.path(output.path, paste('Report/plots/heatmapTop_', control, '_', treat, '.pdf', sep = '')), width = 15, height = 15, title = 'Heatmap using the top features')
    heatmap.2(as.matrix(norm.table.deg), col=brewer.pal(11,"RdBu"),scale="row", trace="none", ColSideColors = palette.group, margins = c(20,18), labRow = gene.norm.table, cexRow = 1.9, cexCol = 1.9)
    legend("topright", title = 'Group', legend=groups, text.font = 15,
         col = palette, fill = palette, cex=1.8)

    dev.off()
    message(paste("---------------","heatmap for Top20 genes for DEA between", control, "and",  treat, "exported ---------------", sep=" "))
      
    ## Sample distances
    ## Run the rlog normalization
    rld <-rlog(dds, blind=TRUE)
    ## Obtain the sample euclidean distances
    sampleDists <- dist(t(assay(rld)))
    sampleDistMatrix <- as.matrix(sampleDists)
    ## Add names based on intgroup
    rownames(sampleDistMatrix) <- apply(as.data.frame(colData(rld)[, c("group")]), 1,paste, collapse = ' : ')
    colnames(sampleDistMatrix) <- NULL
    colors <- colorRampPalette(rev(brewer.pal(9,"Blues")))(255)
    pheatmap(sampleDistMatrix, clustering_distance_rows = sampleDists, clustering_distance_cols = sampleDists, color = colors, main="sample distance", filename=file.path(output.path, paste('Report/plots/SampleDistances_', control, '_', treat, '.pdf', sep = '')))
    message(paste("---------------","Sample distances between", control, "and",  treat, "exported ---------------", sep=" "))

    ## PCA
    pdf(file = file.path(output.path, paste('Report/plots/PCA_', control, '_', treat, '.pdf', sep = '')), width = 15, height = 15, title = 'PCA')
    par(mfrow = c(2,1))
    # run PCA
    fig.pca <- DESeq2::plotPCA(rld, intgroup =c("group"), ntop=1000)
    print(fig.pca)
    dev.off()
    message(paste("---------------","PCA between", control, "and",  treat, "exported ---------------", sep=" "))
  
}      
  

# load the config file
yaml.file <- yaml.load_file('configs/config_main.yaml')

# extract the information from the yaml file
project <- yaml.file$PROJECT  # project name of this analysis
dea.tool <- yaml.file$DEATOOL  # tool used for DEA
controls <- yaml.file$CONTROL  # all groups used as control
treats <- yaml.file$TREAT  # all groups used as treat, should correspond to control
filter.need <- yaml.file$FILTER
pair.test <- yaml.file$PAIR
meta.file <- yaml.file$METAFILE
counter <- yaml.file$COUNTER
mapper <- yaml.file$ALIGNER

# passing the params from command line
args <- commandArgs(TRUE)
counts_path <- args[1]
output.path <- args[2]

# extract the metadata
meta.data <- read.csv(meta.file, header = TRUE, sep = '\t')
group.all <- meta.data$group
subject.all <- meta.data$subject

num.control <- length(controls)  # number of comparisons that the user wants to do
num.treat <- length(treats)  # should equals to num.control

if (num.control != num.treat) {
  message("Error: Control groups don't match with treat groups!")
  message("Please check config_dea.yaml")
  quit(save = 'no')
}

num.comparison <- num.control

# Do DEA

# the main function
for (ith.comparison in c(1:num.comparison)) {
  control <- controls[ith.comparison]
  treat <- treats[ith.comparison]
  DEA(control, treat)
}

