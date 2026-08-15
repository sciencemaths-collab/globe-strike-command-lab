# Architecture

Globe Strike Command Lab is a single-process local simulation application with a browser UI and Python HTTP backend.

## Runtime layers

1. **Browser simulation UI**
   - scenario setup and geospatial controls
   - projectile / interceptor visualization
   - campaign-state dashboards
   - engagement statistics and confidence bands

2. **Simulation engine**
   - campaign state and synthetic stockpiles
   - readiness, logistics, C2, sensor confidence and uncertainty
   - projectile / interceptor state evolution
   - outcome memory and rolling calibration

3. **AI director**
   - receives bounded campaign state
   - returns strategic and operational policy values
   - drives tempo, reserve use, posture, repair, sensing and related game parameters
   - uses a local fallback director when no external model is configured

4. **Local backend**
   - serves the UI
   - exposes geocoding / suggestion endpoints
   - exposes AI configuration and director endpoints

## Data flow

User scenario → campaign state → AI director policy → simulation update → engagement outcome → statistics / memory → next campaign state.

The application is designed as a fictional game / research sandbox. Synthetic game parameters should not be interpreted as verified real-world military performance data.
