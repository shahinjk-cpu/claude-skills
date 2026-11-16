---
name: isponsorblocktv
description: >
  Automation and configuration skill for iSponsorBlockTV. Automatically detects and skips sponsored segments, intros, and outros on Apple TV, Android TV, and smart TVs.
metadata:
  version: "1.0.0"
  category: general_tools
  triggers: isponsorblocktv, sponsorblock, skip ads apple tv, skip youtube sponsors smart tv
---

# iSponsorBlockTV — Smart TV Sponsor Skipping

Configures and maintains iSponsorBlockTV service instances on local home servers to automatically skip sponsored segments on YouTube apps running on Apple TV, Android TV, and LG webOS.

## Configuration & Docker Run
```bash
docker run -d --name isponsorblocktv   -v ./data:/app/data   --net=host   ghcr.io/dmunozv/isponsorblocktv
```
