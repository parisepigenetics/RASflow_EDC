
# load the libraries
library(edgeR)
library(DESeq2)
library(rtracklayer)
library(EnhancedVolcano)
library(Glimma)
library(regionReport)
library(gplots)
library(RColorBrewer)
library(pheatmap)
library(yaml)

# ====================== define the function of DEA ======================


DEA <- function(control, treat, dea.tool) {

  message("====================================================")
  message(paste("DEA:", treat, "vs", control))
  message("====================================================")

  # ----------------------------
  # 1. LOAD DATA
  # ----------------------------
  count.control <- read.table(
    file.path(counts_path, paste0(control, suffix)),
    header = TRUE,
    row.names = 1
  )

  count.treat <- read.table(
    file.path(counts_path, paste0(treat, suffix)),
    header = TRUE,
    row.names = 1
  )

  count.table <- cbind(count.control, count.treat)
  gene_ids <- sub("\\..*", "", rownames(count.table))

  # ----------------------------
  # 2. METADATA
  # ----------------------------
  subject <- factor(subject.all[c(
    which(group.all == control),
    which(group.all == treat)
  )])

  group <- factor(group.all[c(
    which(group.all == control),
    which(group.all == treat)
  )])

  group <- relevel(group, ref = control)

  # ----------------------------
  # 3. RUN DEA (EDGE R OR DESEQ2)
  # ----------------------------
  if (dea.tool == "edgeR") {

    y <- edgeR::DGEList(counts = count.table)

    if (filter.need) {
      keep <- rowSums(edgeR::cpm(y) > 1) > 1
      y <- y[keep, ]
    }

    y <- edgeR::calcNormFactors(y, method="TMM")
    normalized_counts <- cpm(y)  # counts-per-million (TMM normalized) 

    design <- if (pair.test) {
      model.matrix(~subject+group)
    } else {
      model.matrix(~group)
    }
    
    y$samples$subject <- subject
    y$samples$group <- group  
    rownames(design) <- colnames(y) 
      
    dds <- edgeR::estimateDisp(y, design, robust = TRUE)
    fit <- edgeR::glmFit(dds, design)
    lrt <- edgeR::glmLRT(fit)
      
    df <- as.data.frame(lrt$table)
    df$log2FoldChange <- df$logFC
    df$pvalue <- df$PValue
    df$padj <- p.adjust(df$PValue, method = "BH")

    plot_counts <- edgeR::cpm(
        y,
        log = TRUE,
        prior.count = 1
        )

  } else if (dea.tool == "DESeq2") {

    colData <- data.frame(
      row.names = colnames(count.table),
      subject = subject,
      group = group
    )
    
    design <- if (pair.test) {
      ~subject+group
    } else {
      ~group
    }

    dds <- DESeq2::DESeqDataSetFromMatrix(
      countData = count.table,
      colData = colData,
      design = design
    )
      
    if (filter.need) {
      keep <- rowSums(DESeq2::counts(dds)) >= 10
      dds <- dds[keep, ]
    }
    
    # generate normalized counts
    dds <- estimateSizeFactors(dds)
    normalized_counts <- counts(dds, normalized=TRUE)

    dds <- DESeq2::DESeq(dds)
    res <- DESeq2::results(dds, contrast = c("group", treat, control))
    df <- as.data.frame(res)
      
    ### For the sample dist and PCA 
    rld <- DESeq2::rlog(dds, blind = TRUE)  ## à remplacer par vst? 
    plot_counts <- SummarizedExperiment::assay(rld)
  }

  # ----------------------------
  # 4. STANDARDISE OUTPUT
  # ----------------------------
  
  df$gene_id <- gene_ids[match(rownames(df), rownames(count.table))]

  df$DE <- ifelse(
    !is.na(df$padj) & df$padj < 0.05 & df$log2FoldChange > 0, "up",
    ifelse(!is.na(df$padj) & df$padj < 0.05 & df$log2FoldChange < 0, "down", "ns")
  )

  results <- df

  # ----------------------------
  # 5. ANNOTATION (FROM GTF ONLY)
  # ----------------------------
  idx <- match(results$gene_id, annotations$gene_id_clean)
  results$gene_name <- annotations$gene_name[idx]
  results$gene_type <- annotations$gene_type[idx]
  results$chr <- annotations$chr[idx]
  results$start <- annotations$start[idx]
  results$end <- annotations$end[idx]
  results$strand <- annotations$strand[idx]

  results$GeneID <- ifelse(
    is.na(results$gene_name),
    results$gene_id,
    results$gene_name
  )

  # ----------------------------
  # 6. EXPORT TABLES
  # ----------------------------
  dir.create(file.path(output.path, "Tables"), showWarnings = FALSE, recursive = TRUE)

  write.table(
    results,
    file.path(output.path, "Tables", paste0("dea_",  treat, '_', control, ".tsv")),
    sep = "\t",
    quote = FALSE,
    row.names = FALSE
  )

  deg <- subset(results, DE != "ns")
  # sort according to pvalue then FC
  deg <- deg[order(deg$padj, -abs(deg$log2FoldChange)), ]

  write.table(
    deg,
    file.path(output.path, "Tables", paste0("deg_",  treat, '_', control, ".tsv")),
    sep = "\t",
    quote = FALSE,
    row.names = FALSE
  )
  # save the normalized count table   
  write.table(
    normalized_counts,
    file.path(output.path, "Tables", paste0(treat, '_', control, "_NormCounts.tsv")),
    sep = "\t",
    quote = FALSE,
    col.names = NA
  )
  message(glue::glue("DEA tables exported - {treat} vs {control}"))

    
    
  # ----------------------------
  # 7. Region Report
  # ----------------------------
    
  report.dir <- file.path(
  output.path,
  "Report",
  "regionReport",
  paste0(treat, "_", control)
  )
  dir.create(report.dir, recursive = TRUE, showWarnings = FALSE)  
  
  if (dea.tool == "edgeR") {

      tryCatch({

        regionReport::edgeReport(
          dds, 
          lrt, 
          "edgeR Report",
          intgroup = "group",
          outdir = report.dir,
          output = "exploration", 
        )

        message(glue::glue(
          "--------------- edgeR report exported : {treat} vs {control} ---------------"
        ))

      }, error = function(e) {

        message("edgeReport failed:")
        message(e$message)

      })

  } else if (dea.tool == "DESeq2") {

      tryCatch({

        regionReport::DESeq2Report(
          dds = dds,
          res = res,
          intgroup = "group",
          project = "DESeq2 Report",
          outdir = report.dir,
          output = "exploration"
        )

        message(glue::glue(
          "--------------- DESeq2 report exported : {treat} vs {control} ---------------"
        ))

      }, error = function(e) {

        message("DESeq2Report failed:")
        message(e$message)

      })
  }
  
    
  # ----------------------------
  # 8. BASIC OUTPUT OBJECT
  # ----------------------------
  return(list(
    tool = dea.tool,
    model = if (dea.tool == "edgeR") lrt else dds,
    results = results,
    deg = deg,
    normalized_counts = normalized_counts,
    plot_counts = plot_counts,
    dge = if (dea.tool == "edgeR") y else NULL,
    annotation = data.frame(
        GeneID = results$GeneID,
        row.names = rownames(df)),
    metadata = list(
        control = control,
        treat = treat,
        group = group,
        samples = colnames(count.table)
        )
    ))
}


