# Use edgeR to do DEA on the outputs from Salmon

library(biomaRt)
library(yaml)
library(edgeR)
library(DESeq2)
library(tximport)
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

DEA <- function(control, treat, file.control, file.treat, output.path.dea) {
  count.control <- read.table(file.control, header = TRUE, row.names = 1, check.names = FALSE)
  count.treat <- read.table(file.treat, header = TRUE, row.names = 1, check.names = FALSE)
  count.table <- cbind(count.control, count.treat)  # merge the control and treat tables together
  
  # number of samples in control and treat groups (should be the same if it's a pair test)
  num.sample.control <- ncol(count.control)
  num.sample.treat <- ncol(count.treat)
  
  # save gene list in gene.list for extracting gene names later
  gene.list <- rownames(count.table)
  
  # get the sample id
  samples <- colnames(count.table)

  # define the group
  subject <- factor(subject.all[c(which(group.all == control), which(group.all == treat))])
  group <- factor(group.all[c(which(group.all == control), which(group.all == treat))])
  group <- relevel(group, ref = control)

  # The design matrix
  if (pair.test) {
    design <- model.matrix(~subject+group)
  } else {
    design <- model.matrix(~group)
  }
  
  ############### edgeR ##############
  if (dea.tool == 'edgeR') {  # use edgeR for DEA
    # Put the data into a DGEList object
    y <- DGEList(counts = count.table, genes = gene.list)
    
    # Filtering
    if (filter.need) {
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
    
    # conduct likelihood ratio tests for tumour vs normal tissue differences and show the top genes
    res.dea <- glmLRT(fit)
    
    #Report
    report <- edgeReport(dds, res.dea ,"edgeR Report",intgroup = "group", outdir = paste(output.path.dea,'Report/regionReport/', control, '_', treat, sep = ''), output = "exploration")
    message(paste("---------------","Report for DEA between", control, "and",  treat, "exported ---------------", sep=" "))

    
    # the DEA result for all the genes
  
    toptag <- topTags(res.dea, n = nrow(dds$genes), p.value = 1)
    dea <- toptag$table  # just to add one more column of FDR
    dea.sorted <- dea[order(dea$FDR, -abs(dea$logFC), decreasing = FALSE), ]  # sort the table: ascending of FDR then descending of absolute valued of logFC
    
    dea <- data.frame(res.dea$table) #unsorted table for Volcano plots
    dea$FDR <- p.adjust(dea$PValue,"BH")

    # differentially expressed genes
    toptag <- topTags(res.dea, n = nrow(dds$genes), p.value = 0.05)
    deg <- toptag$table
    if (!is.null(deg)) {
      deg <- deg[order(deg$FDR, -abs(deg$logFC), decreasing = FALSE), ]  # sort the table: ascending of FDR then descending of absolute valued of logFC
    }
    
    # to adjust the outputs to edgeR
    row.name = F # to write the tables
    
    # for Glimma
    dds <- as.DESeqDataSet(dds) # dds formated for Glimma
    
    res.dea$table$dt <- as.numeric(res.dea$table$PValue<0.05)
    res.dea$table$DE <- ifelse(res.dea$table$dt == 0,0, sign(res.dea$table$logFC))  
    DE <- res.dea$table$DE
      
    annotation <- data.frame(res.dea$table)  
    annotation$GeneID <- rownames(res.dea$table)
    
    # for glMDPlot
    status <- decideTestsDGE(res.dea)
    count.table.noNA <- normalized_counts 
    transform <- TRUE  
    
    # for glXYPlot (interactive volcano)
    LogFC <- res.dea$table$logFC 
    Pval <- -log10(res.dea$table$PValue)  
    xlab <- "LogFC" 
    ylab <- "-Log10(PValue)" 
    
    # for static volcano plots  
    x.volc <- 'logFC'
    y.volc <- 'FDR'
      
  }     
    ############### DESeq2 ##############
  else if (dea.tool == "DESeq2") {  # use DESeq2 for DEA

    ## prepare txi

    if (gene.level & gene.level.flag) {
      ### load tx2gene
      load(file.path(output.path, "countGroup", 'tx2gene.RData'))

      if (ENSEMBL) {
          files.noVersion <- file.path(quant.path, samples, "quant_noVersion.sf")
          names(files.noVersion) <- samples

          ### import quantification as txi
          txi <- tximport(files.noVersion, type = "salmon", tx2gene = tx2gene, countsFromAbundance = "no")
      } else {
          ### the original quant files from Salmon
          files <- file.path(quant.path, samples, "quant.sf")
          names(files) <- samples

          ### import quantification as txi
          txi <- tximport(files, type = "salmon", tx2gene = tx2gene, countsFromAbundance = "no")
      }
    } else {
      ### the original quant files from Salmon
      files <- file.path(quant.path, samples, "quant.sf")
      names(files) <- samples

      ### import quantification as txi
      txi <- tximport(files, type = "salmon", txOut = TRUE, countsFromAbundance = "no")
    }

    ## create the DESeqDataSet
    colData = data.frame(samples, subject, group)
    dds <- DESeqDataSetFromTximport(txi, colData = colData, design = design)
    
    # generate normalized counts
    dds <- estimateSizeFactors(dds)
    normalized_counts <- counts(dds, normalized=TRUE)

    # Filtering
    if (filter.need) {
      keep <- rowSums(counts(dds)) >= 10
      dds <- dds[keep,]
    }

    ## specify the control group
    dds$group <- relevel(dds$group, ref = control)
    
    ## perform DEA
    dds <- DESeq(dds)
    
    ## make a report
    gc()  # I added this command because I add an error "reached elapsed time limit" for some datasets
    report <- DESeq2Report(dds, "DESeq2-report", outdir = paste(output.path.dea,'Report/regionReport/', control, '_', treat, sep = ''),intgroup = c("group"),output = "exploration")
    message(paste("---------------","Report for DEA between ", control, "and",  treat, "exported ---------------", sep=" "))
    #message(paste("---------------","skipping Report for DEA between ", control, "and",  treat, " ---------------", sep=" "))
    
    
    ## export the results
    #contrast <- c("group",treat,control)
    #res.dea <- results(dds, contrast=contrast)
    res.dea <- results(dds)
    res.dea <- res.dea[complete.cases(res.dea), ]  # remove any rows with NA
    
    dea <- as.data.frame(res.dea)
    dea.sorted <- dea[order(dea$padj, -abs(dea$log2FoldChange), decreasing = FALSE), ]  # sort the table: ascending of FDR then descending of absolute valued of logFC
    
    deg <- dea[dea$padj < 0.05, ]
    if (nrow(deg) > 1) {
      deg <- deg[order(deg$padj, -abs(deg$log2FoldChange), decreasing = FALSE), ]  # sort the table: ascending of FDR then descending of absolute valued of logFC
    }    
    
    # to adjust the outputs to DESeq2
    row.name = T # to write the tables
    
    # for Glimma
    status <- as.numeric(res.dea$padj<0.05)
    DE <- ifelse(status == 0,0, sign(res.dea$log2FoldChange))
      
    annotation <- data.frame(res.dea)  
    annotation$GeneID <- rownames(res.dea)
    
    # for glMDPlot
    count.table.noNA <- normalized_counts[rownames(res.dea),]     
    transform <-FALSE  
    
    # for glXYPlot (interactive volcano)
    LogFC <- res.dea$log2FoldChange
    Pval <- -log10(res.dea$padj)
    xlab <- "Log2FC"
    ylab <- "-Log10(padj)" 
    
    # for static volcano plots  
    x.volc <- 'log2FoldChange'
    y.volc <- 'padj'
    
  }
  
  ######## common part ########
  
  # save the normalized count table  
  write.table(normalized_counts, paste(output.path.dea, 'Tables/', control, '_', treat, '_NormCounts.tsv', sep = ''), quote = FALSE, sep = "\t")   

    
  # save the DEA result and DEGs to files
  write.table(dea.sorted, paste(output.path.dea, 'Tables/dea_', control, '_', treat, '.tsv', sep = ''), row.names = row.name, quote = FALSE, sep = '\t')
  write.table(deg, paste(output.path.dea, 'Tables/deg_', control, '_', treat, '.tsv', sep = ''), row.names = row.name, quote = FALSE, sep = '\t')
  message(paste("---------------","Tables for DEA between", control, "and",  treat, "exported ---------------", sep=" "))
  
  ## Export Glimma interactive plots
      
  # MDS plots
  html <- paste('MDSPlot_', control, '_', treat, sep = '')
  glMDSPlot(dds, groups=group,path=paste(output.path.dea, "Report/", sep=""), folder="Glimma",html=html, launch=FALSE)
     
    # MD and volcano plots
    
  # in case there is no DEG or only Up or Down. 
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
  
  # get Symbols 
    
    annotation$GeneID <- sapply(strsplit(as.character(annotation$GeneID), "\\."),  "[", 1)
    
    if (gene.level.flag) {
       gene.id.dea <- annotation$GeneID
       gene.symbol.dea.all <- queryMany(gene.id.dea, scopes = 'ensembl.gene', fields = 'symbol')
       if (nrow(gene.symbol.dea.all) > 10) {
            h <- hash()
            for (i in 1:nrow(gene.symbol.dea.all)) {
                query <- gene.symbol.dea.all$query[i]
                symbol <- gene.symbol.dea.all$symbol[i]
                if (has.key(query, h)) {  # if there's duplicate for the same query
                    h[[query]] <- paste(hash::values(h, keys = query), symbol, sep = ', ')
                }
                else {
                    if (is.null(symbol) || is.na(symbol)) {  # if there's no hit for the query, keep the original id
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
        }
        else {
        message("queryMany gave no results, keeping previous IDs")
        }
    }
    
    else {
       simplify_names <- function(string) {
          if (startsWith(string, '(')){
             rep <-  unlist(strsplit(string,'\\('))[2]
          }
          else {
             rep <- string
          }
          rep <- unlist(strsplit(rep, ":"))[1]
          rep <- unlist(strsplit(rep, ")n"))[1]
        }
        annotation$GeneID <- sapply(annotation$GeneID, simplify_names)    
    }
    
    anno <- as.data.frame(cbind(annotation$GeneID, DE))      
    
    html <- paste('MDPlot_', control, '_', treat, sep = '')  
    glMDPlot(res.dea, status=status, counts=count.table.noNA, transform=transform, groups=group, samples=samples,anno=annotation, path=paste(output.path.dea, "Report/", sep=""), folder="Glimma",html=html, launch=FALSE) 
    
    sample.cols <- c("darkgreen", "purple")[group]
          
    html <- paste('Volcano_', control, '_', treat, sep = '')
    message()
    glXYPlot(x=LogFC, y=Pval, xlab=xlab, ylab=ylab,anno=annotation,path=paste(output.path.dea, "Report/", sep=""), folder="Glimma",html=html,status=anno$DE, cols=cols, side.main="GeneID",counts=count.table.noNA, groups=group, sample.cols=sample.cols, launch=FALSE)
    message(paste("---------------","Glimma interactive plots for DEA between", control, "and",  treat, "exported ---------------", sep=" "))

    # add PDFs of important figures
    # volcano
    fig.volcano <- EnhancedVolcano(dea, lab = annotation$GeneID, xlab = bquote(~Log[2]~ "fold change"), x = x.volc, y = y.volc, pCutoff = 0.05, col = c("grey30", "orange2", "royalblue", "red2"),
                                 FCcutoff = 1, title = dea.tool, subtitle = paste(control, 'vs', treat, sep = ' '))
    pdf(file = file.path(output.path.dea, paste('Report/plots/volcano_plot_', control, '_', treat, '.pdf', sep = '')), width = 9, height = 7)
    print(fig.volcano)
    dev.off()  
    message(paste("---------------","Volcano plot for DEA between", control, "and",  treat, "exported ---------------", sep=" "))
    
    # draw heatmap of the Top30 regulated genes
    groups <- c(control, treat)  
    splan.control <- meta.data[meta.data$group %in% c(control), ]
    splan.treat <- meta.data[meta.data$group %in% c(treat), ]
    num.control <- nrow(splan.control) 
    num.treat <- nrow(splan.treat)  

    # select the top 30 genes in dea.table
    id2 <- row.names(dea.sorted)
    normalized_counts_df <- as.data.frame(normalized_counts)
    normalized_counts_df$ID <- row.names(normalized_counts_df)  ## add an ID col to merge with index_df
    index_df <- as.data.frame(id2[1:30],ncol=1)
    colnames(index_df)=c('ID')
    index_df$keep.order  <- 1:nrow(index_df)  ## add extra col to keep the order of the genes (pvalue)
    norm.table.deg <- merge(index_df,normalized_counts_df,by = 'ID',all.x= TRUE)  ## merge the 2 dataframes
    norm.table.deg <- norm.table.deg[order(norm.table.deg$keep.order), ]  ## sort according to pvalue order
    norm.table.deg$keep.order <- NULL ## remove the ordering col
    rownames(norm.table.deg) <- norm.table.deg$ID  ## convert row names 
    norm.table.deg$ID <- NULL   ## remove ID col to have a numeric df
    gene.id.norm.table <- rownames(norm.table.deg)
    gene.id.norm.table <- sapply(strsplit(as.character(gene.id.norm.table), "\\."),  "[", 1)
    
    if (gene.level.flag) {
        gene.symbol.norm.table <- tryCatch(
            {   
                queryMany(gene.id.norm.table, scopes = 'ensembl.gene', fields = 'symbol')$symbol
            },
            error=function(cond) {
                message("queryMany gave no results, keeping previous IDs")
                # Choose a return value in case of error
                return(gene.id.norm.table)
            }
            )     
        # if can't find a symbol for the id, then keep the id as it is
        gene.norm.table <- gene.symbol.norm.table
        for (i in c(1:length(gene.norm.table))) {
          if (is.na(gene.norm.table[i])) {
            gene.norm.table[i] <- gene.id.norm.table[i]
          }
        }
    }
    else { # keep transcript ID
        gene.norm.table <- gene.id.norm.table
    }
        
    palette <- c("#000000ac", "#9d9d9dff")
    palette.group <- c(rep(palette[1], num.control), rep(palette[2], num.treat)) # number of cotr/treat samples -> need metadata

    pdf(file = file.path(output.path.dea, paste('Report/plots/heatmapTop_', control, '_', treat, '.pdf', sep = '')), width = 20, height = 20, title = 'Heatmap using the top features')
    par(oma=c(4,4,4,4))
    heatmap.2(as.matrix(norm.table.deg), col=rev(brewer.pal(11,"RdBu")),scale="row", trace="none", ColSideColors = palette.group, margins = c(30,18), 
            labRow = gene.norm.table, cexCol = 2.5, cexRow = 2.5, dendrogram="column",   #  size of the labels, clustering by cols
            yaxt="n", key.par = list(cex=1.2, cex.lab=1), keysize=1)  ## control the heatmap legend
    legend("topright", title = 'Group', legend=groups, text.font = 15,
         col = palette, fill = palette, cex=1.8)

    dev.off()
    message(paste("---------------","heatmap for Top30 genes for DEA between", control, "and",  treat, "exported ---------------", sep=" "))
      
    ## Sample distances
    ## Run the rlog normalization
    rld <-rlog(dds, blind=TRUE)
    
    ## Obtain the sample euclidean distances
    sampleDists <- dist(t(assay(rld)))
    sampleDistMatrix <- as.matrix(sampleDists)
    colnames(sampleDistMatrix) <- rownames(colData(rld))
    
    ## Add names including intgroup
    rownames(sampleDistMatrix) <- paste(rownames(colData(rld)), colData(rld)[, c("group")],sep=":") 
    colnames(sampleDistMatrix) <- rownames(colData(rld))
    colors <- colorRampPalette(rev(brewer.pal(9,"Blues")))(255)
    if (gene.level.flag) {
        title <- "Sample distances for genes"
        titlepca <- 'PCA using gene counts'
    } 
    else {
        title <- "Sample distances for trancripts"
        titlepca <- 'PCA using trancripts counts'
    } 
    pheatmap(sampleDistMatrix, clustering_distance_cols = sampleDists, clustering_distance_rows = sampleDists, color = colors, main=title, filename=file.path(output.path.dea, paste('Report/plots/SampleDistances_', control, '_', treat, '.pdf', sep = '')))        
    message(paste("---------------","Sample distances between", control, "and",  treat, "exported ---------------", sep=" "))

    ## PCA
    pdf(file = file.path(output.path.dea, paste('Report/plots/PCA_', control, '_', treat, '.pdf', sep = '')), width = 15, height = 15, title = 'PCA')
    par(mfrow = c(2,1))
    # run PCA
    pca = DESeq2::plotPCA(rld, intgroup=c("group"), returnData=TRUE, ntop=1000)
    pca_plot <- ggplot(data=pca, aes_string(x="PC1", y="PC2", color="group")) + geom_point(size=3) + 
    labs(title=titlepca, x =paste0("PC1: ",round(attr(pca, 'percentVar')[1] * 100),"% variance"), 
         y = paste0("PC2: ",round(attr(pca, 'percentVar')[2] * 100),"% variance")) + coord_fixed()
    print(pca_plot)
    dev.off()
    message(paste("---------------","PCA between", control, "and",  treat, "exported ---------------", sep=" "))
}
  

# ====================== load parameters in config file ======================

# load the config file
yaml.file <- yaml.load_file('config_ongoing_run.yaml')

# extract the information from the yaml file
project <- yaml.file$PROJECT  # project name
dea.tool <- yaml.file$DEATOOL  # tool used for DEA
quant.path <- file.path(yaml.file$RESULTPATH, project, "Salmon/quantification")
gene.level <- yaml.file$GENE_LEVEL  # whether to do gene-level analysis
controls <- yaml.file$CONTROL  # all groups used as control
treats <- yaml.file$TREAT  # all groups used as treat, should correspond to control
filter.need <- yaml.file$FILTER
pair.test <- yaml.file$PAIR
meta.file <- yaml.file$METAFILE
ENSEMBL <- yaml.file$ENSEMBL
dataset <- yaml.file$EnsemblDataSet

# passing the params from command line
args <- commandArgs(TRUE)
output.path <- args[1]

num.control <- length(controls)  # number of comparisons that the user wants to do
num.treat <- length(treats)  # should equals to num.control

if (num.control != num.treat) {
  message("Error: Control groups don't mathch with treat groups!")
  message("Please check config_dea.yaml")
  quit(save = 'no')
}

num.comparison <- num.control

# extract the metadata
meta.data <- read.csv(meta.file, header = TRUE, sep = '\t', stringsAsFactors = FALSE)
samples <- meta.data$sample
group.all <- meta.data$group
subject.all <- meta.data$subject

# ====================== Do DEA ======================

for (ith.comparison in c(1:num.comparison)) {
  control <- controls[ith.comparison]
  treat <- treats[ith.comparison]
  
  # --------------------- On transcript level ---------------------
  file.control <- paste(output.path, '/countGroup/', control, '_trans_abundance.tsv', sep = '')
  file.treat <- paste(output.path, '/countGroup/', treat, '_trans_abundance.tsv', sep = '')
  output.path.dea <- paste(output.path, '/DEA_transcript-level/', sep = '')
  
  gene.level.flag <- FALSE
  DEA(control, treat, file.control, file.treat, output.path.dea)
  
  # --------------------- On gene level ---------------------
  if (gene.level) {
    file.control <- paste(output.path, '/countGroup/', control, '_gene_abundance.tsv', sep = '')
    file.treat <- paste(output.path, '/countGroup/', treat, '_gene_abundance.tsv', sep = '')
    output.path.dea <- paste(output.path, '/DEA_gene-level/', sep = '')
  
    gene.level.flag <- TRUE
    DEA(control, treat, file.control, file.treat, output.path.dea)
  }
}

