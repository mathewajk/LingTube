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
	comment Start from file number...
	positive start_number 1
	comment Delete Existing Review List
	boolean delete_list 0
endform

# Set names based on boolean
if flagged_only = 0
	file_list$ = "review_list_all.txt"
	table_name$ = "all_rows"
elsif flagged_only = 1
	file_list$ = "review_list_flagged.txt"
	table_name$ = "flagged_rows"
endif

# Read in relevant tables
Read Table from comma-separated file... 'coding_log$'
Rename: "all_rows"
Append column: "row_index"
number_of_rows = Get number of rows
max_order_number = Get value: number_of_rows, "order"
if (start_number > max_order_number)
	exitScript ("Value of start number is greater than the number of rows or maximum file number. Please re-enter a valid number.")
endif
for i_row to number_of_rows
	Set numeric value: i_row, "row_index", i_row
endfor
if flagged_only = 1
	Extract rows where... self$["flag"]="1"
	Rename: "flagged_rows"
endif

if delete_list = 1
	if fileReadable (file_list$)
		deleteFile: file_list$
	endif
endif

# If review_list file does not exist, create it
if !(fileReadable (file_list$))
	number_of_rows = Get number of rows
	start_row# = List row numbers where... self[row,"order"]=start_number
	while size(start_row#) = 0
		start_number += 1
		start_row# = List row numbers where... self[row,"order"]=start_number
	endwhile
	x_file = start_row#[1]

	Create Strings from tokens: "review_list_in", "", ""

	for i_file from x_file to number_of_rows
		select Table 'table_name$'
		soundname$ = Get value: i_file, "file"
		select Strings review_list_in
		Insert string: 0, soundname$
	endfor

	Save as raw text file... 'file_list$'
endif

# Read file and create copy for output list
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

	# Get row index info
	sound_idx$ = Get value: sound_row#[1], "row_index"

	# Edit sound and TextGrid
	 select Sound 'name$'
	 plus TextGrid 'name$'
     Edit
		 beginPause: "Edit Text Grid"
			 comment: "Click 'Done' to save and continue. Click 'Keep' if need to return to this file later."

		 boundaries = choice ("Boundaries", number(sound_boundaries$))
			 option ("good (e.g. fixed)")
			 option ("bad (e.g. can't be fixed)")
			 option ("unsure (e.g. can't identify vowel clearly)")
			 option ("wrong (e.g. no vowel or syllabic C)")
		 creak = choice ("Creak", number(sound_creak$))
			 option ("none")
			 option ("start")
			 option ("end")
			 option ("half/most/all")
		 issues = choice ("Issues", number(sound_issues$))
			 option ("none")
			 option ("vowel quality")
			 option ("breathy/whisper/voiceless")
			 option ("noise/sfx/click/etc.")
			 option ("other")
		 flag = boolean ("Flag", number(sound_flag$))

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
		 			 # First save the new coding if different
					 select Table all_rows
					 Set numeric value: number(sound_idx$), "boundaries", boundaries
					 Set numeric value: number(sound_idx$), "creak", creak
					 Set numeric value: number(sound_idx$), "issues", issues
					 Set numeric value: number(sound_idx$), "flag", flag
					 Copy... updated_rows
					 Remove column... row_index
					 Save as comma-separated file... 'coding_log$'
					 Remove

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
					 # First save the new coding if different
					 select Table all_rows
					 Set numeric value: number(sound_idx$), "boundaries", boundaries
					 Set numeric value: number(sound_idx$), "creak", creak
					 Set numeric value: number(sound_idx$), "issues", issues
					 Set numeric value: number(sound_idx$), "flag", flag
					 Copy... updated_rows
					 Remove column... row_index
					 Save as comma-separated file... 'coding_log$'
					 Remove

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