# ====================== Glimma interactive plots ======================



run_glimma <- function(res, output.path) {

    tool <- res$tool
    model <- res$model
    group <- res$metadata$group
    samples <- res$metadata$samples
    control <- res$metadata$control
    treat <- res$metadata$treat
    annotation <- res$annotation
    normcounts <- res$normalized_counts

    html_base <- paste0(treat, "_", control)
    path <- file.path(
          output.path,
          "Report")
    
    dir.create(path, recursive = TRUE, showWarnings = FALSE)

    if (tool == "edgeR") {

        status <- ifelse(
            model$table$PValue < 0.05,
            sign(model$table$logFC),
            0
        )

        glMDSPlot(
            res$dge,
            groups = group,
            path = path,
            folder = "Glimma",
            html = paste0("MDSPlot_", html_base),
            launch = FALSE
        )
    }

    if (tool == "DESeq2") {

        status <- ifelse(
            !is.na(res$results$padj) &
            res$results$padj < 0.05,
            sign(res$results$log2FoldChange),
            0
        )


        glMDSPlot(
            model,
            groups = group,
            path = path,
            folder = "Glimma",
            html = paste0("MDSPlot_", html_base),
            launch = FALSE
        )
    }
    
    glMDPlot(
    model,
    status = status,
    counts = normcounts,
    groups = group,
    samples = samples,
    anno = annotation,
    path = path,
    folder = "Glimma",
    html = paste0("MDPlot_", html_base),
    launch = FALSE
    )
    
    
    glXYPlot(
    x = res$results$log2FoldChange,
    y = pmin(100, -log10(res$results$padj)),  # max 100 for visualisation
    xlab = "log2FC",
    ylab = "-log10(adj p-value)",   
    anno = annotation,
    status = status,
    counts = normcounts,
    groups = group,
    samples = samples,
    path = path,
    folder = "Glimma",
    html = paste0("Volcano_", html_base),
    side.main = "GeneID",
    cols = c("red", "grey", "blue"),
    sample.cols = c("darkgreen", "purple")[group],
    launch = FALSE
)
    
}


