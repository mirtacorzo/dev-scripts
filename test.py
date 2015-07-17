#!/usr/bin/env python
#

import sys, getopt
import subprocess

def main(argv):
   inputfile = ''
   outputfile = ''
   try:
      opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
   except getopt.GetoptError:
      print 'test.py -i <inputfile> -o <outputfile>'
      sys.exit(2)
   for opt, arg in opts:
      if opt == '-h':
         print 'test.py -i <inputfile> -o <outputfile>'
         sys.exit()
      elif opt in ("-i", "--ifile"):
         inputfile = arg
         print 'Input file is "', inputfile
      elif opt in ("-o", "--ofile"):
         outputfile = arg
         print 'Output file is "', outputfile

if __name__ == "__main__":
   main(sys.argv[1:])

#subprocess.call("ls -l", shell=True)
#target = raw_input("Enter an IP or Host to ping:\n")
#host = subprocess.Popen(['host', target], stdout = subprocess.PIPE).communicate()[0]
#print host