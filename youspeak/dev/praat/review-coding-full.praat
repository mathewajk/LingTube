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
	comment Original Source Directory
	sentence original_dir	./queue/
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

	comment Vowel Lists (list each separated by a space)
	sentence target_vowels OW1 UW1 EY1
	integer max_target 65
	sentence reference_vowels IY1 AE1 AA1 AO1
	integer max_reference 30
endform

#########################################################
# Create vowel list vectors
target_vowels$# = splitByWhitespace$#(target_vowels$)
reference_vowels$# = splitByWhitespace$#(reference_vowels$)
finished_vowels$# = empty$#(size(target_vowels$#) + size(reference_vowels$#))
for j from 1 to size(finished_vowels$#)
	finished_vowels$#[j] = " "
endfor
#########################################################

# Create vowel list vectors
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

		 if not fileReadable: audio_dir$ + name$ + ".wav"
			## Hotfix for reviewing without already moved audio
			appendInfoLine: "Moving " + name$
			Read from file... 'original_dir$''name$'.wav
			select Sound 'name$'
			Write to WAV file... 'audio_dir$''name$'.wav
			filedelete 'original_dir$''name$'.wav
		 else
	 	 	Read from file... 'audio_dir$''name$'.wav
		 endif
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

	# Print total info
	select Table 'table_name$'
	Extract rows where... (self$["boundaries"]="1") & (self$["creak"]="1"|self$["creak"]="2"|self$["creak"]="3") & (self$["issues"]="1"|self$["issues"]="2"|self$["issues"]="4"|self$["issues"]="5")
	Rename: "usable_output"
	usable_rows = Get number of rows
	appendInfoLine: newline$
	appendInfoLine: "Usable vowels coded: " + string$(usable_rows) + newline$

	appendInfoLine: "Target vowels usable: "
							for i_vowel from 1 to size(target_vowels$#)
								current_vowel$ = target_vowels$#[i_vowel]
								select Table usable_output

								vowel_rows# = List row numbers where... self$["vowel"]=current_vowel$
								number_of_vowels = size(vowel_rows#)
								if number_of_vowels > max_target-1
									finished_vowels$#[i_vowel] = current_vowel$
								endif
								appendInfoLine: current_vowel$ + ": " + string$(number_of_vowels)
							endfor

	appendInfoLine:  newline$ + "Reference vowels usable: "
							for i_ref_vowel from 1 to size(reference_vowels$#)
								current_vowel$ = reference_vowels$#[i_ref_vowel]
								select Table usable_output

								vowel_rows# = List row numbers where... self$["vowel"]=current_vowel$
								number_of_vowels = size(vowel_rows#)
								if number_of_vowels > max_reference-1
									finished_vowels$#[i_ref_vowel + size(target_vowels$#)] = current_vowel$
								endif
								appendInfoLine: current_vowel$ + ": " + string$(number_of_vowels)
							endfor

	#select Table output
	select Table usable_output
	Remove

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

		 clicked = endPause: "Quit", "Set 0", "Done", "Keep", 3, 1
		 if clicked = 1
					 endeditor
					 select all
					 Remove
					 exitScript ()
		 elsif clicked = 2
					 # First save the new coding if different
					 select Table all_rows
					 Set numeric value: number(sound_idx$), "boundaries", 0
					 Set numeric value: number(sound_idx$), "creak", 0
					 Set numeric value: number(sound_idx$), "issues", 0
					 Set numeric value: number(sound_idx$), "flag", 0
					 Copy... updated_rows
					 Remove column... row_index
					 Save as comma-separated file... 'coding_log$'
					 Remove

					 select TextGrid 'name$'
					 plus Sound 'name$'
					 Remove
					 
					 # Now remove filename from review file
					 select Strings review_list_out
					 Remove string... list_index
					 Save as raw text file... 'file_list$'
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
