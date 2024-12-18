#!/usr/bin/env python

'''
Created on Dec 6, 2017

@author: Ying Jin
@contact: yjin@cshl.edu
@author: Oliver Tam
@contact tam@cshl.edu
@author: Talitha Forcier
@contact: talitha@cshl.edu
@status:
@version: 2.2.1
'''
# python module
import sys
import os.path
import operator
import argparse
import traceback
import yaml

try:
   import cPickle as pickle
except ImportError:
   import pickle

import subprocess
from time import time
import pysam

from TEToolkit.IO.ReadInputs import read_opts3
from TEToolkit.TEindex import *
from TEToolkit.EMAlgorithm import *
from TEToolkit.IntervalTree import *
from TEToolkit.GeneFeatures import *


# Parameters to control the workflow 
with open('config_ongoing_run.yaml') as yamlfile:
    config = yaml.load(yamlfile,Loader=yaml.BaseLoader)
counter= config["COUNTER"]
    
def prepare_parser():
    desc = "Measuring TE expression per-sample."

    exmp = "Example: TEcount -b RNAseq.bam --GTF gene_annotation.gtf --TE TE_annotation.gtf --sortByPos --mode multi "

    parser = argparse.ArgumentParser(prog='TEcount', description=desc, epilog=exmp)

    parser.add_argument('-b', '--BAM', metavar='RNAseq.bam', dest='bam', required=True,
                        help='An RNAseq BAM file.')
    parser.add_argument('--GTF', metavar='genic-GTF-file', dest='gtffile', type=str, required=True,
                        help='GTF file for gene annotations')
    parser.add_argument('--TE', metavar='TE-GTF-file', dest='tefile', type=str, required=True,
                        help='GTF file for transposable element annotations')
    parser.add_argument('--format', metavar='input file format', dest='fileformat', type=str, default='BAM', choices=['BAM', 'SAM'],
                        help='Input file format: BAM or SAM. DEFAULT: BAM')
    parser.add_argument('--stranded', metavar='option', dest='stranded', type=str, default="no", choices=['no', 'forward', 'reverse'],
                        help='Is this a stranded library? (no, forward, or reverse). For "first-strand" cDNA libraries (e.g. TruSeq stranded), choose reverse. For "second-strand" cDNA libraries (e.g. QIAseq stranded), choose forward. DEFAULT: no.')
    parser.add_argument('--mode', metavar='TE counting mode', dest='te_mode', type=str, default='multi', choices=['uniq', 'multi'],
                        help='How to count TE: uniq (unique mappers only), or multi (distribute among all alignments).\
                        DEFAULT: multi')
    parser.add_argument('--project', metavar='name', dest='prefix', default='TEtranscripts_out',
                        help='Name of this project. DEFAULT: TEcount_out')
    parser.add_argument('--sortByPos', dest='sortByPos', action="store_true",
                        help='Alignment file is sorted by chromosome position.')
    parser.add_argument('-i', '--iteration', metavar='iteration', dest='numItr', type=int, default=100,
                        help='number of iteration to run the optimization. DEFAULT: 100')
    parser.add_argument('--maxL', metavar='maxL', dest='maxL', type=int, default=500,
                        help='maximum fragment length. DEFAULT:500')
    parser.add_argument('--minL', metavar='minL', dest='minL', type=int, default=0,
                        help='minimum fragment length. DEFAULT:0')
    parser.add_argument('-L', '--fragmentLength', metavar='fragLength', dest='fragLength', type=int, default=0,
                        help='average fragment length for single end reads. \
                        For paired-end, estimated from the input alignment file. DEFAULT: for paired-end, \
                        estimate from the input alignment file; for single-end, ignored by default.')
    parser.add_argument('--verbose', metavar='verbose', dest='verbose', type=int, nargs='?', default=2, const=3,
                        help='Set verbose level. 0: only show critical message, 1: show additional warning message, \
                        2: show process information, 3: show debug messages. DEFAULT:2')
    parser.add_argument('--version', action='version', version='%(prog)s 2.2.1')

    return parser


class UnknownChrom(Exception):
    pass


