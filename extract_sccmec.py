import os
import sys
import regex as re
import subprocess

def config():
	import ConfigParser
	config = ConfigParser.ConfigParser()
	config.readfp(open(r'config.txt'))
	prokka_exe = config.get('configuration', 'prokka')
	blastn_exe = config.get('configuration', 'blastn')
	makeblastdb_exe = config.get('configuration', 'makeblastdb')
	inputFiles = config.get('configuration', 'input')
	contigs = config.get('configuration', 'contig')
	ccr = config.get('configuration', 'ccr')
	orfX = config.get('configuration', 'orfX')
	mecA = config.get('configuration', 'mecA')

	return prokka_exe, blastn_exe, makeblastdb_exe, inputFiles, contigs, ccr, orfX, mecA


def simple_sequence(file):
    with open(file) as f:
        lines = f.read()
        sequences = [line for line in lines.split('\n') if not ">" in line]
    nucl = ''.join(map(str,sequences))

    return nucl

def blastn(blastn_exe, database, query):
	outfmt = "6 qseqid qlen sseqid slen qstart qend sstart send length nident pident evalue"
	cmd = [blastn_exe, "-outfmt", outfmt, "-db", database]
	proc = subprocess.Popen(cmd,
		stdin=subprocess.PIPE,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT)
	results, err = proc.communicate(query)

	return results, err

def makeblastdb(makeblastdb_exe, working_dir, input_seq, nucl, db_name):
	os.chdir(working_dir)
	proc = makeblastdb_exe+' -in '+input_seq+' -dbtype '+nucl+' -out '+db_name
	os.system(proc)

	return db_name

def prokka_files(location):
	for file in os.listdir(location):
		if file.endswith(".ffn"):
			ffn = os.path.join(location, file)
		if file.endswith(".gff"):
			gff = os.path.join(location, file)
		if file.endswith(".fna"):
			fna = os.path.join(location, file)

	return ffn, gff, fna

def execute_prokka(prokka_exe, output_prokka, contigs):
	kingdom = "Bacteria"
	genus = "Staphylococcus"
	locustag = "saureus"
	cmd_prokka = prokka_exe+" --kingdom "+kingdom+ \
					" --outdir "+output_prokka+ \
					" --quiet "+ \
					" --genus "+genus+ \
					" --locustag "+locustag+ \
					" --centre 10 --compliant"+ \
					' '+contigs
	os.system(cmd_prokka)

def fasta2dict(file):
	fastadict = {}
	with open(file) as file_one:
		for line in file_one:
			line = line.strip()
			if not line:
				continue
			if line.startswith(">"):
				active_sequence_name = str(line.split()[0][1:])
				if active_sequence_name not in fastadict:
					fastadict[active_sequence_name] = []
				continue
			sequence = line
			fastadict[active_sequence_name].append(sequence)

	return fastadict

def get_sequence(contigs_dict, contig_id):
	seq = ""
	for i in contigs_dict.get(contig_id)[:]:
		seq += ''.join(i)

	return seq

#import string
#import random
#def id_generator(size=6, chars=string.ascii_lowercase + string.digits):
#	return ''.join(random.choice(chars) for _ in range(size))


def reverse_complement(seq):
	"""takes a sequence to get the reverse complement of it"""
	complement = {'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A'}
	bases = list(seq)
	bases = [complement[base] for base in bases]
	complement = ''.join(bases)
	reverse = complement[::-1]
	return reverse

def blast_parser(blastn_exe, db, query):
	blastfile, err = blastn(blastn_exe, db, query)
	best_hit = blastfile.split()[2]

	return best_hit

def get_contig(gff, query):
	with open(gff) as f:
		header = []
		lines = f.readlines()
		for line in lines:
			if query in line:
				header.append(line.split()[0])

	return header[0]

def checkContig(lst):
	return lst[1:] == lst[:-1]

def checkSense(sequence, contig):
	if re.findall("{pattern}".format(pattern=sequence), contig):
		return contig, "+"
	contig = reverse_complement(contig)
	if re.findall("{pattern}".format(pattern=sequence), contig):
		return contig, "-"

def clean_att(atts_location):
	"""
	Conditions to verify if seq is att,
	"""
	core = "TATCA"
	adjacent_core = "GA*G"
	stop_codons = ["TAA", "TGA"]

	for k in atts_location.keys():
		if not k[-3:] in stop_codons:
			del atts_location[k]
	for k in atts_location.keys():
		if not core in k:
			del atts_location[k]
	for k in atts_location.keys():
		if not re.findall("{pattern}".format(pattern=adjacent_core), k):
			del atts_location[k]

	cassette_coordinates = []
	for k, v in atts_location.iteritems():
		print "att: ", k, "location: ", v
		cassette_coordinates.append(v[0])

	from itertools import chain
	coordinates = sorted(list(chain(*cassette_coordinates)))

	return coordinates, atts_location


