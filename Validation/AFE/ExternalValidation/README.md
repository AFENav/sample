AFE External Validation
-----------------------

This project is a sample AFE validator (route/release) that runs as a standalone executable.

It is passed an [AFE validation message](http://cloudfront.energynavigator.com/afenav/releases/8.1/schemas/afe-validate.xsd) ([AFE schema](http://cloudfront.energynavigator.com/afenav/releases/8.1/schemas/afe.xsd)) in a temp file (ARG #1 to the EXE), and is expected to return a [validation result](http://cloudfront.energynavigator.com/afenav/releases/8.1/schemas/afe-validate-result.xsd) in another temp file (ARG #2 to the EXE).

This mechanism can be used for validating the AFE contents against an external system, or some complex logic, when the AFE is routed or released.

This example checks for the following:

- Requires that Start Date is not empty
- Requires that End Date is not empty
- Requires that End Date >= Start Date 
- Warns if AFE isn't sufficiently polite (doesn't include "please" in AFE description)

To execute this, compile to an EXE and then copy the "plugins\_available\custom\_validation\validation\_afe\_route\_release\_exe.config.sample" file to "plugins\validation\_test.config" (the exact name doesn't matter) and edit the .config file to specify the path to the built EXE.  When routing the AFE for review or release for approval the EXE will be passed the AFE information and will validate it.