def count_reads(filename, format, geneIdx, teIdx, stranded, te_mode, sortByPos, numItr, fragLength, maxL):
    gene_tbl = {}
    te_tbl = {}
    libsize = []
    # check input files exist or not
    if not os.path.isfile(filename):
        sys.stderr.write("File %s does not exist or is not a file. \n" % filename)
        sys.exit(1)
    try:
        (gene_counts, te_instance_counts) = count_transcript_abundance(filename, format, geneIdx, teIdx, stranded,
                                                                       te_mode, sortByPos, numItr, fragLength, maxL)
        # summarize on elements
        te_ele_counts = teIdx.groupByEle(te_instance_counts)
        # save gene counts and TE counts into count table
        gene_tbl[filename] = dict(list(gene_counts.items())) 
        te_tbl[filename] = dict(list(te_ele_counts.items()))
        num_reads = sum(gene_counts.values()) + sum(te_ele_counts.values())
        libsize.append(num_reads)
    except:
        sys.stderr.write("Error: %s \n" % str(sys.exc_info()[1]))
        sys.stderr.write("[Exception type: %s, raised in %s:%d] \n" %
                         (sys.exc_info()[1].__class__.__name__,
                          os.path.basename(traceback.extract_tb(sys.exc_info()[2])[-1][0]),
                          traceback.extract_tb(sys.exc_info()[2])[-1][1]))
        sys.exit(1)

    return gene_tbl, te_tbl


def fetch_exon(chrom, st, cigar, direction, fileformat):
    ''' fetch exon regions defined by cigar. st must be zero based
    return list of tuple of (chrom,st, end)
    '''
    chrom_st = st + 1
    exon_bound = []

    for c, s in cigar:  # code and size
        if c == 0:  # match
            if direction == 0:
                exon_bound.append([chrom, chrom_st, chrom_st + s - 1, "."])
            if direction == 1:
                exon_bound.append([chrom, chrom_st, chrom_st + s - 1, "+"])
            if direction == -1:
                exon_bound.append([chrom, chrom_st, chrom_st + s - 1, "-"])
            chrom_st += s
        elif c == 1:  # insertion to ref
            continue
        elif c == 2:  # deletion to ref
            chrom_st += s
        elif c == 3:  # gap or intron
            chrom_st += s
        elif c == 4:  # soft clipping. We do NOT include soft clip as part of exon
            chrom_st += s
        else:
            continue
    return exon_bound


def ovp_annotation(references, multi_reads, geneIdx, teIdx, stranded, fileformat):
    annot_gene = []
    annot_TE = []

    # loop over every alignment
    for r1, r2 in multi_reads:
        itv_list = []
        direction = 1
        if r1 is not None and r1.is_reverse:
            direction = -1
        if r2 is not None and not r2.is_reverse:
            direction = -1
        chrom1 = ""
        if r1 is not None:
            chrom1 = references[r1.tid]
        chrom2 = ""
        if r2 is not None:
            chrom2 = references[r2.tid]

        if stranded == "no":
            direction = 0
        if stranded == "reverse":
            direction = direction * (-1)

        # fetch all mapping intervals
        itv_list = []
        if r1 is not None:
            itv_list = fetch_exon(chrom1, r1.pos, r1.cigartuples, direction, fileformat)

        if chrom2 != "":  # paired-end, both mates are mapped
            itv_list2 = fetch_exon(chrom2, r2.pos, r2.cigar, direction, fileformat)
            itv_list.extend(itv_list2)
        try:
            TEs = teIdx.TE_annotation(itv_list)
            genes = geneIdx.Gene_annotation(itv_list)

            if len(TEs) > 0:
                annot_TE.append(TEs)

            if len(genes) > 0:
                annot_gene.append(list(set(genes)))   
        except:
            sys.stderr.write("Error occurred during read assignments \n")
            raise

    return (annot_gene, annot_TE)


def readInAlignment(filename, fileformat, sortByPos):
    try:
        if fileformat == "BAM":
            if not sortByPos:
                samfile = pysam.AlignmentFile(filename, 'rb')
                if len(samfile.header) == 0:
                    sys.stderr.write("BAM/SAM file has no header section. Exit! \n")
                    sys.exit(1)

            else:
                cur_time = time.time()
                bam_tmpfile = '.' + str(cur_time)
                # pysam.sort("-n", filename, bam_tmpfile)  # For pysam v0.8.0 or earlier
                pysam.sort("-n","-T",bam_tmpfile,"-o",bam_tmpfile+".bam",filename)
                # For pysam v0.9.0+ and using htlibs/samtools 1.3+
                samfile = pysam.AlignmentFile(bam_tmpfile + ".bam", 'r')
                if len(samfile.header) == 0:
                    sys.stderr.write("BAM/SAM file has no header section. Exit! \n")
                    sys.exit(1)
                subprocess.call(['rm -f ' + bam_tmpfile + '.bam'], shell=True)
        else:
            samfile = pysam.AlignmentFile(filename, 'r')
            if len(samfile.header) == 0:
                sys.stderr.write("BAM/SAM file has no header section. Exit!\n")
                sys.exit(1)

    except:
        sys.stderr.write("Error occurred when reading first line of sample file %s.\n" % filename)
        raise
    return samfile


