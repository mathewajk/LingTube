#########################################################################
# This is a script that automatically brings up a Sound and
# TextGrid for coding/adjusting boundaries after forced alignment.
# -------------------------------------------------------------
# Lauretta Cheng, 2021
# Based on scripts by Grant McGuire, Katherine Crosswhite, Mark Antoniou
#########################################################################

# Compatible with both Windows and OSX
# Requires the slash at the end of the directory name.
# (Windows: backslash, OSX: forward slash)

form Modify textgrids
	comment Source Audio Directory
	sentence audio_dir	./queue/
	comment Aligned Textgrid Directory
	sentence tg_dir	./queue/
	comment Directory to move the original Sound files to
	sentence out_audio_dir ./audio/
	comment Directory to write the TextGrid to
	sentence out_tg_dir ./textgrids/
	comment Output filename
	sentence outfile vowel_coding_log.csv
	comment Vowel Lists (list each separated by a space)
	sentence target_vowels OW1 UW1 EY1
	integer max_target 50
	sentence reference_vowels IY1 AE1 AA1 AO1
	integer max_reference 20
endform

#########################################################
# Create vowel list vectors
target_vowels$# = splitByWhitespace$#(target_vowels$)
reference_vowels$# = splitByWhitespace$#(reference_vowels$)
finished_vowels$# = empty$#(size(target_vowels$#) + size(reference_vowels$#))
for j from 1 to size(finished_vowels$#)
	finished_vowels$#[j] = " "
endfor
#finished_vowel_i = 1

#########################################################
# Create/read file and add header if file doesn't already exist (NOTE: fileReadable location is always relative to script)
new_outfile = 0
if !(fileReadable (outfile$))
		writeFileLine: "'outfile$'", "file,order,vowel,boundaries,creak,issues,flag"
		new_outfile = 1
endif

# Check coding progress
if new_outfile = 0
	clearinfo
	Read Table from comma-separated file... 'outfile$'
	Rename: "output"
	total_rows = Get number of rows
	appendInfoLine: "Total vowels coded: " + string$(total_rows) + newline$

	Extract rows where... self$["boundaries"]="1" & self$["creak"]="1" & self$["issues"]="1"
	Rename: "usable_output"
	usable_rows = Get number of rows
	appendInfoLine: "Usable vowels coded: " + string$(usable_rows) + newline$

	appendInfoLine: "Target vowels usable: "
	for i_vowel from 1 to size(target_vowels$#)
		current_vowel$ = target_vowels$#[i_vowel]
		select Table usable_output

		vowel_rows# = List row numbers where... self$["vowel"]=current_vowel$
		number_of_vowels = size(vowel_rows#)
		if number_of_vowels > 49
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
		if number_of_vowels > 19
			finished_vowels$#[i_ref_vowel + size(target_vowels$#)] = current_vowel$
		endif
		appendInfoLine: current_vowel$ + ": " + string$(number_of_vowels)
	endfor

	select Table output
	plus Table usable_output
	Remove
else
	usable_rows = 0
endif

#########################################################
# Get list of all files
clearinfo
Create Strings as file list... list 'audio_dir$'*.wav
number_of_files = Get number of strings

# Process each file
for i_file to number_of_files
	select Strings list
	soundname$ = Get string... i_file
	name$ = soundname$-".wav"

	# Name structure: channel[1]_channelid[2]_ytid[3]_order[4]_starttimems[5]_endtimems[6]_vowellabel[7]
	# Create string vector by splitting on '_' transformed into whitespace
	namesplit$# = splitByWhitespace$#(replace$ (name$, "_", " ", 0))

	# Get necessary info from filename
	order$ = namesplit$#[4]
	#appendInfoLine: order$
	vowel$ = namesplit$#[7]
	#appendInfoLine: vowel$


	#########################################################
	# Check if need to open file
	if usable_rows > 199
		first200_complete = 1
	else
		first200_complete = 0
	endif

	vowel_complete = 0
	if first200_complete = 1
		for j from 1 to size(finished_vowels$#)
			if finished_vowels$#[j] = vowel$
				vowel_complete = 1
			endif
		endfor
	endif

	if first200_complete = 0 or vowel_complete = 0
		#########################################################
		# Read and modify files
		Read from file... 'audio_dir$''name$'.wav
		Read from file... 'tg_dir$''name$'.TextGrid

		# Insert target vowel point marker at center of sound file
		tg_end_time = Get end time
		Insert point tier: 3, "vowel marker"
		Insert point: 3, tg_end_time/2, "target"

		#########################################################
		# Now bring up the editor to work on fixing the boundaries

		select Sound 'name$'
		plus TextGrid 'name$'
		Edit
			beginPause: "Edit Text Grid"
				comment: "Please adjust the boundaries on the TextGrid."

	    boundaries = choice ("Boundaries", 1)
	    	option ("good (e.g. fixed)")
	    	option ("bad (e.g. can't be fixed)")
				option ("unsure (e.g. can't identify vowel clearly)")
				option ("wrong (e.g. no vowel or syllabic C)")
			creak = choice ("Creak", 1)
				option ("none")
				option ("start")
				option ("end")
				option ("half/most/all")
			issues = choice ("Issues", 1)
				option ("none")
				option ("vowel quality (e.g. mispronounced)")
				option ("breathy/whisper/voiceless")
				option ("noise/sfx/click/etc.")
				option ("other")
			flag = boolean ("Flag", 0)

			clicked = endPause: "Quit", "Skip", "Done", 3, 1
			if clicked = 1
						endeditor
						select all
						Remove
						if new_outfile = 1
							deleteFile: outfile$
						endif
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
						# Delete file
						filedelete 'audio_dir$''name$'.wav

						# Save to a spreadsheet
						appendFileLine: "'outfile$'",
							...soundname$, ",",
							...order$, ",",
							...vowel$, ",",
							...boundaries, ",",
							...creak, ",",
							...issues, ",",
							...flag

							if new_outfile = 1
								new_outfile = 0
							endif

							clearinfo
							Read Table from comma-separated file... 'outfile$'
							Rename: "output"
							total_rows = Get number of rows
							appendInfoLine: "Total vowels coded: " + string$(total_rows) + newline$

							Extract rows where... self$["boundaries"]="1" & self$["creak"]="1" & self$["issues"]="1"
							Rename: "usable_output"
							usable_rows = Get number of rows
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

							select Table output
							plus Table usable_output
							Remove

			endif
		endeditor

	endif

endfor

select all
Remove
