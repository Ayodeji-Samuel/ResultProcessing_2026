# GPS Coordinate Tracking - Quick Reference

## What You'll See in Result Alterations

When viewing alteration details, you'll now see:

### Location Information Section
```
┌─────────────────────────────────────────────────┐
│ 📍 Device & Location Information                │
├─────────────────────────────────────────────────┤
│ IP Address:       197.210.76.196                │
│ Device Type:      Desktop                       │
│ Browser:          Chrome 120.0.0                │
│ Operating System: Windows 10                    │
│ Device Username:  ADMIN-PC\administrator        │
│ Location:         Lagos, Lagos, Nigeria         │
│ Coordinates:      6.524379, 3.379206            │
│                   📍 View on Google Maps  ←─────┼── Clickable!
└─────────────────────────────────────────────────┘
```

## Example Scenarios

### Scenario 1: Legitimate Local Edit
```
Location:     Abuja, Federal Capital Territory, Nigeria
Coordinates:  9.076480, 7.398580
Google Maps:  [Shows Federal Capital Territory]
```
✅ Expected behavior - user is in university location

### Scenario 2: Remote Access
```
Location:     London, England, United Kingdom  
Coordinates:  51.509865, -0.118092
Google Maps:  [Shows London city center]
```
⚠️ Requires investigation - unusual location for result alteration

### Scenario 3: VPN/Proxy Detection
```
Location:     Ashburn, Virginia, United States
Coordinates:  39.043701, -77.487488
Google Maps:  [Shows data center location]
```
⚠️ Possible VPN - many VPN servers route through Virginia

### Scenario 4: Local Development
```
Location:     Local Machine
Coordinates:  (Not available)
Google Maps:  (No link)
```
✅ Localhost access - testing/development environment

## Coordinate Format

- **Latitude**: -90 to +90 (negative = South, positive = North)
  - Example: 6.524379 (6.52° North - Lagos, Nigeria)
  
- **Longitude**: -180 to +180 (negative = West, positive = East)
  - Example: 3.379206 (3.38° East - Lagos, Nigeria)

- **Precision**: 6 decimal places
  - Accuracy: ~0.11 meters (very precise!)

## Google Maps Integration

Clicking the "View on Google Maps" link will:
1. Open a new browser tab
2. Show the exact location on Google Maps
3. Display nearby landmarks and streets
4. Allow you to:
   - Zoom in/out
   - Switch to satellite view
   - Get directions
   - See street view (if available)

## Security Benefits

1. **Anomaly Detection**: Spot unusual access locations immediately
2. **Audit Trail**: Complete geographic record of all changes
3. **Forensics**: Investigate suspicious activity with precise location data
4. **Compliance**: Meet regulatory requirements for data modification tracking
5. **Deterrence**: Users know their location is being tracked

## Privacy Considerations

- ✅ Only captures approximate location from IP address
- ✅ No personal GPS data from user devices
- ✅ Same data already available to network administrators
- ✅ Visible only to HoD and authorized administrators
- ✅ Helps protect student data integrity

## Accuracy

| Connection Type | Typical Accuracy |
|----------------|------------------|
| University WiFi | City-level (±10-50 km) |
| Mobile Network | City/Region (±20-100 km) |
| Home Broadband | City-level (±10-50 km) |
| VPN/Proxy | Data center location |
| Localhost | Not applicable |

**Note**: IP geolocation provides approximate location, not exact GPS position from device.

## Technical Details

- **API Provider**: ip-api.com (free tier, 45 requests/minute)
- **Fallback**: If API unavailable, shows "Unknown" for location/coordinates
- **Timeout**: 2 seconds maximum (prevents system delays)
- **Storage**: Coordinates stored as FLOAT in database
- **Display**: 6 decimal places for precision

---

**Last Updated**: February 6, 2026
**Status**: ✅ Active and Operational
