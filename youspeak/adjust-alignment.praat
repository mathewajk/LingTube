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
	comment Review List Directory
	sentence out_list_dir replace_me_with_out_listpath
endform

#first rename
clearinfo
Create Strings as file list... list 'audio_dir$'*.wav
number_of_files = Get number of strings

Read Strings from raw text file... 'out_list_dir$'full-review.txt
Read Strings from raw text file... 'out_list_dir$'flagged-review.txt

for i_file to number_of_files
	select Strings list
	soundname$ = Get string... i_file
	name$ = soundname$-".wav"
	Read from file... 'audio_dir$''name$'.wav
	Read from file... 'tg_dir$''name$'.TextGrid

	# Now bring up the editor to work on fixing the boundaries

	select Sound 'name$'
	plus TextGrid 'name$'
	Edit
		beginPause: "Edit Text Grid"
			comment: "Please adjust the boundaries on the TextGrid."
		clicked = endPause: "Quit", "Skip", "Done", "Flag", 3, 1
		if clicked = 1
					endeditor
					select all
					Remove
					exitScript ()
		elsif clicked = 2
					select TextGrid 'name$'
					plus Sound 'name$'
					Remove
		elsif clicked = 3
					# Now save the result
					select TextGrid 'name$'
					Write to text file... 'out_tg_dir$''name$'.TextGrid
					Remove
					select Sound 'name$'
					Write to WAV file... 'out_audio_dir$''name$'.wav
					Remove
					# Now add filename to full review file
					select Strings full-review
					Insert string... 0 'name$'.wav
					Save as raw text file... 'out_list_dir$'full-review.txt
					# Delete file
					filedelete 'audio_dir$''name$'.wav
		elsif clicked = 4
					# Now save the result
					select TextGrid 'name$'
					Write to text file... 'out_tg_dir$''name$'.TextGrid
					Remove
					select Sound 'name$'
					Write to WAV file... 'out_audio_dir$''name$'.wav
					Remove
					# Write filename to flagged review file
					select Strings flagged-review
					Insert string... 0 'name$'.wav
					Save as raw text file... 'out_list_dir$'flagged-review.txt
					# Delete file
					filedelete 'audio_dir$''name$'.wav
		endif
	endeditor

endfor

select all
Remove
