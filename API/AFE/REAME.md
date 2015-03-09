# AFE API Code Examples
This folder contains example projects that interact with the AFE Navigator API.

Each programming language has, at the very least, its own sub folder and a default example project. The default project does the following:
- Logs into AFENav
- Finds all AFEs with the text 'AFE' in the description
- Prints the result of the query to standard out
- Loops through each AFE in the result set and performs the following operations:
    - Retrieves the description and modifies it by capitalizing all instances of 'afe' it finds
    - Updates the description on the AFE
    - Saves the new changes to the AFE
- Logs out of AFENav