# A system for managing compound numbering

Numbering compounds is a common headache for chemistry researchers when preparing long chemistry documents, as a single missed compound might involve hours of tedious and error-prone renumbering, both in the text and all your ChemDraw files.
This repository provides a minimal example of the system I used during the preparation of my PhD thesis to circumvent this and increase the reliability of compound numbering.
The system allows you to only refer to compounds by a compound ID, such as a lab book reference, throughout your LaTeX document and ChemDraw files.
The compound numbers to which the compound IDs map to are separately defined in a `.csv` file.
The combined action of a `\cmpd` LaTeX command, python script, and applescript will keep the numbering system coordinated and ensure there is no inconsistency between your ChemDraws and your text.
The other key advantage is that if you need to (inevitably) change your compound numbering, for example, inserting or removing compounds, which would ordinarily cause an extremely annoying frameshift, you only need to edit the `.csv` file by shifting all the number fields up or down, which is facile in a text editor like Vim, or Microsoft Excel.
Elements of the system may be used in your own documents and adapted to your own use cases.

## Design, usage, and function

A centralised `maps/structure_id_map.csv` file defines a mapping of compound IDs to a compound number.
In the examples contained in this repository, the `.csv` maps compound `LL03-05 -> 133` and `LL03-06 -> 134`.
A third column in the `.csv` file is included called 'notes' where additional description of the compounds can be entered to make the mapping file more coherent and human readable; this is purely for convenience.

The python script `scripts/relabel_cdxmls.py` will read the mapping file, disregard the 'notes' column, take the data contained in the compound and label columns, and strip white space around the data to create a 1:1 dictionary mapping.
It will then sequentially search for all `.cdxml` files in the directory `chemdraw/cdxml/` to renumber.
To avoid editing the original source file, it will first clone all `.cdxml` files it finds into a mirror directory `chemdraw/cdxml_`, which will be edited by the python script.

In your original ChemDraw `.cdxml` files, instead of naming compounds with a number, you name the compounds with a tag `CMPD:`, followed by your compound ID; which must consist only of alphanumerical characters or hyphens; So :x: LL03_05 :white_check_mark: LL03-05.
You can allow additional characters by changing the regex expression in the `scripts/relabel_cdxmls.py` file but I would personally recommend against it and some other characters will mess up the command calls in your `.tex` files.
To ensure proper alignment is maintained after relabelling, the alignment in the textbox containing your compound ID tag should be **centered**.

![](examples/ChemDrawSourceFile.png)

As `.cdxml` is a human-readable text format, the python script will use regex to find all instances of the `CMPD:` tag and replace it with the appropriate label, so `CMPD:LL03-05` becomes `133`.

![](examples/ChemDrawRelabelledFile.png)

Finally, the python script will generate a new `.csv` file called `maps/_structure_id_map.csv`, which will be a clone of the source `maps/structure_id_map.csv` file, except with all white space stripped out, and only the two relevant columns (compound & label) remaining.
This is file will later be loaded by LaTeX during compilation.

To save the user having to now manually export the relabelled `.cdxml` file as a `.pdf` for inclusion into LaTeX document, running the applescript `scripts/cdxml2pdf.applescript` will search for all `.cdxml` files in the `chemdraw/cdxml_/` mirror directory and command the ChemDraw application to sequentially open each one and export them as a `.pdf` file of the same name in the `chemdraw/out/` directory.
These `.pdf` files can then be included in your LaTeX document with the `\includegraphics` command.

In your LaTeX document, the contents of `relabel.tex` need to included in the document preamble using an `\input` directive.
The file contains code which uses the `datatools` package to read the `maps/_structure_id_map.csv` file at the start of compilation and load it into memory as a lookup table called `chemmap`.
The file also defines the `\cmpd` command which can be used throughout the document.
Calling the command e.g. `\cmpd{LL03-05}` will trigger a lookup of `chemmap`, which will use `LL03-05` as the key and will replace it with whatever corresponding value it finds, in this case `133`.
If no value is found, the query key is outputted.

During certain points of writing and editorial review, it may be easier to read the document with the compound ID printed, rather than the relabelled number; in these cases changing the first line of `maps/structure_id_map.csv` file from `RELABEL=TRUE` to `RELABEL=FALSE` will disable relabelling.
In the `relabel.tex` file, `\relabelCmpdstrue` can be commented out and the `\relabelCmpdsfalse` uncommented to toggle relabelling off specifically in the main text.

The sum of these scripts is:

Original LaTeX document with relabelling disabled:

![](examples/PDFOutputRelabellingOff.png)

is outputted like so:

![](examples/PDFOutputRelabellingOn.png)

Since the whole system requires a specific running order of scripts, a bash script `./compile.sh` is used to reproducibly run these scripts and the `pdflatex` compilation passes necessary to produce the final document.

## Optimisations

Since the ChemDraw export process can take quite a while and be quite annoying to see (with tens or hundreds of files sequentially opening and closing), a system is implemented where the time where the scripts are last run is cached in `.chemdraw/cdxml_/.relabel_last_run_epoch` and `.chemdraw/out/.chemDraw_last_run_epoch` files and only ChemDraw files which have been edited *after* the last run time is re-exported.
An exception is applied when the mapping `maps/structure_id_map.csv` file itself is edited after the last run time.
In these cases, the system cannot know which labels have changed so *all* ChemDraw files are relabelled and re-exported.

## Performance

I comfortably used this system in writing my PhD thesis with hundreds of relabelled compounds and tens of `.cdxml` files.
Most of the time overhead is in the `.applescript` automation which commands the ChemDraw application to open all the files sequentially; this is minimised by the aforementioned optimisations.
The python script relabelling script takes a fraction of a second to parse through the `.csv` and crunch through hundreds of relabels.
The `datatools` lookups by the pdflatex interpreter is likewise quite fast, with only fractions of seconds added to overall compilation time for hundreds of lookups.

## Requirements

- Python 3; tested on v3.13 but the python script is basic and only uses the standard library so almost certainly works on other versions
- macOS; tested on Tahoe 26.6.2, needed for the `.applescript` to run. If anyone wants to try and get it working on Windows, you probably could but would need to write a PowerShell script to emulate the function of the `.applescript`
- ChemDraw; tested on v26.1.0.6801, worked on an older version as well
- TeX Live; tested with the 2024 distribution, for `datatools` and `pdflatex`

Note: Overleaf users, TeX Live is installed by default, although I have no idea how you'd run these scripts in your Overleaf environment.
I'm not an Overleaf expert so maybe someone else could get a system in place.

## Contributions

Open to any suggestions where improvements can be made, especially if you get this working on other operating systems or Overleaf; open up a pull request!