# ------------------------------------------------------------------------- #
# ------------------------------------------------------------------------- #
# ------------------------------------------------------------------------- #

def main():
	prokka_exe, blastn_exe, makeblastdb_exe, inputFiles, contigs, ccr, orfX, mecA = config()

	orfx_base = simple_sequence(os.path.join(inputFiles, orfX))
	mecA_base = simple_sequence(os.path.join(inputFiles, mecA))
	ccr_base = simple_sequence(os.path.join(inputFiles, ccr))

	nombre = contigs.split(".")[0]
	#print nombre
	contigs = os.path.join(inputFiles, contigs)
	working_dir = os.getcwd()
	#print working_dir
	#output = "output_" + id_generator()
	output = "output_"+nombre
	raw_data = os.path.join(working_dir, output)
	output_prokka = os.path.join(raw_data, "output_prokka")

	# execute prokka 
	execute_prokka(prokka_exe, output_prokka, contigs)
	ffn, gff, fna = prokka_files(output_prokka)

	# create nucleotide db
	db_dir = os.path.join(raw_data, "db_dir")
	if not os.path.isdir(db_dir):
		os.makedirs(db_dir)
	database = makeblastdb(makeblastdb_exe, db_dir, ffn, "nucl", "test_db")
	db = os.path.join(db_dir, database)

	# run blastn and parse output
	orfx_hit = blast_parser(blastn_exe, db, orfx_base)
	mecA_hit = blast_parser(blastn_exe, db, mecA_base)
	ccr_hit = blast_parser(blastn_exe, db, ccr_base)

	# find contig which contains orfx, mec and ccr
	contig_id_orfx = get_contig(gff, orfx_hit)
	contig_id_mecA = get_contig(gff, mecA_hit)
	contig_id_ccr = get_contig(gff, ccr_hit)
	contig_ids = [contig_id_orfx, contig_id_mecA, contig_id_ccr]

	print
	print("-"*78)
	print


	""" Check if sccmec core components are in the same contig to continue """
	if checkContig(contig_ids):

		contigs_dict = fasta2dict(fna)
		seq = get_sequence(contigs_dict, contig_id_orfx)
		nucl_dict = fasta2dict(ffn)
		actual_orfx = get_sequence(nucl_dict, orfx_hit)
		actual_mecA = get_sequence(nucl_dict, mecA_hit)
		actual_ccr = get_sequence(nucl_dict, ccr_hit)

		""" Check if orfX has the same sense as the contig or use the reverse complementary sequence """
		seq, sense = checkSense(actual_orfx, seq)
		#print sense
		for i in re.findall("{pattern}".format(pattern=actual_orfx), seq):
			print "orfX Location at: ", [(m.start(0), m.end(0)) for m in re.finditer("{}".format(i), seq)]

		print
		print("-"*78)
		print

		""" Extract 19 nucleotides located at the 3'- end of orfX gene corresponding to attL """
		att_actual_orfx = actual_orfx[len(actual_orfx)-21:-3]

		""" Search for attachment site sequences """
		atts_location = {}
		for i in re.findall("({att}){{s<=4}}".format(att=att_actual_orfx), seq):
			[(m.start(0), m.end(0)) for m in re.finditer("{}".format(i), seq)]
			atts_location[seq[m.start(0):(m.end(0)+3)]] = [(m.start(0), m.end(0)) for m in re.finditer("{}".format(i), seq)]

		""" Filter att sequences according to literature """
		coordinates, cleaned_atts_location = clean_att(atts_location)
		sccmec = seq[coordinates[0]:coordinates[-1]]

		print
		print("-"*78)
		print

		print "Contig Length: ", len(seq)
		print "SCCmec Length: ", len(sccmec)

		os.chdir(raw_data)
		""" EDIT """
		with open("sccmec_"+nombre, "w") as f:
			f.write(">sccmec_"+nombre+"_"+str(len(sccmec))+"\n")
			for i in range(0, len(sccmec), 60):
				f.write(sccmec[i:i+60]+'\n')
		with open("info.txt", "w") as f:
			f.write("General Information"+ '\n'+'\n')
			f.write("Strand Sense: "+sense+'\n')
			f.write("Contig Length: "+str(len(seq))+'\n')
			f.write("SCCmec Length: "+str(len(sccmec))+'\n'+'\n')
			f.write("Attachment Site Sequences"+'\n'+'\n')
			for k, v in cleaned_atts_location.iteritems():
				f.write("att: " + str(k) + " location: " + str(v[0]) + '\n')

	else:
		print "Error: core components are not in the same contig"
		sys.exit()


if __name__ == '__main__':
        main()