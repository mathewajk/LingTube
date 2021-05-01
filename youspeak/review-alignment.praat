#########################################################################
# This is a script that automatically brings up a Sound and
# TextGrid for reviewing/changing the boundaries or labels.
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
	sentence audio_dir	replace_me_with_out_audpath
	comment Source Textgrid Directory
	sentence tg_dir	replace_me_with_out_tgpath
endform

Create Strings as file list... list 'audio_dir$'*.wav
number_of_files = Get number of strings
for x from 1 to number_of_files
     select Strings list
     current_file$ = Get string... x
		 #basename$ = current_file$ - ".wav"
		 #printline 'basename$'
     Read from file... 'audio_dir$''current_file$'
     object_name$ = selected$ ("Sound")
     Read from file... 'tg_dir$''object_name$'.TextGrid
     plus Sound 'object_name$'
     Edit
		 beginPause: "Edit Text Grid"
			 comment: "Make any changes then continue."
		 clicked = endPause: "Quit", "Save & Continue", 2, 1
		 if clicked = 1
					 endeditor
					 select all
					 Remove
					 exitScript ()
		 endif
     minus Sound 'object_name$'
     Write to text file... 'tg_dir$''object_name$'.TextGrid
     select all
     minus Strings list
     Remove
endfor

select Strings list
Remove
clearinfo
printline TextGrids have been reviewed for files in 'audio_dir$'.
