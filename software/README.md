# Software
This Page outlines details about the software side of the project.

## Folder Layout
### demo-objdet
An initial demo to detect colours and apriltags using openCV

### noir
Setup and basic code for the noir camera using picamera2 library

### thermal
Setup and basic code for the thermal camera using mi48

### camcom
Integration of thermal, noir, and serial communication.
Implementing main project using multithreading then multiprocessing.

## Releases
1. dualcam.py
Used in Rev 0 presentation for very basic hazard & hand detection. Also has LED feedback based on distance between hazard and hand.

## Documentation Standards

### Making changes
When making any code changes, a new branch must be created from main with an appropriate name. This allows the main branch to always be clean and stable. Once the changes have been added, a pull request will be made to merge the branch with main. The branch must be tested and include documentation of testing. The pull request must get approved by at least one other group member by completing a code review.

### Formatting
All code is strongly recommended to follow similar practices to the Google style guides https://google.github.io/styleguide/. A few important coding practices:
-	Detailed variable and file names
-	Commented code wherever non-trivial
Naming development branches for adding features should start with “dev-” and have a unique feature name.

Naming bug fixing branches should start with “bug-” and followed by an appropriate bug name or number.

Naming release branches should start with “rel-<date>-” where date is replaced with date “DD/MM/YY” of the day the branch is made, and a unique name.

### Documentation
Every code change must be documented using detailed commit messages. Commit messages are never one line and must include:
-	Motivation (why is this change needed?)
-	Description (what does this commit do?)
-	Testing done
-	Any other relevant information (dependencies, files generated, other commits required)
README files will also be used to document multiple files and directories in the repository at a larger scale. They will be used to track all features that are present. These files will be updated in the commits and pull requests that add the features.

### Testing
Before merging a pull request, appropriate testing must be done to ensure that the new additions do not impact any other functionality. Testing at this stage does not need to cover every case and feature, only those affected by the changes.

Releases, if necessary, will be created using a new branch off main. This branch will not allow any new additions except bug fixes that have been found during testing. Testing will go through every feature that is present in the branch (see documentation for list of features).