# ====================== Static plots ======================

run_plots <- function(res, output.path) {
    
    path <- file.path(output.path, "Report/plots")
    dir.create(path, recursive = TRUE, showWarnings = FALSE)
    ## Volcano plot  
    tool <- res$tool
    fig.volcano <- EnhancedVolcano(
        res$results,
        lab = res$results$GeneID, 
        x = "log2FoldChange",
        y = "padj", 
        xlab = bquote(~Log[2]~ "fold change"), 
        pCutoff = 0.05, 
        col = c("grey30", "orange2", "royalblue", "red2"),
        FCcutoff = 1, 
        title = paste(tool, "using", repeats.genes, "counts"), 
        subtitle = paste(treat, 'vs', control, sep = ' ')
        )
    pdf(file = file.path(output.path, paste('Report/plots/volcano_plot_', treat, '_', control, '.pdf', sep = '')), width = 9, height = 7)
    print(fig.volcano)
    dev.off() 
    
    ## Heatmap Top 30 genes
    groups <- res$metadata$group
    palette <- c("#000000ac", "#9d9d9dff")
    palette.group <- palette[as.numeric(groups == treat) + 1]
    
    
    top30 <- res$results[order(res$results$padj), ][1:30, ]
    
    norm <- res$normalized_counts[rownames(top30), , drop = FALSE]
    
    # labels
    lab <- top30$GeneID
    
    pdf(file.path(output.path, paste0("Report/plots/heatmapTop_", treat, '_', control, ".pdf")),
        width = 20, height = 20, title = 'Heatmap using the top features')
    
    heatmap.2(
        as.matrix(norm),
        col = rev(brewer.pal(11, "RdBu")),
        scale = "row",
        trace = "none",
        ColSideColors = palette.group,
        margins = c(30, 18),
        labRow = lab,
        cexCol = 2.5,
        cexRow = 2.5,
        dendrogram = "column",
        yaxt = "n", 
        key.par = list(cex=1.2, cex.lab=1), 
        keysize=1
    )
    
    legend(
        "topright",
        legend = unique(groups),
        fill = unique(palette.group), 
        title = 'Group', 
        text.font = 15,
        col = palette, 
        cex=1.8
    )
    dev.off()

    ## sample distance heatmap
    mat <- res$plot_counts

    sampleDists <- dist(t(mat))
    dist_matrix <- as.matrix(sampleDists)
    
    colnames(dist_matrix) <- colnames(mat)
    rownames(dist_matrix) <- paste(colnames(mat), groups, sep=":")
    
    colors <- colorRampPalette(rev(brewer.pal(9, "Blues")))(255)
    
    title <- paste("Sample distances using", repeats.genes, "counts")
    
    pdf(file.path(output.path, paste0("Report/plots/SampleDistances_",  treat, '_', control, ".pdf")))
    
    pheatmap(
        dist_matrix,
        clustering_distance_rows = sampleDists,
        clustering_distance_cols = sampleDists,
        color = colors,
        main = title
    )
    dev.off()

    ## PCA
    
    pca <- prcomp(
      t(res$plot_counts),
      scale. = FALSE
    )
    
    percentVar <- pca$sdev^2 / sum(pca$sdev^2)
    
    pca_df <- data.frame(
      sample = rownames(pca$x),
      PC1 = pca$x[, 1],
      PC2 = pca$x[, 2],
      group = res$metadata$group
    )
    
    pca_plot <- ggplot2::ggplot(
      pca_df,
      ggplot2::aes(x = PC1, y = PC2, color = group)
    ) +
      ggplot2::geom_point(size = 3) +
      ggplot2::labs(
        title = paste("PCA using", repeats.genes, "counts"),
        x = paste0("PC1: ", round(percentVar[1] * 100), "% variance"),
        y = paste0("PC2: ", round(percentVar[2] * 100), "% variance")
      ) +
      ggplot2::coord_fixed()
    
    ggplot2::ggsave(
      file.path(
        output.path,
        "Report",
        "plots",
        paste0("PCA_",  treat, '_', control, ".pdf")
      ),
      pca_plot,
      width = 8,
      height = 8
    )
            
    }


    
