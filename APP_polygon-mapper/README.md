# About Openstreet maps usage

Important: If you're opening the file directly (file:// protocol), you might still get 403 errors because browsers don't send proper Referer headers for local files. In that case, serve it from a simple web server:

Navigate to the folder containing the HTML file, then run:

    python -m http.server 8000

Then open in browser:

[http://localhost:8000/polygon-mapper.html]

This ensures proper HTTP headers are sent to OpenStreetMap's tile servers as per their usage policy. The referrer policy meta tag combined with serving from a web server should fix the 403 error while using the official OpenStreetMap tiles.
