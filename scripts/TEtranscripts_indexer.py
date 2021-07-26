#!/usr/bin/env python


import sys
import logging
import subprocess
import time

try:
    import cPickle as pickle
except ImportError:
    import pickle
    
import argparse
import os.path

import time
import re
import gzip
from math import ceil, floor
import collections
import operator


from TEToolkit.TEindex import *
from TEToolkit.IntervalTree import *
from TEToolkit.GeneFeatures import *
from TEToolkit.Constants import TEindex_BINSIZE


class IntervalTree(object):
    # for an unknown reason, this won't import from IntervalTree.py
    __slots__ = ('intervals', 'left', 'right', 'center')

    def __init__(self, intervals, depth=16, minbucket=16, _extent=None, maxbucket=512):
        """\
        `intervals` a list of intervals *with start and stop* attributes.
        `depth`     the depth of the tree
        `minbucket` if any node in the tree has fewer than minbucket
                    elements, make it a leaf node
        `maxbucket` even it at specifined `depth`, if the number of intervals >
                    maxbucket, split the node, make the tree deeper.

        depth and minbucket usually do not need to be changed. if
        dealing with large numbers (> 1M) of intervals, the depth could
        be increased to 24.

        Useage:

         >>> ivals = [Interval(2, 3), Interval(1, 8), Interval(3, 6)]
         >>> tree = IntervalTree(ivals)
         >>> sorted(tree.find(1, 2))
         [Interval(2, 3), Interval(1, 8)]

        this provides an extreme and satisfying performance improvement
        over searching manually over all 3 elements in the list (like
        a sucker). 

        the IntervalTree class now also supports the iterator protocol
        so it's easy to loop over all elements in the tree:

         >>> import operator
         >>> sorted([iv for iv in tree], key=operator.attrgetter('start'))
         [Interval(1, 8), Interval(2, 3), Interval(3, 6)]


        NOTE: any object with start and stop attributes can be used
        in the incoming intervals list.
        """ 
        
        depth -= 1
        if (depth == 0 or len(intervals) < minbucket) and len(intervals) < maxbucket:
            self.intervals = intervals
            self.left = self.right = None
            return 

        if _extent is None:
            # sorting the first time through allows it to get
            # better performance in searching later.
            intervals.sort(key=operator.attrgetter('start'))

        # when does this go with the _extent?
        left, right = _extent or (intervals[0].start, max(i.stop for i in intervals))
        center = (left + right) / 2.0

        self.intervals = []
        lefts, rights = [], []
        
        for interval in intervals:
            if interval.stop < center:
                lefts.append(interval)
            elif interval.start > center:
                rights.append(interval)
            else:  # overlapping.
                self.intervals.append(interval)
                
        self.left = lefts and IntervalTree(lefts, depth, minbucket, (intervals[0].start, center)) or None
        self.right = rights and IntervalTree(rights, depth, minbucket, (center, right)) or None
        self.center = center

    def find(self, start, stop):
        """find all elements between (or overlapping) start and stop"""
        if self.intervals and not stop < self.intervals[0].start:
            overlapping = [i for i in self.intervals if i.stop >= start and i.start <= stop]
        else:
            overlapping = []

        if self.left and start <= self.center:
            overlapping += self.left.find(start, stop)

        if self.right and stop >= self.center:
            overlapping += self.right.find(start, stop)

        return overlapping

    def find_gene(self, start, stop):
        """find all elements between (or overlapping) start and stop"""
        if self.intervals and not stop < self.intervals[0].start:
            overlapping = [i.gene for i in self.intervals if i.stop >= start and i.start <= stop]
        else:
            overlapping = []

        if self.left and start <= self.center:
            overlapping += self.left.find_gene(start, stop)

        if self.right and stop >= self.center:
            overlapping += self.right.find_gene(start, stop)

        return overlapping

    def __iter__(self):
        if self.left:
            for l in self.left:
                yield l

        for i in self.intervals:
            yield i

        if self.right:
            for r in self.right:
                yield r