def count_transcript_abundance(filename, fileformat, geneIdx, teIdx, stranded, te_mode,
                               sortByPos, numItr, fragLength, maxL):
    # read in BAM/SAM file
    samfile = readInAlignment(filename, fileformat, sortByPos)

    references = samfile.references

    empty = 0
    nonunique = 0
    uniq_reads = 0

    i = 0
    prev_read_name = ''

    alignments_per_read = []
    leftOver_gene = []
    leftOver_te = []
    avgReadLength = 0
    tmp_cnt = 0
    multi_read1 = []
    multi_read2 = []
    paired = False
    gene_counts = dict(zip(geneIdx.getFeatures(), [0.0] * len(geneIdx.getFeatures())))
    te_counts = [0.0] * teIdx.numInstances()
    te_multi_counts = [0.0] * len(te_counts)
    multi_reads = []
    cc = 0
    try:
        while 1:
            i += 1
            cc += 1
            aligned_read = next(samfile)

            if aligned_read.is_unmapped or aligned_read.is_duplicate or aligned_read.is_qcfail:
                continue
           
            cur_read_name = aligned_read.query_name

            if aligned_read.is_paired:  # this is not reliable if read mate is unmapped
                added_flag_pos = aligned_read.query_name.find('/')
                if added_flag_pos == -1:
                    added_flag_pos = len(aligned_read.query_name)
                    if aligned_read.query_name.endswith(".1") or aligned_read.query_name.endswith(".2"):
                        added_flag_pos = len(aligned_read.query_name) - 2
                
                cur_read_name = aligned_read.query_name[:added_flag_pos]
                
                paired = True
                if cur_read_name == prev_read_name or prev_read_name == "":
                    prev_read_name = cur_read_name
                    if aligned_read.is_read1:
                        multi_read1.append(aligned_read)
                    if aligned_read.is_read2:
                        multi_read2.append(aligned_read)
                    continue

                else:
                    if len(multi_read1) <= 1 and len(multi_read2) <= 1:
                        uniq_reads += 1
                        read1 = None
                        read2 = None
                        if len(multi_read1) == 1:
                            read1 = multi_read1[0]
                        if len(multi_read2) == 1:
                            read2 = multi_read2[0]
                        if read1 is not None and read1.is_proper_pair:
                            if read2 is None:
                                sys.stderr.write("******NOT COMPLETE******* \n")
                                sys.stderr.write("If the BAM file is sorted by coordinates, \
                                please specify --sortByPos and re-run! \n")
                                sys.exit(0)
                            if tmp_cnt < 10000:
                                pos1 = read1.reference_start
                                pos2 = read2.reference_start
                                if abs(pos1 - pos2) <= maxL:
                                    avgReadLength += abs(pos1 - pos2) + read2.query_length
                                    tmp_cnt += 1

                        alignments_per_read.append((read1, read2))

                    else:
                        nonunique += 1
                        if te_mode == 'uniq':
                            empty += 1
                            alignments_per_read = []
                            multi_read1 = []
                            multi_read2 = []
                            prev_read_name = cur_read_name
                            if aligned_read.is_read1:
                                multi_read1.append(aligned_read)
                            if aligned_read.is_read2:
                                multi_read2.append(aligned_read)
                            continue

                        else:  # singleton
                            if len(multi_read2) == 0:
                                for r in multi_read1:
                                    alignments_per_read.append((r, None))
                            if len(multi_read1) == 0:
                                for r in multi_read2:
                                    alignments_per_read.append((None, r))
                            if len(multi_read2) == len(multi_read1):
                              for i in range(len(multi_read1)):
                                read1 = multi_read1[i]
                                read2 = multi_read2[i]
                                alignments_per_read.append((read1, read2))

            else:  # single end read
                if cur_read_name == prev_read_name or prev_read_name == "":
                    alignments_per_read.append((aligned_read, None))
                    prev_read_name = cur_read_name
                    continue

                else:  # a new read
                    if tmp_cnt < 10000:
                        avgReadLength += aligned_read.query_length
                        tmp_cnt += 1

                    if len(alignments_per_read) == 1:
                        uniq_reads += 1

                    else:
                        nonunique += 1
                        if te_mode == 'uniq':  # ignore multi-reads
                            empty += 1
                            alignments_per_read = []
                            prev_read_name = cur_read_name
                            alignments_per_read.append((aligned_read, None))
                            continue

            try:
                (annot_gene, annot_TE) = ovp_annotation(references, alignments_per_read, geneIdx,
                                                        teIdx, stranded, fileformat)

                if len(alignments_per_read) > 1:  # multi read, prior to TE
                    no_annot_te = parse_annotations_TE(multi_reads, annot_TE, te_counts, te_multi_counts, leftOver_te)

                    if no_annot_te:
                        no_annot_gene = parse_annotations_gene(annot_gene, gene_counts, leftOver_gene)
                        if no_annot_gene:
                            empty += 1

                else:  # uniq read, prior to gene
                    no_annot_gene = parse_annotations_gene(annot_gene, gene_counts, leftOver_gene)
                    if no_annot_gene:
                        no_annot_te = parse_annotations_TE(multi_reads, annot_TE, te_counts,
                                                           te_multi_counts, leftOver_te)
                        if no_annot_te:
                            empty += 1

            except:
                sys.stderr.write("Error occurred when processing annotations of %s in file %s. \n" %
                                 (prev_read_name, filename))
                raise

            if i % 1000000 == 0:
                sys.stderr.write("%d alignments processed. \n" % i)

            alignments_per_read = []
            multi_read1 = []
            multi_read2 = []
            prev_read_name = cur_read_name

            if not aligned_read.is_paired:
                alignments_per_read.append((aligned_read, None))

            else:
                if aligned_read.is_read1:
                    multi_read1.append(aligned_read)
                if aligned_read.is_read2:
                    multi_read2.append(aligned_read)

    except StopIteration:
        pass  # the last read

    try:
        # resolve ambiguity
        if len(leftOver_gene) > 0:
            resolve_annotation_ambiguity(gene_counts, leftOver_gene)
        if len(leftOver_te) > 0:
            resolve_annotation_ambiguity(te_counts, leftOver_te)

        ss = sum(te_counts)
        sys.stderr.write("uniq te counts = %s \n" % repr(int(ss)))

        te_tmp_counts = [0] * len(te_counts)

        if numItr > 0:
            try:
                ''' iterative optimization on TE reads '''
                sys.stderr.write(".......start iterative optimization .......... \n")
                if not paired and fragLength > 0:
                    avgReadLength = fragLength

                elif avgReadLength > 0:
                    avgReadLength = avgReadLength // tmp_cnt

                else:
                    sys.stderr.write("There are not enough reads to estimate fragment length. \n")
                    raise
                new_te_multi_counts = [0] * len(te_counts)
                if len(multi_reads) > 0:
                    new_te_multi_counts = EMestimate(teIdx, multi_reads, te_tmp_counts, te_multi_counts,
                                                     numItr, avgReadLength)

            except:
                sys.stderr.write("Error in optimization \n")
                raise
            te_counts = list(map(operator.add, te_counts, new_te_multi_counts))

        else:
            te_counts = list(map(operator.add, te_counts, te_multi_counts))

    except:
        sys.stderr.write("Error occurred when assigning read gene/TE annotations in file %s. \n" % filename)
        raise
    st = sum(te_counts)
    sg = sum(gene_counts.values())
    num_reads = st + sg

    sys.stderr.write("TE counts total %s \n" % st)
    sys.stderr.write("Gene counts total %s \n" % sg)
    sys.stderr.write("\nIn library %s: \n" % filename)
    sys.stderr.write("Total annotated reads = %s \n" % repr(int(num_reads)))
    sys.stderr.write("Total non-uniquely mapped reads = %s \n" % repr(int(nonunique)))
    sys.stderr.write("Total unannotated reads = %s \n\n" % repr(int(empty)))

    return gene_counts, te_counts


