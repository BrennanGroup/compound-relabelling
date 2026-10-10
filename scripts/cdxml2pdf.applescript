set currentDir to do shell script "pwd"

set inputFolder to currentDir & "/chemdraw/cdxml_"
set outputFolder to currentDir & "/chemdraw/out"

-- Hidden state file that stores the last successful run time (Unix epoch seconds)
set stateFile to outputFolder & "/.chemDraw_last_run_epoch"

-- Convert POSIX path to AppleScript alias
set inputFolderAlias to POSIX file inputFolder as alias

-- Read last run time, or default to 0 if this is the first run
set lastRunEpoch to 0
try
	set lastRunEpochText to do shell script "cat " & quoted form of stateFile
	if lastRunEpochText is not "" then set lastRunEpoch to lastRunEpochText as integer
end try

tell application "Finder"
	set fileList to every file of folder inputFolderAlias whose name extension is "cdxml"
end tell

repeat with aFile in fileList
	set filePath to POSIX path of (aFile as alias)
	
	-- Use file modification time in Unix epoch seconds
	set modEpochText to do shell script "stat -f %m " & quoted form of filePath
	set modEpoch to modEpochText as integer
	
	-- Only process if modified after the last run
	if modEpoch > lastRunEpoch then
		tell application "ChemDraw"
			open (aFile as alias)
			
			-- Extract filename without extension
			set fileName to name of aFile
			if fileName contains "." then
				set baseName to text 1 thru ((offset of "." in fileName) - 1) of fileName
			else
				set baseName to fileName
			end if
			
			-- Save as PDF
			set outputPath to outputFolder & "/" & baseName & ".pdf"
			save document 1 as "PDF" in POSIX file outputPath
			
			-- Close the document
			close document 1 saving no
		end tell
	end if
end repeat

-- Update last run time only after the script finishes successfully
do shell script "date +%s > " & quoted form of stateFile
