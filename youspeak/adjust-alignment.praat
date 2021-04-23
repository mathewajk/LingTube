################################################################
# This is a script that automatically brings up a TextGrid for
# marking boundaries. The 'outdir' - the directory to where the
# files are written must be different from the text grid source
# directory or else the progam will keep bringing up the same
# files if you don't finish in one session. A text grid is only
# saved if you click 'continue'.
# -------------------------------------------------------------
# Modified by Lauretta Cheng - UM - Apr 2021
# Original by Grant McGuire - UCSC - July 2011
################################################################

# Be sure not to forget the slash (Windows: backslash, OSX: forward
# slash)  at the end of the directory name.

form Modify textgrids
	comment Source Audio Directory
	sentence audio_dir	replace_me_with_audpath
	comment Aligned Textgrid Directory
	sentence tg_dir	replace_me_with_tgpath
	comment Directory to move the original Sound files to
	sentence out_audio_dir replace_me_with_out_audpath
	comment Directory to write the TextGrid to
	sentence out_tg_dir replace_me_with_out_tgpath
endform

#first rename
clearinfo
Create Strings as file list... list 'audio_dir$'*.wav
all = Get number of strings
iter = 0

for ifile to all
	select Strings list
	soundname$ = Get string... ifile
	name$ = soundname$-".wav"
	Read from file... 'audio_dir$''name$'.wav

	# Read in TextGrid
	select Sound 'name$'
	Read from file... 'tg_dir$''name$'.TextGrid

	# Now bring up the editor to work on fixing the boundaries

	select Sound 'name$'
	plus TextGrid 'name$'
	Edit
		#pause Please Edit TextGrid
		beginPause: "Edit Text Grid"
			comment: "Please adjust the boundaries on the TextGrid."
		clicked = endPause: "Quit", "Save & Continue", 2, 1
		if clicked = 1
					endeditor
					select all
					Remove
					exitScript ()
		endif
    endeditor

	# Now save the result
	select TextGrid 'name$'
	Write to text file... 'out_tg_dir$''name$'.TextGrid
	select Sound 'name$'
	Write to WAV file... 'out_audio_dir$''name$'.wav
	filedelete 'audio_dir$''name$'.wav
	iter = iter + 1

# Clear the lists
select all
minus Strings list
Remove
endfor

select Strings list
Remove
