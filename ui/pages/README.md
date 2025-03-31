# WinOTP Pages Organization

This directory contains the HTML components for each page in the WinOTP application. Originally, the application had all pages in a single index.html file, but they have been refactored into separate files for better organization.

## Current Status

**Important**: The application is currently using the individual page components embedded directly in `index.html` rather than loading them dynamically. This is to ensure compatibility with the existing JavaScript.

## Files Organization

- `main.html` - Main page with token list
- `settings.html` - Settings page
- `about.html` - About page with app information
- `import-tokens.html` - Import tokens selection page
- `import-progress.html` - Import progress indicator
- `google-auth-import.html` - Google Authenticator import page
- `add-token.html` - Add new token page
- `app-protection.html` - App protection settings
- `login.html` - Login page
- `base.html` - Base template for reference

## Future Improvements

In future versions, we plan to load these components dynamically with a proper templating system. For now, all pages exist in these separate files for organization, but the actual HTML is directly embedded in the main index.html file.

## How to Make Changes

When making changes to the UI:

1. If it's a small change, edit the component directly in `index.html`
2. For larger changes:
   - Edit the corresponding page file in the `pages` directory
   - Then update the corresponding section in `index.html`
   - Keep both files in sync

This approach ensures code is properly organized while maintaining compatibility with the existing JavaScript functionality. 