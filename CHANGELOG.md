# ALPHA23
- Added welcome message with empty drawer image when no tokens exist
- Added bulk import functionality in the settings page
- Implemented settings page with JSON format information for bulk imports
- Added guidance about settings/bulk import in the welcome screen
- Added automatic welcome message display when all tokens are deleted
- Made welcome message automatically disappear when tokens are added

# ALPHA22
- Added command-line argument support to switch between production and development token files
- Added `--debug` or `-d` flag to use the development token file (tokens.json.dev)
- Default behavior uses production token file (tokens.json) for normal execution
- Added console output to indicate which mode (DEBUG/PRODUCTION) the application is running in

# ALPHA21
- Changed token storage format to use unique IDs instead of issuer names as keys
- Added support for multiple tokens from the same issuer (e.g., multiple Instagram accounts)
- Updated duplicate checking to only prevent tokens with the same secret rather than same issuer
- Improved error handling for JSON file loading and parsing
- Added debug logging of loaded tokens to help troubleshoot issues

# ALPHA20
- Added hover animation that turns delete buttons red when hovering
- Added confirmation dialog before deleting TOTP tokens
- Standardized button colors: all action buttons are now blue in normal state

# ALPHA19
- Added hand cursor to all buttons to improve user experience
- Buttons now visually indicate they are clickable when hovered over
- Enhanced interface consistency with web-like interaction patterns

# ALPHA18
- Fixed copy button animation to show green background for the entire button
- Restored proper blue color for copy buttons in normal state
- Improved button focus behavior to prevent focus outlines from appearing after clicks

# ALPHA17
- Added copy confirmation animation with visual feedback on the copy button
- Changed copy button to temporarily show a success state with confirmation icon
- Improved user experience with clear visual feedback when copying TOTP codes

# ALPHA16
- Added icons for sort, copy, and delete buttons
- Improved sort button to display appropriate icon for current sort direction
- Enhanced consistency of button icon display across the application

# ALPHA15
- Fixed scrollbar display to match app theme using ttk.Scrollbar
- Added smart scrollbar that hides when content doesn't exceed window height
- Improved layout consistency when scrollbar appears/disappears

# ALPHA14
- Added sort button to arrange TOTPs alphabetically by issuer name
- Added toggle functionality to switch between ascending and descending sort order
- Visual indicators (A→Z/Z→A) show current sort direction
- Fixed sorting to apply immediately when application loads
- Refactored code to make sorting more consistent across app

# ALPHA13
- Added proper icon support for search, plus, and settings buttons
- Improved icon loading with better error handling
- Added fallback to text buttons when icons aren't available
- Added button padding for better visual appearance
- Fixed styling compatibility issues with different ttkbootstrap versions

# ALPHA12
- Renamed conf_path to tokens_path for better code readabilty

# ALPHA11
- Fixed delete token functionality by correctly deleting it from the loaded token also
- Fixed visual glitch when adding token after deleting one related to the previous issue
- Added unquote library to automatically replace percentage character with normal characters
- Added cryptography library for future json cryptography implementation

# ALPHA10
- Added delete token functionality

# ALPHA9
- Code refactor to use classes
- Searchbar separated from scrolling canvas to keep it usable when scrolling

# ALPHA8
- Disabled window resize

# ALPHA7
- Fixed exception when closing file dialog for add token without selecting a file
- Added settings button (yet to implement)

# ALPHA6
- Added scrolling capabilities to the window

# ALPHA5
- Added add token via qr code image functionality
- Switched GUI layout to grid for better organization

# ALPHA4
- Set the window to be opened at the center of the screen

# ALPHA3
- Fixed copy button logic

# ALPHA2
- Fixed typo in winotp.py

# ALPHA1
- Initial release