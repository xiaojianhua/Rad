#! /usr/bin/env python

import re, sys, os, itertools, sets, getopt        # Load standard modules I often use
import pickle


'''
This script will generate the required input file for dadi based on Stacks output data.  Required input is an output directory to write results, popmap file, plink ped file, plink map file, fasta file of consensus sequences for each locus (as generated by consensus_fasta.py), name of outgroup in popmap file, and comma separated list of ingroup populations (e.g. west,east,mexico,africa). Note that the position in PLINK for this version of Stacks is 1 position off, so this script corrects for the actual position (every position is actually +1).

Note also that all loci that are heterozygous in the outgroup will be removed from the dadi input file.
'''

def main(argv):
	try:
		opts,args = getopt.getopt(argv,'ho:m:P:M:f:O:I:',)
	except getopt.GetOptError:
		print "dadi_format_converter.py -o <path to output file (default ./dadi_format.txt)> -m <Popmap file> -P <Plink ped file> -M <Plink map file> -f <Fasta file of consensus sequences for each locus> -O <outgroup> -I <Ingroup comma separated list>"
		sys.exit(2)
			
	output = './dadi_format.txt'
	plinkped = ''
	plinkmap = ''
	popmap = ''
	fastafile = ''
	outgroup = ''
	ingroups = ''

	for opt, arg in opts:
		if opt == "-h":
			print "dadi_format_converter.py -o <path to output file (default ./dadi_format.txt)> -m <Popmap file> -P <Plink ped file> -M <Plink map file> -f <Fasta file of consensus sequences for each locus> -O <outgroup> -I <Ingroup comma separated list>"
			sys.exit(2)
		elif opt == "-o":
			output = arg
		elif opt == "-m":
			popmap = arg
		elif opt == "-P":
			plinkped = arg
		elif opt == "-M":
			plinkmap = arg
		elif opt == "-f":
			fastafile = arg
		elif opt == "-O":
			outgroup = arg
		elif opt == "-I":
			ingroups = arg

	#The PLINK ped file contains all genotype information for individuals in rows.  Note that the first 6 columns of each row are special.  Relevant here is the populations ID (first column) and individual ID (second column).  The PLINK map file contains locus information.  Most important is the second column, which has the locus catalog_id "_" position on the read.
	ped = open(plinkped,"r")
	map = open(plinkmap,"r")

	#Get locus position information
	locusid = []
	catid = []
	tagpos = []
	bp = []

	for row in map:
		if row[0] == "#":
			pass
		else:
			row = row.split("\t")
			locusid.append(row[1])
			loc = row[1]
			sep = loc.split("_")
			catid.append(sep[0])
			tagpos.append(sep[1])
			row_bp = row[3].strip()
			bp.append(row_bp)

	#Get individual genotypes (make a dictionary), and make a dictionary of populations pop[list of individuals]
	indgendict = {}
	indpop = {}

	for row in ped:	
		if row[0] == "#":
			pass
		else:
			row = row.strip()
			row = row.split("\t")
			if row[0] not in indpop:
				indpop[row[0]]=[row[1]]
			else:
				indpop[row[0]].append(row[1])
			indgendict[row[1]]=row[6:]
			numlets = len(row[6:])


	#Make two lists, var1 with genotype 1 for a locus and var2 with genotype2 for a  locus.  The lists are in the same order as the catalog_ids and tag_postions from catid and tagpos.  The individual calls are in the order of indorder, which is extracted as the keys of the dictionary.  

	index = range(0,numlets-1,2)

	var1 = range(0,len(index))
	var2 = range(0,len(index))

	indorder = indgendict.keys()

	for ind in indorder:
		for i in range(0,len(index)):
			if type(var1[i]) == list:
				var1[i].append(indgendict[ind][index[i]])
			else:
				var1[i] = [indgendict[ind][index[i]]]
			if type(var2[i]) == list:
				var2[i].append(indgendict[ind][index[i]+1])
			else:
				var2[i] = [indgendict[ind][index[i]+1]]		

	genotypes = range(0,len(var1))

	for i in range(0,len(var1)):
		genotypes[i] = tuple(zip(var1[i],var2[i]))
	
	#Get a list of possible alleles at each locus, but removing 0, which is caused by missing data.	
	allele_vars = []	
	for i in range(0,len(genotypes)):
		alleles = list(set(itertools.chain.from_iterable(genotypes[i])))
		while '0' in alleles:
			alleles.remove('0')
		allele_vars.append(alleles)

		
	#Now, open the popmap and assign individuals into each of the populations listed in the popdict dictionary

	pops = open(popmap,"r")

	ingroups = ingroups.split(",")

	popdict = {}
	for line in pops:
		line = line.strip()
		line = line.split("\t")
		pop = line[1]
		ind = line[0]
		if pop not in popdict:
			popdict[pop] = [ind]
		else:
			popdict[pop].append(ind)

	#Extract the genotypes only for the individuals in each population, add them to the popgenotypes dictionary.

	popgenotypes = {}

	poppos = {}
	
	for pop in popdict:
		popposlist = []
		for ind in popdict[pop]:
			indpos = [int(i) for i,v in enumerate(indorder) if v==ind]
			indpos = indpos[0]
			popposlist.append(indpos)
		poppos[pop]=popposlist

	for pop in poppos:
		genset = []
		for locus in genotypes:
			newset = []
			for indpos in poppos[pop]:
				newset.append(locus[indpos])
			genset.append(tuple(newset))
		popgenotypes[pop]=genset

	#Open dadi output file and write the header
	ingroup_str = "\t".join(ingroups)
	
	dadi = open(output,"w")
	header = ("ingroup",outgroup,"Allele1",ingroup_str,"Allele2",ingroup_str,"tag_id","position\n")
	header = "\t".join(header)

	dadi.write(header)
	
	#Create a dictionary of counts in the ingroup population for alleles of interest.
	allele1_dict = {}
	allele2_dict = {}
	
	for loc in range(0,len(locusid)):
		allele1_cnts = []
		allele2_cnts = []
		for popnum in range(0,len(ingroups)):
			pop_alleles = popgenotypes[ingroups[popnum]][loc]
			pop_alleles_list = list(sum(pop_alleles,()))
			allele1_cnts.append(str(pop_alleles_list.count(allele_vars[loc][0])))
			allele2_cnts.append(str(pop_alleles_list.count(allele_vars[loc][1])))
		allele1_dict[locusid[loc]] = allele1_cnts
		allele2_dict[locusid[loc]] = allele2_cnts
		
	#Need to obtain base right before and after SNP in both ingroups and outgroups.  I will do this with the consensus sequences output in the fasta file.  Because the outgroups were included in the Stacks library, the bases surrounding SNPs should be the same in ingroups and outgroups if there was no SNP present.  For the outgroup variant types, I will pull the genotypes of the outgroup sequences in the popgenotypes dictionary.
	
	#First, open and parse the fasta file into a dictionary called "seqs"
	fasta = open(fastafile,"r")
	
	order = []
	seqs = {}
	
	for line in fasta:
		if line.startswith('>'):
			name = line[1:].strip()
			order.append(name)
			seqs[name] = ''
		else:
			seqs[name] += line.strip()
			
	in_ref = {}
	out_ref = {}
	
	outhet = 0
	outhom = 0
	
	#Make a list of True or False as to whether the outgroups are heterozyous, and therefore the locus should be kept or dropped.
	keep = []
	
	#Iterate through all SNPs, pull surrounding bases and consensus SNP
	for pos in range(0,len(locusid)):
		catid_loc = catid[pos]
		#Note here the positions in the plink files are 1 nucleotide off (short), liekly because the count starts at 0, so I add 1 to each position.
		tagpos_loc = int(tagpos[pos])+1
		
		
		con_seq = seqs[catid_loc]
		
		#Get first base from consensus, if first base in the consensus sequence is not the SNP
		if tagpos_loc == 1:
			first = "-"
		else:
			first = con_seq[tagpos_loc-2]
		
		#Get the ingroup reference base
		in_ref_var = con_seq[tagpos_loc-1]
		
		#Get third base from consensus, if third base in the consensus sequence is not the SNP
		if tagpos_loc >= len(con_seq):
			third = "_"
		else:
			third = con_seq[tagpos_loc]
		
		in_ref_triple = [first,in_ref_var,third]
		in_ref[locusid[pos]] = "".join(in_ref_triple)
		

		
		out_ref_var_list = list(sum(popgenotypes[outgroup][pos],()))
		#Test if there is any variation in outgroup genotypes, if not, record variant
		if out_ref_var_list.count(out_ref_var_list[0]) == len(out_ref_var_list):
			if out_ref_var_list[0] == "0":
				out_ref_var = "-"
				first = third = "-"
				outhom += 1
				keep.append("TRUE")
			else:
				out_ref_var = out_ref_var_list[0]
				outhom += 1
				keep.append("TRUE")
		elif '0' in out_ref_var_list:#Remove missing individuals if that is causing discrepancy
			while '0' in out_ref_var_list:
				out_ref_var_list.remove('0')
			if out_ref_var_list.count(out_ref_var_list[0]) == len(out_ref_var_list):
				out_ref_var = out_ref_var_list[0]
				outhom += 1
				keep.append("TRUE")
			else:
				outhet += 1
				keep.append("FALSE")

		else:
			outhet += 1
			keep.append("FALSE")
		
		out_ref_triple = [first,out_ref_var,third]
		out_ref[locusid[pos]] = "".join(out_ref_triple)
		
		
		
	#Write results to dadi input file, and exclude any loci that were heterozygous in the outgroup.
	
	out_present = 0
	out_missing = 0
	
	for loc in range(0,len(locusid)):
		if keep[loc] == "TRUE":
			line = [in_ref[locusid[loc]],out_ref[locusid[loc]],allele_vars[loc][0]]+allele1_dict[locusid[loc]]+[allele_vars[loc][1]]+allele2_dict[locusid[loc]]+[catid[loc],str(tagpos[loc])]
			line = "\t".join(line)
			line = line + "\n"
			dadi.write(line)
			if "-" in out_ref[locusid[loc]]:
				out_missing += 1
			else:
				out_present += 1
			
		else:
			pass

	print "There are %d loci with outgrouop information, and %d loci without outgroup information"%(out_present,out_missing)

	dadi.close()
	ped.close()
	map.close()
	pops.close()
	fasta.close()


if __name__ == "__main__":
		main(sys.argv[1:])