def parse_annotations_gene(annot_gene, gene_counts, leftOver_gene):
    if len(annot_gene) > 1:
        leftOver_gene.append((annot_gene, 1.0))
    elif len(annot_gene) == 1:
        genes = annot_gene[0]
        if len(genes) == 1:
            gene_counts[genes[0]] += 1
        else:
            for genname in genes:
                gene_counts[genname] += 1.0 / len(genes)

    else:
        return True

    return False


# Assign ambiguous genic reads mapped to a location with multiple annotations
def resolve_annotation_ambiguity(counts, leftOvers):
    for annlist, w in leftOvers:
        readslist = {}
        total = 0.0
        size = len(annlist)
        ww = 1.0 * w
        if size > 1:
            ww = ww / size

        for ann in annlist:
            for a in ann:
                if a not in readslist:
                    readslist[a] = counts[a]
                    total += counts[a]

        if total > 0.0:
            for a in readslist:
                v = ww * readslist[a] / (1.0*total)
                counts[a] += v
        else:
            for a in readslist:
                counts[a] = ww / len(readslist)


def parse_annotations_TE(multi_reads, annot_TE, uniq_counts, multi_counts, leftOver_list):
    if len(annot_TE) == 0:
        return True

    if len(annot_TE) == 1 and len(annot_TE[0]) == 1:
        uniq_counts[annot_TE[0][0]] += 1

    if len(annot_TE) == 1 and len(annot_TE[0]) > 1:
        leftOver_list.append((annot_TE, 1.0))

    if len(annot_TE) > 1:
        multi_algn = []
        for i in range(len(annot_TE)):
            for te in annot_TE[i]:
                multi_counts[te] += 1.0 / (len(annot_TE) * len(annot_TE[i]))
                multi_algn.append(te)

        multi_reads.append(multi_algn)

    return False


