import yaml
import time
import sys
import os

def main(time_string):
    with open('configs/config_main.yaml') as yamlfile:
        config = yaml.load(yamlfile,Loader=yaml.BaseLoader)
    server = "IFB"
    project = config["PROJECT"]
    trim = config["TRIMMED"]
    mapping = config["MAPPING"]
    reference = config["REFERENCE"]
    dea = config["DEA"]
    aligner = config["ALIGNER"]
    counter = config["COUNTER"]
    control = config["CONTROL"]
    treat = config["TREAT"]
    deatool = config["DEATOOL"]
    resultpath = config["RESULTPATH"]

    start_time = time.localtime()
    date_string = time.strftime("%d/%m/%Y", start_time)


    f = open(resultpath+'/'+project+'/report.html','w')


    message = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <title> RNAseq report </title>
    <style>
    h1 {
    font-size: 2.5em;
    color: #385e72;
    text-align:center;
    }

    h2 {
    font-size: 1.4em;
    color: #6aabd2;
    background-color: white;
    margin-right: 50px;
    margin-left: 50px;
    padding: 5px 30px;
    }

    h3 {
    font-size: 1.2em;
    color: #b7cfdc;
    background-color: #385e72;
    margin-right: 50px;
    margin-left: 50px;
    padding: 5px 30px;
    }

    p {
    font-size: 1.2em;
    margin-right: 50px;
    margin-left: 50px;
    padding: 5px 30px;
    }
    </style>
    </head>
    <body style="background-color:#d9e4ec;font-family:verdana;">
    <p><br></p>
    <h1 >RNA-seq analysis report</h1>
    <p style="text-align:center;">This report was generated on %s by BIBS-EDC RASflow implementation on %s cluster.<br><br></p>
    <h2 id="project-name-projectname">  Project %s</h2>
    <p><br></p>
    <h2 id="project-settings">  Analysis settings</h2>
    <p>The settings used for the analysis can be found in the <a href="logs/%s_configuration.txt">logs/%s_configuration.txt</a>.<br></p>
    """% (date_string, server,project,time_string,time_string)
    f.write(message)


    if os.path.isfile("fastqc/report_quality_control.html"):
        message="""
    <h2 id="fastq-quality-control">Fastq quality control</h2>
    <p>A summary of the quality of the raw sequences can be found in <a href="fastqc/report_quality_control.html">fastqc/report_quality_control.html</a>. <br></p>
    """
    else : 
        message="""
    <h2 id="fastq-quality-control">Fastq quality control</h2>
    <p> QC report could not be found. Have you run QC before the rest of the analysis? If not, all the results might be impaired by low quality FASTQ reads. Running QC on raw sequences is highly recommended!<br></p>
    """
    f.write(message)

    if trim=='yes' : 
        message="""
    <h2 id="trimming">Trimming</h2>
    <p> Raw sequences were trimmed. A summary of the quality of the trimmed sequences can be found in 
    <a href="fastqc_after_trimming/report_quality_control_after_trimming.html">report_quality_control_after_trimming.html</a>. <br></p>
    """
    else :
        message="""
    <h2 id="trimming">Trimming</h2>
    <p> The sequences were not trimmed and raw sequences were used for subsequent mapping. <br></p>
    """
    f.write(message)

    if mapping =='yes' and reference == "genome":
        message="""
    <h2 id="mapping-and-counting">Mapping and counting</h2>
    <p> The mapping was done using %s. </p>
    <p>Mapping quality is assessed in <a href="mapping_%s/report_align_count_%s.html">mapping_%s/report_align_count_%s.html</a>. </p>
    <p>This report also contains an overview of feature counting that was perfomed by %s. </p>
    <p>Raw count tables are available in <a href="mapping_%s/counting_%s/countTables/">mapping_%s/counting_%s/countTables/</a>.<br></p>
    <h2 id="exploratory-analysis-of-all-the-samples">Exploratory analysis of all the samples</h2>
    <p>To assess the quality of the experiment and the reproducibility of the replicates, an 
    <a href="mapping_%s/counting_%s/PCA.pdf">analysis in principal components</a> 
    for all the samples is available, 
    as well as a <a href="mapping_%s/counting_%s/heatmap.pdf">heatmap with clustering</a>.  </p>
    <p><embed src= "mapping_%s/counting_%s/PCA.pdf" type="application/pdf" width= "700" height= "700">
    <embed src= "mapping_%s/counting_%s/heatmap.pdf" type="application/pdf" width= "700" height= "700"><br></p>
    """ %(aligner,aligner, counter, aligner, counter,counter,\
        aligner,counter,aligner,counter,aligner,counter,aligner, counter,aligner, counter,aligner, counter)
        f.write(message)

    if dea=='yes':
        L = len(control)
        if L>1 : 
            message="""
            <h2 id="pairwise-differential-expression-analyses">Pairwise differential expression analyses</h2>
            <p>You have made """+str(L)+""" pairwise comparisons. Please see below the results for each comparison.</p>
            """
        else:
            message="""
            <h2 id="pairwise-differential-expression-analyses">Pairwise differential expression analyses</h2>
            <p>You have made one pairwise comparison. Please see below the results for this comparison.</p>
            """

        f.write(message)

        for compa in zip(control,treat):
            print("Exporting comparison "+str(compa)+"...")
            controlGroup = compa[0]
            treatGroup = compa[1]
            message="""
        <p><br></p>
        <h3 id="Comparison-between-%s-and-%s">Comparison between %s and %s</h3>
        <p>The <a href="mapping_%s/counting_%s/DEA_%s/Report/regionReport/%s_%s/DESeq2Exploration.html">regionReport exploratory report</a> 
        is a good start to get an idea of the results.</p> 
        <p>To be easily shared and reused the <a href="mapping_%s/counting_%s/DEA_%s/Report/plots/PCA_%s_%s.pdf">PCA</a> 
        and the 
        <a href="mapping_%s/counting_%s/DEA_%s/Report/plots/SampleDistances_%s_%s.pdf">heatmap with clustering </a>
        are also available as PDF files.  </p> 
        <p>
        <embed src= "mapping_%s/counting_%s/DEA_%s/Report/plots/PCA_%s_%s.pdf" type="application/pdf" width= "700" height= "700">
        <embed src= "mapping_%s/counting_%s/DEA_%s/Report/plots/SampleDistances_%s_%s.pdf" width= "700" height= "700">
        </p>
        <p>Glimma interactive <a href="mapping_%s/counting_%s/DEA_%s/Report/Glimma/MDSPlot_%s_%s.html">MDS plot</a> 
        can help you to identify problematic samples.</p>
        <p> <embed type="text/html" src="mapping_%s/counting_%s/DEA_%s/Report/Glimma/MDSPlot_%s_%s.html" width="1000" height="900"> </p>
        <p>DEA result tables (all genes or significantly differentially expressed genes) are stored in 
        <a href="mapping_%s/counting_%s/DEA_%s/Tables">mapping_%s/counting_%s/DEA_%s/Tables</a>.</p>
        <p>Importantly, the results can be deeply explored thanks to <b>interactive</b>
        <a href="mapping_%s/counting_%s/DEA_%s/Report/Glimma/MDPlot_%s_%s.html">MD</a>
        and 
        <a href="mapping_%s/counting_%s/DEA_%s/Report/Glimma/Volcano_%s_%s.html">Volcano</a> 
        plots.</p>
        <p> <embed type="text/html" src="mapping_%s/counting_%s/DEA_%s/Report/Glimma/Volcano_%s_%s.html" width="1050" height="1000"> </p>
        <p>A static <a href="mapping_%s/counting_%s/DEA_%s/Report/plots/volcano_plot_%s_%s.pdf">Volcano plot</a> 
        is also available, as well as a 
        <a href="mapping_%s/counting_%s/DEA_%s/Report/plots/heatmapTop_%s_%s.pdf">heatmap of the 20 top-regulated genes</a>. </p>
        <p>
        <embed src= "mapping_%s/counting_%s/DEA_%s/Report/plots/volcano_plot_%s_%s.pdf" type="application/pdf" width= "700" height= "700">
        <embed src= "mapping_%s/counting_%s/DEA_%s/Report/plots/heatmapTop_%s_%s.pdf" width= "700" height= "700">
        </p>
            """ % (controlGroup, treatGroup,controlGroup, treatGroup,\
                aligner, counter, deatool,controlGroup,treatGroup,\
                aligner, counter, deatool,controlGroup,treatGroup,aligner, counter, deatool,controlGroup,treatGroup,\
                aligner, counter, deatool,controlGroup,treatGroup,\
                aligner, counter, deatool,controlGroup,treatGroup,aligner, counter, deatool,controlGroup,treatGroup,\
                aligner, counter, deatool,controlGroup,treatGroup,\
                aligner, counter, deatool, aligner, counter, deatool,\
                aligner, counter, deatool,controlGroup,treatGroup,\
                aligner, counter, deatool,controlGroup,treatGroup,aligner, counter, deatool,controlGroup,treatGroup,\
                aligner, counter, deatool,controlGroup,treatGroup,aligner, counter, deatool,controlGroup,treatGroup,\
                aligner, counter, deatool,controlGroup,treatGroup,aligner, counter, deatool,controlGroup,treatGroup)

            f.write(message)

    message = """
    </body> 
    </html>
    """
    f.write(message)

    f.close()