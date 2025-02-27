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