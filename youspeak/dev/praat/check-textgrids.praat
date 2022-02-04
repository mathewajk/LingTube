## text grid reviewer.praat
## Originally created by the excellent Katherine Crosswhite
## Script modified by Mark Antoniou
## MARCS Auditory Laboratories C 2010
## Script modified by Lauretta Cheng 2021

##  This script opens all the sound files in a given directory, plus
##  their associated textgrids so that you can review/change the
##  boundaries or labels.

form Enter directory and search string
# Be sure not to forget the slash (Windows: backslash, OSX: forward
# slash)  at the end of the directory name.
	sentence Directory ./audio/
	sentence Tg_directory ./textgrids/
#  Leaving the "Word" field blank will open all sound files in a
#  directory. By specifying a Word, you can open only those files
#  that begin with a particular sequence of characters. For example,
#  you may wish to only open tokens whose filenames begin with ba.
	sentence Vowel_number 0001
	sentence Filetype wav
endform

Create Strings as file list... list 'directory$'*'vowel_number$'*'filetype$'
number_of_files = Get number of strings
for x from 1 to number_of_files
     select Strings list
     current_file$ = Get string... x
	 #basename$ = current_file$ - ".wav"
	 #printline 'basename$'
     Read from file... 'directory$''current_file$'
     object_name$ = selected$ ("Sound")
     Read from file... 'tg_directory$''object_name$'.TextGrid
     plus Sound 'object_name$'
     Edit
     pause  Make any changes then click Continue. 
     minus Sound 'object_name$'
     Write to text file... 'tg_directory$''object_name$'.TextGrid
     select all
     minus Strings list
     Remove
endfor

select Strings list
Remove
clearinfo
printline TextGrids have been reviewed for 'vowel_number$' .'filetype$' files in 
printline 'directory$'.

## written by Katherine Crosswhite
## crosswhi@ling.rochester.edu
