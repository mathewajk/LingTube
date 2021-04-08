################################################################
# This is a script that automatically brings up a TextGrid for #
# marking boundaries. The 'outdir' - the directory to where the#
# files are written must be different from the text grid source#
# directory or else the progam will keep bringing up the same  #
# files if you don't finish in one session. A text grid is only#
# saved if you click 'continue'. 							     #
# **MAC VERSION**		                                        #
# -------------------------------------------------------------#
# Updated by Lauretta Cheng - UM - Apr 2021                    #
# Original by Grant McGuire - UCSC - July 2011					 #
################################################################

form Modify textgrids
	comment Source Audio Directory
	sentence sourcedir	replace_me_with_audpath
	comment Aligned Textgrid Directory
	sentence aligndir	replace_me_with_tgpath
	comment Directory to move the original files to
	sentence outauddir replace_me_with_out_audpath
	comment Directory to write the TextGrid
	sentence outtgdir replace_me_with_out_tgpath
endform

#first rename
clearinfo
Create Strings as file list... list 'sourcedir$'/*.wav
all = Get number of strings
iter = 0

for ifile to all
	select Strings list
	soundname$ = Get string... ifile
	name$ = soundname$-".wav"
	Read from file... 'sourcedir$'/'name$'.wav

	# Read in TextGrid
	select Sound 'name$'
	Read from file... 'aligndir$'/'name$'.TextGrid
	
	# Now bring up the editor to work on fixing the boundaries
	select Sound 'name$'
	plus TextGrid 'name$'
	Edit
		pause Please Edit Text Grid
		endeditor	
	
	# Now save the result
	select TextGrid 'name$'
	Write to text file... 'outtgdir$'/'name$'.TextGrid
	select Sound 'name$'
	Write to WAV file... 'outauddir$'/'name$'.wav
	filedelete 'sourcedir$'/'name$'.wav
	iter = iter + 1

# Clear the lists
select all
minus Strings list
Remove
endfor

select Strings list
Remove