# ====================== Main ======================



# load the config file
yaml.file <- yaml.load_file('config_ongoing_run.yaml')

# extract the information from the yaml file
project <- yaml.file$PROJECT  # project name of this analysis
dea.tool <- yaml.file$DEATOOL  # tool used for DEA
controls <- yaml.file$CONTROL  # all groups used as control
treats <- yaml.file$TREAT  # all groups used as treat, should be as long as ctrl list
filter.need <- as.logical(yaml.file$FILTER)
pair.test <- yaml.file$PAIR
meta.file <- yaml.file$METAFILE
gtf_file <- yaml.file$ANNOTATION


# passing the params from command line
args <- commandArgs(TRUE)
counts_path <- args[1]
output.path <- args[2]
suffix <- args[3]

# for proper figure labeling
repeats.genes <- if (suffix == "_countsTE.tsv") {
  "repeat"
} else if (suffix == "_countsGenes.tsv") {
  "gene"
} else {
  stop("Unknown suffix: ", suffix)
}

# extract the metadata
meta.data <- read.csv(meta.file, header = TRUE, sep = '\t')
group.all <- meta.data$group
subject.all <- meta.data$subject

# load the GTF 
gtf <- rtracklayer::import(gtf_file)
genes <- gtf[gtf$type == "gene"]
annotations <- data.frame(
    gene_id = genes$gene_id,
    gene_name = genes$gene_name,
    gene_type = genes$gene_type,
    chr = as.character(seqnames(genes)),
    start = start(genes),
    end = end(genes),
    strand = as.character(strand(genes))
)
annotations$gene_id_clean <- sub(
    "\\..*",
    "",
    annotations$gene_id
)


## Run all the comparisons

num.control <- length(controls)  # number of comparisons that the user wants to do
num.treat <- length(treats)  # should equals to num.control

if (num.control != num.treat) {
  message("Error: Control groups don't match with treat groups!")
  message("Please check your configuration file.")
  quit(save = 'no')
}

num.comparison <- num.control

# Do DEA

# the main function
for (ith.comparison in c(1:num.comparison)) {
  control <- controls[ith.comparison]
  treat <- treats[ith.comparison]
  dea <- DEA(control, treat, dea.tool)
  run_plots(dea, output.path) 
  run_glimma(dea, output.path)
}