class GeneFeatures:
    # For an unknown reason, this won't import from GeneFeatures
    """index of Gene annotations.
        """
    def __init__(self, GTFfilename, feature_type, id_attribute):

        self.featureIdxs_plus = {}
        self.featureIdxs_minus = {}
        self.featureIdxs_nostrand = {}
        self.features = []

        self.read_features(GTFfilename, feature_type, id_attribute)

    # Reading & processing annotation files
    def read_features(self, gff_filename, feature_type, id_attribute):

        # dict of dicts since the builtin type doesn't support it for some reason
        temp_plus = collections.defaultdict(dict)
        temp_minus = collections.defaultdict(dict)
        temp_nostrand = collections.defaultdict(dict)

        # read count of features in GTF file
        gff = GFF_Reader(gff_filename, id_attribute)
        i = 0
        counts = 0
        try:
            for f in gff:
                if f[0] is None:
                    continue
                if f[5] == feature_type:
                    counts += 1
                    if f[2] == ".":
                        sys.stderr.write("Feature %s does not have strand information." % f[0])
                    try:
                        if f[2] == ".":
                            temp_nostrand[f[1]][f[0]].append((f[3], f[4]))
                    except:
                        temp_nostrand[f[1]][f[0]] = [(f[3], f[4])]

                    try:
                        if f[2] == "+":
                            temp_plus[f[1]][f[0]].append((f[3], f[4]))
                    except:
                        temp_plus[f[1]][f[0]] = [(f[3], f[4])]

                    try:
                        if f[2] == "-":
                            temp_minus[f[1]][f[0]].append((f[3], f[4]))
                    except KeyError:
                        temp_minus[f[1]][f[0]] = [(f[3], f[4])]

                    # save gene id
                    if f[0] not in self.features:
                        self.features.append(f[0])

                    i += 1
                    if i % 100000 == 0:
                        sys.stderr.write("%d GTF lines processed. \n" % i)
        except:
            sys.stderr.write("Error occurred in %s. \n" % gff.get_line_number_string())
            raise

        if counts == 0:
            sys.stderr.write("Warning: No features of type '%s' found in gene GTF file. \n" % feature_type)

        # build interval trees
        for each_chrom in temp_plus.keys():
            inputlist = []
            for each_gene in temp_plus[each_chrom].keys():
                for (start, end) in temp_plus[each_chrom][each_gene]:
                    inputlist.append(Interval(each_gene, start, end))
            self.featureIdxs_plus[each_chrom] = IntervalTree(inputlist)

        for each_chrom in temp_minus.keys():
            inputlist = []
            for each_gene in temp_minus[each_chrom].keys():
                for (start, end) in temp_minus[each_chrom][each_gene]:
                    inputlist.append(Interval(each_gene, start, end))
            self.featureIdxs_minus[each_chrom] = IntervalTree(inputlist)

        for each_chrom in temp_nostrand.keys():
            inputlist = []
            for each_gene in temp_nostrand[each_chrom].keys():
                for (start,end) in temp_nostrand[each_chrom][each_gene]:
                    inputlist.append(Interval(each_gene, start, end))
            self.featureIdxs_nostrand[each_chrom] = IntervalTree(inputlist)

    def getFeatures(self):
        return self.features

    def Gene_annotation(self, itv_list):
        genes = []
        fs = []
        for itv in itv_list:
            try:
                if itv[3] == "+":
                    if itv[0] in self.featureIdxs_plus:
                        fs = self.featureIdxs_plus[itv[0]].find_gene(itv[1], itv[2])

                if itv[3] == "-":
                    if itv[0] in self.featureIdxs_minus:
                        fs = self.featureIdxs_minus[itv[0]].find_gene(itv[1], itv[2])

                if itv[3] == ".":
                    if itv[0] in self.featureIdxs_minus:
                        fs = self.featureIdxs_minus[itv[0]].find_gene(itv[1], itv[2])

                    if itv[0] in self.featureIdxs_plus:
                        fs += self.featureIdxs_plus[itv[0]].find_gene(itv[1], itv[2])
                    if itv[0] in self.featureIdxs_nostrand:
                        fs += self.featureIdxs_nostrand[itv[0]].find_gene(itv[1], itv[2])

                if len(fs) > 0:
                    genes = genes + fs

            except:
                raise

        return genes


