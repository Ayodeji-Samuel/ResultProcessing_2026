"""
Configuration for default GPS coordinates
Used when user accesses from localhost/campus network
"""

# Default location for localhost access (campus location)
# UPDATE THESE to your actual university coordinates!

# Current setting: Abuja, Nigeria (example)
DEFAULT_LOCATION = {
    'name': 'Local Machine (Campus Network)',
    'latitude': 9.0765,      # Change to your university's latitude
    'longitude': 7.3986,     # Change to your university's longitude
    'city': 'Abuja',         # Your city
    'state': 'FCT',          # Your state/region
    'country': 'Nigeria'     # Your country
}

# HOW TO FIND YOUR UNIVERSITY'S COORDINATES:
# 1. Go to Google Maps (https://maps.google.com)
# 2. Search for your university
# 3. Right-click on the university location
# 4. Click the coordinates (they'll be copied)
# 5. Paste them above (format: latitude, longitude)

# Examples:
# University of Lagos: 6.5165, 3.3901
# University of Ibadan: 7.4467, 3.9056
# Ahmadu Bello University: 11.1593, 7.6431
# University of Nigeria, Nsukka: 6.8626, 7.3986
# University of Abuja: 9.0765, 7.3986
# Obafemi Awolowo University: 7.5305, 4.5215
