# v0.8.0
- Added cloud backup functionality:
  - Google Drive backup with automatic daily backups
  - OneDrive backup with automatic daily backups
  - Unencrypted backups with date-stamped filenames
  - Automatic backup verification to ensure files exist
- Fixed disable protection modal positioning
- Moved json files location to AppData Roaming WinOTP folder

# v0.7.7
- Fixed regression with next code preview, showing the same code after the first preview.

# v0.7.6
- Added single instance logic to prevent users from creating multiple windows of winotp
- Added double click functionality on tray icon to bring back the app window

# v0.7.5
- Performance improvements to API calls and backend reducing cpu usage

# v0.7.4
- Updated token refresh logic to cache secrets fixing CPU usage spike on reload
- Optimized next code preview

# v0.7.3
- Fixed issue where the quit button in the system tray menu didn't kill the app process
- Frontend performance improvements and stutter bug fixes
- I/O performance improvements

# v0.7.2
- Updated copy button logic to copy the next code when the current code is expiring
- Improved app startup performance

# v0.7.1
- Improved update downloaded confirmation section
- Fixed downloading update popup
- Fixed error when using screen capture

# v0.7
- Replaced SHA256 with Argon2 as encryption algorithm for a stronger protection of the tokens store
    - **NOTE**: this is a breaking change. Make sure to disable app protection before updating or tokens imported with previous app versions will not work and will need to be reimported.
- Added a security step with PIN / Password entering requirement to disable app protection
- Enhanced app protection page styling
- Enhanced app scrollbar look
- Improved token's account name contrast 
- Improved transition between next code preview and current code
- Replaced QR code camera scanning with screen capture

# v0.6
- Added open on startup feature
- New workflow for app updates, including in app changelog for the new release and an automated portable downloader in the User download folder
- Fixed an issue with re-authentication timeout config not being saved to the app settings file.
- Fixed an issue with animations smoothness when searching tokens
- Added a clear search button in the searchbar

# v0.5.2
- Fixed an issue blocking icons from loading when app protection is enabled
- Improved button styling for timeout option

# v0.5.1
- Fixed a critical issue which moved the app settings, config and tokens folder into the AppData/Local folder instead of the User Documents folder.

# v0.5
- Added functionality to import tokens from Google Authenticator migration QR codes.
- UI Refactor
- Updated App icon
- Fixed system tray icon size
- Optimized performance of Setings page

# v0.4
- Added next code preview functionality
- Optimized settings access to prevent unnecessary disk reads
- Added thread-safe settings handling with proper locking mechanism
- Added Authenticator browser plugin import functionality

# v0.3
- Added functionality to import tokens from 2FAS backup files (`.2fas`).
- Implemented a progress indicator during 2FAS import for better user experience.
- Fixed settings page 'Import Tokens' button to navigate to the import page instead of immediately opening the file explorer.
- Fixed progress bar not showing
- Fixed progress bar not becoming red
- Moved static folders into UI folder
- Updated bootstrap to 5.3.3
- Fixed the update check enable / disable toggle not saving state
- Fixed tray icon not appearing

# v0.2.1
- Fixed About page to display the correct dynamic version instead of a hardcoded value.

# 0.2
- Added update checker function with button redirect to release page

# 0.1
- Beta release

# ALPHA24
- Added strict validation for manually entered TOTP tokens
- Added base32 format validation for secret keys
- Automatically normalize secret keys by removing spaces and converting to uppercase
- Added functional validation to ensure TOTP codes can be generated
- Improved error messages with specific details about validation failures

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