def output_count_tbl(tbl, prefix, element):
    smp=prefix.split("_")[0]
    try:
        f = open("{}_{}_count.tsv".format(prefix,element), 'w')
    except IOError:
        sys.stderr.write("Cannot create report file %s ! \n" % fname)
        sys.exit(1)
    else:
        cnt_tbl = {}
        header = element
        keys = set([])
        for tsmp in tbl:
            keys = keys.union(list(tbl[tsmp].keys()))
            header += "\t"+smp
            cnts = tbl[tsmp]
            for k in keys:
                val = 0
                if k in cnts:
                    val = cnts[k]

                if k in cnt_tbl:
                    cnt_tbl[k].append(int(val))

                else:
                    vallist = [int(val)]
                    cnt_tbl[k] = vallist

        # output
        f.write(header + "\n")
        for gene in sorted(cnt_tbl.keys()):
            vals = cnt_tbl[gene]
            vals_str = gene
            for i in range(len(vals)):
                vals_str += "\t" + str(vals[i])
            f.write(vals_str + "\n")
        f.close()

    return


# Main function of script
def main():
    """Start TEcount......parse options......"""

    args = read_opts3(prepare_parser())

    info = args.info
    error = args.error

    # Output arguments used for program
    info("\n" + args.argtxt + "\n")

    info("Processing GTF files ... \n")

    # gene index
    if args.gtffile[-4:] == '.gtf':
        try:
            info("Building gene index ....... \n")
            geneIdx = GeneFeatures(args.gtffile, args.stranded, "exon", "gene_id")
            info("Done building gene index ...... \n")
        except:
            sys.stderr.write("Error in building gene index \n")
            sys.exit(1)

    elif args.gtffile[-4:] == '.ind':
        info("File extension indicates a pre-built gene index, attempting to load ...... \n")
        try:
            with open(args.gtffile, 'rb') as newhandle:
                geneIdx = pickle.load(newhandle)
            info("gene index loaded ...... \n")
        except:
            sys.stderr.write("Error attempting to load %s \n" % args.gtffile)
            sys.exit(1)

    else:
        sys.stderr.write("Gene annotation file extension not recognized, it needs to be either .gtf or .ind")
        sys.exit(1)

    # TE index
    if args.tefile[-4:] == '.gtf':
        try:
            teIdx = TEfeatures()
            cur_time = time.time()
            te_tmpfile = '.' + str(cur_time) + '.te.gtf'
            subprocess.call(['sort -k 1,1 -k 4,4g ' + args.tefile + ' >' + te_tmpfile], shell=True)
            info("Building TE index ....... \n")
            teIdx.build(te_tmpfile)
            subprocess.call(['rm -f ' + te_tmpfile], shell=True)
            info("Done building TE index ...... \n")

        except:
            sys.stderr.write("Error in building TE index \n")
            sys.exit(1)

    elif args.tefile[-4:] == '.ind':
        info("File extension indicates a pre-built TE index, attempting to load ...... \n")
        try:
            with open(args.tefile, 'rb') as newhandle:
                teIdx = pickle.load(newhandle)
            info("TE index loaded ...... \n")
        except:
            sys.stderr.write("Error attempting to load %s\n" % args.tefile)
            sys.exit(1)
    else:
        sys.stderr.write("TE annotation file extension not recognized, it needs to be either .gtf or .ind")
        sys.exit(1)

    # Read sample files make count table
    info("\nReading sample file ... \n")
    
    (gene_tbl,te_tbl) = count_reads(args.bam, args.fileformat, geneIdx, teIdx, args.stranded, args.te_mode, args.sortByPos,
                      args.numItr, args.fragLength, args.maxL)
    info("Finished processing sample file")
    #make count TE table
    output_count_tbl(te_tbl, args.prefix, "TE")
    #make count genes table
    if counter == "TEcount":
        output_count_tbl(gene_tbl, args.prefix, "gene")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write("User interrupt! \n")
        sys.exit(0)