def read_opts4(parser):
    args = parser.parse_args()
    if not os.path.isfile(args.afile):
        logging.error("No such file: %s ! \n" % args.afile)
        sys.exit(1)

    if args.itype.lower() not in ['gene', 'te']:
        logging.error("indexing mode %s not supported \n" % args.itype)
        sys.exit(1)
                
    # Level of logging for tool
    logging.basicConfig(
        level=(4 - args.verbose) * 10,
        format='%(levelname)-5s @ %(asctime)s: %(message)s ',
        datefmt='%a, %d %b %Y %H:%M:%S',
        stream=sys.stderr,
        filemode="w")
    
    args.error = logging.critical        # function alias
    args.warn = logging.warning
    args.debug = logging.debug
    args.info = logging.info
    
#    args.argtxt = "# ARGUMENTS LIST: \n# prefix = %s \n# file to index = \
#    %s \n# index type = %s" % (args.prefix, args.afile, args.itype)
    args.argtxt = "# ARGUMENTS LIST: \n# file to index = %s \n# index type = %s" % (args.afile, args.itype)
    return args 

def prepare_parser():
    desc = "Building an index for gene or transposable element annotations file for TEtranscripts/TEcount."

    exmp = "Example: TEtrancripts_indexer --afile gene_annotation.gtf --itype gene "

    parser = argparse.ArgumentParser(prog='TEtranscripts_indexer', description=desc, epilog=exmp)

    parser.add_argument('--afile', metavar='annotation-file', dest='afile', type=str, required=True,
                        help='file for indexing of annotations')
    parser.add_argument('--itype', metavar='index-type', dest='itype', type=str, required=True,
                        help='index type to build for this gtf (gene or TE)')
#    parser.add_argument('--project', metavar='name', dest='prefix', default='', help='Prefix for the index file. Default is empty string')
    parser.add_argument('--verbose', metavar='verbose', dest='verbose', type=int, default=2,
                        help='Set verbose level. 0: only show critical message, 1: show additional warning message, \
                        2: show process information, 3: show debug messages. DEFAULT:2')
    parser.add_argument('--version', action='version', version='%(prog)s 2.0.3')
    
    parser.add_argument('--output', metavar='output index file', dest='output_name', type=str, required=True,
                        help='output index file path')

    return parser


def main():
    """Start TEtranscripts_indexer......parse options......"""

    args = read_opts4(prepare_parser())

    info = args.info
    
    # Output arguments used for program
    info("\n" + args.argtxt + "\n")

    info("Processing %s annotation file ... \n" % args.itype)

#    filename = args.prefix + args.afile.split('/')[-1] + '.ind'
    #filename = args.afile.split('/')[-1] + '.ind'
    filename = args.output_name

    if args.itype.lower() == 'gene':
        try:
            info("Building gene index ....... \n")
            geneIdx = GeneFeatures(args.afile, "exon", "gene_id")
            info("Done building gene index ...... \n")

            with open(filename, 'wb') as filehandle:
                pickle.dump(geneIdx, filehandle, protocol=2)
            info("Done saving gene index\n")
            info("Gene index can be used by TEtranscripts and TElocal\n")
            info("Gene index saved to %s\n" % filename)
        
        except:
            sys.stderr.write("Error in building gene index \n")
            sys.exit(1)
            
    elif args.itype.lower() == 'te':
        try:
            teIdx = TEfeatures()
            cur_time = time.time()
            te_tmpfile = '.' + str(cur_time) + '.te.gtf'
            subprocess.call(['sort -k 1,1 -k 4,4g ' + args.afile + ' >' + te_tmpfile], shell=True)
            info("\nBuilding TE index ....... \n")
            teIdx.build(te_tmpfile)
            info("Done building TE index ...... \n")

            with open(filename, 'wb') as filehandle:
                pickle.dump(teIdx, filehandle, protocol=2)
            subprocess.call(['rm -f ' + te_tmpfile], shell=True)
            info("Done saving TE index\n")
            info("TE index can be only used by TEtranscripts/TEcount\n")
            info("TE index saved to %s\n" % filename)
                        
        except:
            sys.stderr.write("Error in building TE index \n")
            sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        sys.stderr.write("User interrupt !\n")
        sys.exit(0)
