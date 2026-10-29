import yaml
import time
import sys
import os
import tarfile

def main(time_string, server):
    with open('config_ongoing_run.yaml') as yamlfile:
        config = yaml.load(yamlfile,Loader=yaml.BaseLoader)
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
    repeats = config["REPEATS"]
    fromcounts = config["FROMCOUNTS"]
    seq_type = {"single":"Single-end", "pair":"Paired-end"}
    if (fromcounts != "no" and fromcounts != False) or reference == "transcriptome":
        repeats = "no"  # repeat analysis is disable when starting from homemade count tables or doing transcriptome analysis. 
    qc = config["QC"]
    sra = config["SRA"]
    if sra == "yes" or sra == True: 
        qc = "yes"
    if qc == "yes" or qc == True: # deactivate the rest
        trim = "disabled"
        mapping = "disabled"
        dea = "disabled"
        repeats = "disabled"
        fromcounts = "no"
    
    # Define the folders and files that you want in the tar.bz2.
    ToKeep = ["logs"]	
    ExtraFiles= ["report_quality_control.html","SRA.log"]
    
    # "report_align_count_"+counter+"_data" ?
    # "report_quality_control_data" ?
    
    if trim=='yes' :
        ExtraFiles = ExtraFiles + ["report_quality_control_after_trimming.html"]
        
    if mapping == 'yes': 
        ExtraFiles = ExtraFiles + ["report_quality_control_after_trimming.html","report_align_count_"+counter+".html", "Heatmap_samples.pdf", "PCA.pdf", "report_quantify.html", "Heatmap_samples_TE.pdf","PCA_TE.pdf"]
        ToKeep = ToKeep + ["Glimma"]
        
    if repeats == 'yes':
        ExtraFiles= ExtraFiles + ["Heatmap_samples_TE.pdf","PCA_TE.pdf"]
    
    if dea == 'yes': 
        ToKeep = ToKeep + ["Glimma", "plots","regionReport"]
    
    if fromcounts != "no" and fromcounts != False:
        ExtraFiles= ExtraFiles + ["Heatmap_samples.pdf", "PCA.pdf"]
        
            ############# Tar.bz2 file ############
    dirName = resultpath+'/'+project
    Tar = tarfile.open(dirName+'/'+time_string+'_report.tar.bz2', 'w:bz2')
    
    
    ToKeepSub = []
    for folderName, subfolders, filenames in os.walk(dirName):
        if os.path.basename(folderName) in ToKeep:
            ToKeepSub += subfolders	
            for filename in filenames:	
                #create complete filepath of file in directory
                filePath = os.path.join(folderName, filename)
                relativePath = filePath.replace(dirName, '')
                # Add file to tar	
                Tar.add(filePath, relativePath)	
        else:	
            for filename in filenames: 	
                if filename in ExtraFiles:	
                    filePath = os.path.join(folderName, filename)	
                    relativePath = filePath.replace(dirName, '')
                    # Add file to zip	
                    Tar.add(filePath, relativePath)	
                    	
    for folderName, subfolders, filenames in os.walk(dirName):	
        if os.path.basename(folderName) in ToKeepSub:
            for filename in filenames:	
                #create complete filepath of file in directory	
                filePath = os.path.join(folderName, filename)	
                relativePath = filePath.replace(dirName, '')	
                # Add file to tar	
                Tar.add(filePath, relativePath)	


    start_time = time.localtime()
    date_string = time.strftime("%d/%m/%Y", start_time)

    f = open(resultpath+'/'+project+'/'+time_string+'_report.html','w')


    message = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <title> RNAseq report </title>
    <style>
    
    
    body {{
        margin: 0;
        background-color: #f4f7fa;
        font-family: Verdana, sans-serif;
        color: #263746;
        line-height: 1.6;
    }}

    /* sidebar */
    #sidebar {{
        position: fixed;
        top: 0;
        left: 0;
        width: 250px;
        height: 100vh;
        box-sizing: border-box;
        overflow-y: auto;
        padding: 25px 16px;
        background-color: #ffffff;
        border-right: 1px solid #d9e3ec;
        z-index: 100;
    }}

    #sidebar h3 {{
        margin: 0 0 20px;
        padding: 0 8px;
        font-size: 1.05em;
        color: #073965;
    }}

    #toc a {{
        display: block;
        padding: 8px 10px;
        margin: 3px 0;
        border-radius: 5px;
        color: #385e72;
        text-decoration: none;
        font-size: 0.85em;
        overflow-wrap: anywhere;
    }}

    #toc a.subsection {{
        padding-left: 22px;
        font-size: 0.8em;
    }}

    #toc a:hover,
    #toc a.active {{
        background-color: #e7f0f7;
        color: #073965;
    }}

    /* Contenu principal */
    #main-content {{
        margin-left: 250px;
        padding: 25px 35px;
        max-width: 1500px;
    }}

    h1 {{
        font-size: 2.2em;
        color: #073965;
        text-align: center;
    }}

    h2 {{
        font-size: 1.5em;
        color: #074276;
        background-color: transparent;
        margin: 40px 20px 15px;
        padding: 8px 15px;
        border-bottom: 2px solid #d5e0e9;
        scroll-margin-top: 20px;
        overflow-wrap: anywhere;
    }}

    h3 {{
        font-size: 1.15em;
        color: #155790;
        margin: 25px 30px 10px;
        padding: 5px 15px;
        border-left: 3px solid #6aabd2;
        scroll-margin-top: 20px;
        overflow-wrap: anywhere;
    }}

    p {{
        font-size: 1em;
        margin: 10px 20px;
        padding: 5px 15px;
        overflow-wrap: anywhere;
    }}

    a {{
        color: #1769aa;
    }}

    html {{
        scroll-behavior: smooth;
    }}

    /* Petits écrans */
    @media (max-width: 800px) {{
        #sidebar {{
            position: relative;
            width: 100%;
            height: auto;
            max-height: 280px;
            border-right: none;
            border-bottom: 1px solid #d9e3ec;
        }}

        #main-content {{
            margin-left: 0;
            padding: 10px;
        }}

        h2, h3, p {{
            margin-left: 5px;
            margin-right: 5px;
        }}
    }}
        
    </style>
    </head>
    <body>

    <nav id="sidebar">
        <h3>Table of Contents</h3>
        <div id="toc"></div>
    </nav>

    <main id="main-content">
    
    <p><br></p>
    <h1 >RNA-seq analysis report</h1>
    <h1 >{project}</h1>
    <p style="text-align:center;">This report was generated on {date_string} by <a href="https://parisepigenetics.github.io/bibs/edctools/workflows/rasflow_edc/">RASflow_EDC</a> on {server} cluster. Don’t forget to acknowledge <a href="https://parisepigenetics.github.io/bibs/">BiBs</a> in your communications.<br><br></p>
    <h2 id="project-settings">  Analysis settings</h2>
    <p>The settings used for the analysis can be found in the <a href="logs/{time_string}_configuration.txt">logs/{time_string}_configuration.txt</a>.<br></p>
    """
    f.write(message)
    
    if os.path.isfile(resultpath+'/'+project+"/fastqc/SRA.log"):
        message=f"""
    <h2 id="SRA">FASTQ files from SRA</h2>
    <p> {seq_type[config["END"]]} FASTQ files were downloaded from SRA. Information about the download can be found in <a href="fastqc/SRA.log">fastqc/SRA.log</a>. <br></p>
    """
    else : 
        message=f"""
    <h2 id="SRA">FASTQ files from personal data</h2>
    <p> The FASTQ files were not downloaded from SRA, but come from your personal data. {seq_type[config["END"]]} data were used. <br></p>
    """
    f.write(message)

    if os.path.isfile(resultpath+'/'+project+"/fastqc/report_quality_control.html"):
        message="""
    <h2 id="fastq-quality-control">FASTQ quality control</h2>
    <p>A summary of the quality of the raw sequences can be found in <a href="fastqc/report_quality_control.html">fastqc/report_quality_control.html</a>. <br></p>
    """
    else : 
        message="""
    <h2 id="fastq-quality-control">FASTQ quality control</h2>
    <p> QC report could not be found. Have you run QC before the rest of the analysis? If not, all the results might be impaired by low quality FASTQ reads. Running QC on raw sequences is highly recommended!<br></p>
    """
    f.write(message)

    if trim=='yes' : 
        message="""
    <h2 id="trimming">Trimming</h2>
    <p> Raw sequences were trimmed. A summary of the quality of the trimmed sequences can be found in 
    <a href="fastqc_after_trimming/report_quality_control_after_trimming.html">report_quality_control_after_trimming.html</a>. <br></p>
    """
        f.write(message)
    elif  trim != "disabled":
        message="""
    <h2 id="trimming">Trimming</h2>
    <p> The sequences were not trimmed and raw sequences were used for subsequent mapping. <br></p>
    """
        f.write(message)

    if mapping =='yes' and reference == "genome":
        message=f"""
    <h2 id="mapping-and-counting">Mapping and counting</h2>
    <p> The mapping was done using {aligner}. </p>
    <p>Mapping quality is assessed in <a href="mapping_{aligner}/report_align_count_{counter}.html">mapping_{aligner}/report_align_count_{counter}.html</a>. </p>
    <p>This report also contains an overview of feature counting that was perfomed by {counter}. </p>
    <p>Raw count tables are available in <a href="mapping_{aligner}/counting_{counter}/countTables/">mapping_{aligner}/counting_{counter}/countTables/</a> [Raw counts are not available in the online report].<br></p>
    <h2 id="exploratory-analysis-of-all-the-samples">Exploratory analysis of all the samples</h2>
    <p>To assess the quality of the experiment and the reproducibility of the replicates, please use the interactive 
    <a href="mapping_{aligner}/counting_{counter}/Glimma/MDSPlot.html">MDS plot</a>. 
    <p> <embed type="text/html" src="mapping_{aligner}/counting_{counter}/Glimma/MDSPlot.html" width="1000" height="900"> </p>
    <p>A static <a href="mapping_{aligner}/counting_{counter}/PCA.pdf">principal component analysis</a> 
    for all the samples is also available,  
    as well as a <a href="mapping_{aligner}/counting_{counter}/Heatmap_samples.pdf">heatmap with sample clustering</a>.  </p>
    <p><embed src= "mapping_{aligner}/counting_{counter}/Heatmap_samples.pdf" type="application/pdf" width= "700" height= "700"><br></p>
    """
        f.write(message)
        
        if repeats == 'yes':
            message=f"""
    <h2 id="repeat-analysis">Repeat analysis</h2>
    <p> You have enable the analysis of repeated elements using {counter}. </p>
    <p> Raw count tables for repeats are available in <a href="mapping_{aligner}/repeats_{counter}/countTables/">mapping_{aligner}/repeats_{counter}/countTables/</a> [Raw counts are not available in the online report].<br></p>
    <h2 id="exploratory-analysis-of-all-the-samples-for-the-repeats">Exploratory analysis of all the samples for the repeats</h2>
    <p>An interactive MDS plot based on repeat information only is shown at
    <a href="mapping_{aligner}/repeats_{counter}/Glimma/MDSPlot.html">MDS plot</a>. 
    <p> <embed type="text/html" src="mapping_{aligner}/repeats_{counter}/Glimma/MDSPlot.html" width="1000" height="900"> </p>
    <p>A static <a href="mapping_{aligner}/repeats_{counter}/PCA_TE.pdf">principal component analysis</a> 
    for all the samples is also available,  
    as well as a <a href="mapping_{aligner}/repeats_{counter}/Heatmap_samples_TE.pdf">heatmap with sample clustering</a>.  </p>
    <p><embed src= "mapping_{aligner}/repeats_{counter}/Heatmap_samples_TE.pdf" type="application/pdf" width= "700" height= "700"><br></p>
    """
            f.write(message)
    
    if mapping =='yes' and reference == "transcriptome":
        message=f"""
    <h2 id="quantification">Transcript quantification</h2>
    <p> Transcript quantification was done using Salmon. </p>
    <p>Quanfication quality is assessed in <a href="Salmon/report_quantify.html">Salmon/report_quantify.html</a>. </p>
    <p>Raw quantifications are available in <a href="Salmon/quantification/">Salmon/quantification/</a>.<br></p>
    <h2 id="exploratory-analysis-of-all-the-samples">Exploratory analysis of all the samples</h2>
    <p>To assess the quality of the experiment and the reproducibility of the replicates, please use the interactive 
    <a href="Salmon/Glimma/MDSPlot.html">MDS plot</a>. 
    <p> <embed type="text/html" src="Salmon/Glimma/MDSPlot.html" width="1000" height="900"> </p>
    <p>A static <a href="Salmon/PCA.pdf">principal component analysis</a> 
    for all the samples is also available,  
    as well as a <a href="Salmon/Heatmap_samples.pdf">heatmap with sample clustering</a>.  </p>
    <p><embed src= "Salmon/Heatmap_samples.pdf" type="application/pdf" width= "700" height= "700"><br></p>
    """
        f.write(message)
        

    if dea=='yes' :
        if reference == "genome":
            outpath = f"""mapping_{aligner}/counting_{counter}"""
        elif reference == "transcriptome":
            outpath = "Salmon"
        if fromcounts != "no" and fromcounts != False: 
            outpath = "fromExternalCounts"
        if mapping != 'yes':
            message=f"""
    <h2 id="exploratory-analysis-of-all-the-samples">Exploratory analysis of all the samples</h2>
    <p>To assess the quality of the experiment and the reproducibility of the replicates, please use the interactive 
    <a href="{outpath}/Glimma/MDSPlot.html">MDS plot</a>. 
    <p> <embed type="text/html" src="{outpath}/Glimma/MDSPlot.html" width="1000" height="900"> </p>
    <p>A static <a href="{outpath}/PCA.pdf">principal component analysis</a> 
    for all the samples is also available,  
    as well as a <a href="{outpath}/Heatmap_samples.pdf">heatmap with sample clustering</a>.  </p>
    <p><embed src= "{outpath}/Heatmap_samples.pdf" type="application/pdf" width= "700" height= "700"><br></p>
    """
            f.write(message)
            
        L = len(control)
        if L>1 : 
            message="""
            <h2 id="pairwise-differential-expression-analyses">Pairwise differential expression analyses</h2>
            <p>You have made """+str(L)+f""" pairwise comparisons using {deatool}. Please see below the results for each comparison.</p>
            """
        else:
            message=f"""
            <h2 id="pairwise-differential-expression-analyses">Pairwise differential expression analyses</h2>
            <p>You have made one pairwise comparison using {deatool}. Please see below the results for this comparison.</p>
            """

        f.write(message)
        
        def export_comparison(out_path, controlGroup, treatGroup, analysis):
            message=f"""
            <p><br></p>
            <h3 id="Comparison-between-{treatGroup}-and-{controlGroup}">Comparison between {treatGroup} and {controlGroup} for {analysis}</h3>
            <p>The <a href="{out_path}/Report/regionReport/{treatGroup}_{controlGroup}/exploration.html">regionReport exploratory report</a> 
            is a good start to get an idea of the results.</p> 
            <p>Glimma interactive <a href="{out_path}/Report/Glimma/MDSPlot_{treatGroup}_{controlGroup}.html">MDS plot</a> 
            can help you to identify problematic samples.</p>
            <p> <embed type="text/html" src="{out_path}/Report/Glimma/MDSPlot_{treatGroup}_{controlGroup}.html" width="1000" height="900"> </p>
            <p>To be easily shared and reused the <a href="{out_path}/Report/plots/PCA_{treatGroup}_{controlGroup}.pdf">PCA</a> 
            and the 
            <a href="{out_path}/Report/plots/SampleDistances_{treatGroup}_{controlGroup}.pdf">heatmap with sample clustering </a>
            are also available as PDF files.  </p> 
            <p>
            <embed src= "{out_path}/Report/plots/PCA_{treatGroup}_{controlGroup}.pdf" type="application/pdf" width= "700" height= "700">
            <embed src= "{out_path}/Report/plots/SampleDistances_{treatGroup}_{controlGroup}.pdf" width= "700" height= "700">
            </p>
            <p>DEA result tables (all {analysis} or significantly differentially expressed {analysis}) are stored in 
            <a href="{out_path}/Tables">{out_path}/Tables</a> [not available in the online report].</p>
            <p>Importantly, the results can be deeply explored thanks to <b>interactive</b>
            <a href="{out_path}/Report/Glimma/MDPlot_{treatGroup}_{controlGroup}.html">MD</a>
            and 
            <a href="{out_path}/Report/Glimma/Volcano_{treatGroup}_{controlGroup}.html">Volcano</a> 
            plots.</p>
            <p> <embed type="text/html" src="{out_path}/Report/Glimma/Volcano_{treatGroup}_{controlGroup}.html" width="1050" height="1000"> </p>
            <p>A static <a href="{out_path}/Report/plots/volcano_plot_{treatGroup}_{controlGroup}.pdf">Volcano plot</a> 
            is also available, as well as a 
            <a href="{out_path}/Report/plots/heatmapTop_{treatGroup}_{controlGroup}.pdf">heatmap of the 30 top-regulated {analysis}</a>. </p>
            <p>
            <embed src= "{out_path}/Report/plots/volcano_plot_{treatGroup}_{controlGroup}.pdf" type="application/pdf" width= "700" height= "700">
            <embed src= "{out_path}/Report/plots/heatmapTop_{treatGroup}_{controlGroup}.pdf" width= "700" height= "700">
            </p> 
                """ 
            f.write(message)
            
        for compa in zip(control,treat):
            controlGroup = compa[0]
            treatGroup = compa[1]    
        
            if reference == "transcriptome":
                genelevel = config["GENE_LEVEL"]
                if genelevel == True or genelevel == "yes" or genelevel == "TRUE": 
                    out_path = f"{outpath}/DEA_{deatool}/DEA_gene-level"
                    export_comparison(out_path, controlGroup, treatGroup, "genes")
                out_path = f"{outpath}/DEA_{deatool}/DEA_transcript-level"
                export_comparison(out_path, controlGroup, treatGroup, "transcripts")
                
            else: 
                out_path = f'{outpath}/DEA_{deatool}'
                export_comparison(out_path, controlGroup, treatGroup, "genes")
                
            if repeats == 'yes':
                out_path = f"mapping_{aligner}/repeats_{counter}/DEA_{deatool}"
                export_comparison(out_path, controlGroup, treatGroup, "repeats")
                
    
    message = """
    </main>

    <script>
    (function () {
        const toc = document.getElementById("toc");
        const headings = document.querySelectorAll(
            "#main-content h2, #main-content h3"
        );
        const usedIds = new Set();

        headings.forEach(function (heading) {
            // uniq ID for each section
            let id = heading.id || heading.textContent
                .trim()
                .toLowerCase()
                .replace(/[^a-z0-9]+/g, "-")
                .replace(/^-|-$/g, "");

            if (!id) {
                id = "section";
            }

            const baseId = id;
            let suffix = 2;

            while (usedIds.has(id)) {
                id = baseId + "-" + suffix++;
            }

            usedIds.add(id);
            heading.id = id;

            // link to table
            const link = document.createElement("a");
            link.href = "#" + id;
            link.textContent = heading.textContent.trim();

            if (heading.tagName === "H3") {
                link.classList.add("subsection");
            }

            toc.appendChild(link);
        });

        // highlighting section
        const links = toc.querySelectorAll("a");

        function updateActiveLink() {
            let current = headings[0];

            headings.forEach(function (heading) {
                if (heading.getBoundingClientRect().top <= 100) {
                    current = heading;
                }
            });

            links.forEach(function (link) {
                link.classList.toggle(
                    "active",
                    current && link.hash === "#" + current.id
                );
            });
        }

        window.addEventListener("scroll", updateActiveLink);
        updateActiveLink();
    })();
    </script>

    </body>
    </html>
    """


    f.write(message)

    f.close()
    
    ## add this report to the tar. 
    Tar.add(dirName+'/'+time_string+'_report.html', time_string+'_report.html')
    Tar.close()
