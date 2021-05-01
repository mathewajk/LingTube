#########################################################################
# This is a script that automatically brings up a Sound and
# TextGrid for adjusting boundaries after forced alignment.
# It is a component of adjust-textgrids.py in LingTube/YouSpeak.
# -------------------------------------------------------------
# Lauretta Cheng, 2021
# Based on scripts by Grant McGuire, Katherine Crosswhite, Mark Antoniou
#########################################################################

# Compatible with both Windows and OSX
# Requires the slash at the end of the directory name.
# (Windows: backslash, OSX: forward slash)

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
