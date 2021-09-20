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
	sentence audio_dir	./audio/
	comment Source Textgrid Directory
	sentence tg_dir	./textgrids/
	comment Coding Log Filename
	sentence coding_log vowel_coding_log.csv
	#comment Review List Filename
	#sentence file_list review_list.txt
	comment Review All or Flagged Only
	boolean flagged_only 0
endform

if flagged_only = 0
	file_list$ = "review_list_all.txt"
	table_name$ = "all_rows"
elsif flagged_only = 1
	file_list$ = "review_list_flagged.txt"
	table_name$ = "flagged_rows"
endif

Read Table from comma-separated file... 'coding_log$'
Rename: "all_rows"
if flagged_only = 1
	Extract rows where... self$["flag"]="1"
	Rename: "flagged_rows"
endif

# If review_list file does not exist, create it
if !(fileReadable (file_list$))
	number_of_rows = Get number of rows

	Create Strings from tokens: "review_list_in", "", ""

	for i_file to number_of_rows
		select Table 'table_name$'
		soundname$ = Get value: i_file, "file"
		select Strings review_list_in
		Insert string: 0, soundname$
	endfor

	Save as raw text file... 'file_list$'
endif

if fileReadable: file_list$
	# Read the text file and put it to the string file$
	Read Strings from raw text file... 'file_list$'
	Rename... review_list_in
	Copy... review_list_out
endif

# Processing each file
list_index = 1

number_of_files = Get number of strings
for i_file to number_of_files
     select Strings review_list_in
     soundname$ = Get string... i_file
		 name$ = soundname$-".wav"
	 	 Read from file... 'audio_dir$''name$'.wav
     Read from file... 'tg_dir$''name$'.TextGrid

	# Print coding row values
	select Table 'table_name$'
	sound_row# = List row numbers where... self$[row,"file"]=soundname$
	clearinfo
	appendInfoLine: soundname$ + newline$
	sound_vowel$ = Get value: sound_row#[1], "vowel"
	appendInfoLine: "Vowel: " + sound_vowel$
	sound_boundaries$ = Get value: sound_row#[1], "boundaries"
	appendInfoLine: "Boundaries: " + sound_boundaries$
	sound_creak$ = Get value: sound_row#[1], "creak"
	appendInfoLine: "Creak: " + sound_creak$
	sound_issues$ = Get value: sound_row#[1], "issues"
	appendInfoLine: "Issues: " + sound_issues$
	sound_flag$ = Get value: sound_row#[1], "flag"
	appendInfoLine: "Flagged: " + sound_flag$

	# Edit sound and TextGrid
	 select Sound 'name$'
	 plus TextGrid 'name$'
     Edit
		 beginPause: "Edit Text Grid"
			 comment: "Click 'Done' to save and continue. Click 'Keep' if need to return to this file later."
		 clicked = endPause: "Quit", "Skip", "Done", "Keep", 3, 1
		 if clicked = 1
					 endeditor
					 select all
					 Remove
					 exitScript ()
		 elsif clicked = 2
					 select TextGrid 'name$'
					 plus Sound 'name$'
					 Remove
					 list_index = list_index + 1
		 elsif clicked = 3
					 # Now save the result
					 select TextGrid 'name$'
					 Write to text file... 'tg_dir$''name$'.TextGrid
					 Remove
					 select Sound 'name$'
					 Remove
					 # Now remove filename from review file
					 select Strings review_list_out
					 Remove string... list_index
					 Save as raw text file... 'file_list$'
		 elsif clicked = 4
					 # Now save the result
					 select TextGrid 'name$'
					 Write to text file... 'tg_dir$''name$'.TextGrid
					 Remove
					 select Sound 'name$'
					 Remove
					 list_index = list_index + 1
		 endif
		 endeditor
endfor

select all
Remove
clearinfo
printline TextGrids have been reviewed for files in 'audio_dir$'.
